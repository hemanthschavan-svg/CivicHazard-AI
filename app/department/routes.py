import os
import uuid

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, abort
)
from flask_login import current_user
from PIL import Image, UnidentifiedImageError

from app import db
from app.access import roles_required
from app.models.report import Report
from app.models.history import History

department = Blueprint("department", __name__, url_prefix="/department")


@department.route("/dashboard")
@roles_required("department_officer")
def dashboard():
    reports = Report.query.filter_by(
        assigned_officer_id=current_user.id
    ).order_by(Report.updated_at.desc()).all()

    return render_template("department/dashboard.html", reports=reports)


@department.route("/report/<int:report_id>", methods=["GET", "POST"])
@roles_required("department_officer")
def update_report(report_id):
    report = Report.query.filter_by(
        id=report_id,
        assigned_officer_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        action = request.form.get("action")
        remarks = request.form.get("remarks", "").strip()

        if action == "start":
            if report.status != "Assigned":
                abort(400)

            old_status = report.status
            report.status = "In Progress"

        elif action == "complete":
            if report.status not in ("Assigned", "In Progress"):
                abort(400)

            uploaded = request.files.get("completion_image")

            if not uploaded or not uploaded.filename:
                flash("Upload a completion photograph.")
                return redirect(url_for(
                    "department.update_report", report_id=report.id
                ))

            try:
                uploaded.stream.seek(0)
                image = Image.open(uploaded.stream)
                image.verify()

                uploaded.stream.seek(0)
                image = Image.open(uploaded.stream)

                if image.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("Unsupported image format.")

                image_format = image.format

            except (UnidentifiedImageError, OSError, ValueError):
                flash("Upload a valid JPEG, PNG or WEBP photograph.")
                return redirect(url_for(
                    "department.update_report", report_id=report.id
                ))

            extension = {
                "JPEG": ".jpg",
                "PNG": ".png",
                "WEBP": ".webp"
            }[image_format]

            filename = f"{uuid.uuid4().hex}{extension}"

            folder = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                "completion_evidence"
            )
            os.makedirs(folder, exist_ok=True)

            image_path = os.path.join(folder, filename)

            uploaded.stream.seek(0)
            uploaded.save(image_path)

            old_status = report.status
            report.completion_image = filename
            report.status = "Pending Verification"

        else:
            abort(400)

        try:
            db.session.add(History(
                report_id=report.id,
                changed_by=current_user.id,
                old_status=old_status,
                new_status=report.status,
                remarks=remarks or "Department officer updated the complaint."
            ))
            db.session.commit()

        except Exception:
            db.session.rollback()

            if action == "complete" and os.path.exists(image_path):
                os.remove(image_path)

            current_app.logger.exception("Department update failed.")
            flash("Could not update the complaint.")
            return redirect(url_for(
                "department.update_report", report_id=report.id
            ))

        flash("Complaint updated successfully.")
        return redirect(url_for("department.dashboard"))

    history = History.query.filter_by(
        report_id=report.id
    ).order_by(History.created_at.asc()).all()

    return render_template(
        "department/report.html",
        report=report,
        history=history
    )

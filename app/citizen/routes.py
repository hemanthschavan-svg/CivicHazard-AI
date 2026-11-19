import os
import uuid
from datetime import datetime

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app
)
from flask_login import login_required, current_user, logout_user
from PIL import Image, UnidentifiedImageError

from app import db
from app.models.report import Report
from app.models.history import History
from app.ai.classifier import get_classifier

citizen = Blueprint("citizen", __name__, url_prefix="/citizen")

CATEGORIES = {
    "Pothole": "Roads",
    "Road Damage": "Roads",
    "Streetlight Failure": "Electrical",
    "Drainage Problem": "Drainage",
    "Garbage Accumulation": "Sanitation"
}


@citizen.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(
        citizen_id=current_user.id
    ).order_by(Report.created_at.desc()).all()

    return render_template("citizen/dashboard.html", reports=reports)


@citizen.route("/report", methods=["GET", "POST"])
@login_required
def submit_report():

    if request.method == "POST":
        category = request.form.get("category")
        description = request.form.get("description", "").strip()
        address = request.form.get("address", "").strip()

        try:
            latitude = float(request.form.get("latitude"))
            longitude = float(request.form.get("longitude"))

            if not (
                -90 <= latitude <= 90
                and -180 <= longitude <= 180
            ):
                raise ValueError()

        except (TypeError, ValueError):
            flash("Please detect or enter a valid location.")
            return redirect(url_for("citizen.submit_report"))

        if category not in CATEGORIES or len(description) < 10:
            flash("Select a valid category and enter at least 10 characters.")
            return redirect(url_for("citizen.submit_report"))

        uploaded = request.files.get("image")

        if not uploaded or not uploaded.filename:
            flash("Please upload a complaint photograph.")
            return redirect(url_for("citizen.submit_report"))

        # Validate the actual image file.
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
            flash("Invalid image. Upload a JPEG, PNG or WEBP photograph.")
            return redirect(url_for("citizen.submit_report"))

        extension = {
            "JPEG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp"
        }[image_format]

        filename = f"{uuid.uuid4().hex}{extension}"

        upload_folder = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            "complaints"
        )

        os.makedirs(upload_folder, exist_ok=True)

        image_path = os.path.join(upload_folder, filename)

        # Save temporarily so the AI model can inspect the image.
        uploaded.stream.seek(0)
        uploaded.save(image_path)

        # AI image analysis.
        try:
            classifier = get_classifier()
            result = classifier.classify(image_path)

        except Exception:
            if os.path.exists(image_path):
                os.remove(image_path)

            current_app.logger.exception("AI image classifier failed.")
            flash("AI image analysis is currently unavailable. Please try again.")
            return redirect(url_for("citizen.submit_report"))

        # Reject unrelated images before creating a complaint.
        if not result.get("accepted"):
            if os.path.exists(image_path):
                os.remove(image_path)

            flash(result.get(
                "message",
                "This image does not appear to show a supported civic issue."
            ))
            return redirect(url_for("citizen.submit_report"))

        # Use the category detected by AI.
        detected_category = result.get("category")

        if detected_category not in CATEGORIES:
            if os.path.exists(image_path):
                os.remove(image_path)

            flash("AI could not identify a supported civic issue. Please try another photograph.")
            return redirect(url_for("citizen.submit_report"))

        category = detected_category

        complaint_id = (
            "CHA-"
            + datetime.now().strftime("%Y%m%d")
            + "-"
            + uuid.uuid4().hex[:6].upper()
        )

        try:
            report = Report(
                complaint_id=complaint_id,
                citizen_id=current_user.id,
                category=category,
                description=description,
                latitude=latitude,
                longitude=longitude,
                address=address,
                image_filename=filename,
                department=CATEGORIES[category],
                status="Submitted"
            )

            db.session.add(report)
            db.session.flush()

            history = History(
                report_id=report.id,
                changed_by=current_user.id,
                old_status=None,
                new_status="Submitted",
                remarks="Complaint submitted by citizen after AI image screening."
            )

            db.session.add(history)
            db.session.commit()

        except Exception:
            db.session.rollback()

            if os.path.exists(image_path):
                os.remove(image_path)

            current_app.logger.exception("Complaint submission failed.")
            flash("Complaint could not be submitted. Please try again.")
            return redirect(url_for("citizen.submit_report"))

        flash(
            f"AI detected: {category}. "
            f"Complaint submitted successfully! ID: {complaint_id}"
        )

        return redirect(url_for("citizen.dashboard"))

    return render_template("citizen/report.html")


@citizen.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("main.home"))
@citizen.route("/report/<int:report_id>")
@login_required
def track_report(report_id):
    report = Report.query.filter_by(
        id=report_id,
        citizen_id=current_user.id
    ).first_or_404()

    history = History.query.filter_by(
        report_id=report.id
    ).order_by(History.created_at.asc()).all()

    return render_template(
        "citizen/track.html",
        report=report,
        history=history
    )

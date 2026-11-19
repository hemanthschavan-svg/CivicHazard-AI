import os

from flask import (
    Blueprint, render_template, request, current_app,
    redirect, url_for, flash, abort
)
from flask_login import current_user

from app import db
from app.access import roles_required
from app.models.report import Report
from app.models.history import History

verification = Blueprint(
    "verification", __name__, url_prefix="/verification"
)


@verification.route("/dashboard")
@roles_required("verification_officer")
def dashboard():
    reports = Report.query.filter_by(
        status="Pending Verification"
    ).order_by(Report.updated_at.asc()).all()

    return render_template(
        "verification/dashboard.html",
        reports=reports
    )


@verification.route("/report/<int:report_id>", methods=["GET", "POST"])
@roles_required("verification_officer")
def review_report(report_id):
    report = Report.query.filter_by(
        id=report_id,
        status="Pending Verification"
    ).first_or_404()

    if request.method == "POST":
        action = request.form.get("action")
        remarks = request.form.get("remarks", "").strip()

        if action not in ("approve", "reject"):
            abort(400)

        if action == "reject" and len(remarks) < 10:
            flash("Please provide a rejection reason of at least 10 characters.")
            return redirect(url_for(
                "verification.review_report",
                report_id=report.id
            ))

        if not report.completion_image:
            flash("This complaint has no completion evidence.")
            return redirect(url_for(
                "verification.review_report",
                report_id=report.id
            ))

        old_status = report.status
        old_evidence = report.completion_image

        if action == "approve":
            report.status = "Resolved"
            report.verification_notes = remarks or "Resolution verified."

        else:
            report.status = "In Progress"
            report.verification_notes = remarks
            report.completion_image = None

        try:
            db.session.add(History(
                report_id=report.id,
                changed_by=current_user.id,
                old_status=old_status,
                new_status=report.status,
                remarks=report.verification_notes
            ))

            db.session.commit()

        except Exception:
            db.session.rollback()
            current_app.logger.exception("Verification update failed.")

            flash("Could not save the verification decision.")
            return redirect(url_for(
                "verification.review_report",
                report_id=report.id
            ))

        # Delete rejected evidence only after the database update succeeds.
        if action == "reject" and old_evidence:
            evidence_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                "completion_evidence",
                old_evidence
            )

            try:
                if os.path.isfile(evidence_path):
                    os.remove(evidence_path)
            except OSError:
                current_app.logger.exception(
                    "Could not delete rejected completion evidence."
                )

        flash(
            "Complaint approved and resolved."
            if action == "approve"
            else "Complaint returned for further work."
        )

        return redirect(url_for("verification.dashboard"))

    history = History.query.filter_by(
        report_id=report.id
    ).order_by(History.created_at.asc()).all()

    return render_template(
        "verification/review.html",
        report=report,
        history=history
    )

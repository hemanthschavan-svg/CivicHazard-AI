import os

from flask import Blueprint, abort, current_app, send_from_directory
from flask_login import login_required, current_user

from app.models.report import Report

media = Blueprint("media", __name__, url_prefix="/media")


@media.route("/<int:report_id>/<string:kind>")
@login_required
def report_image(report_id, kind):
    report = Report.query.get_or_404(report_id)

    if kind not in ("complaint", "completion"):
        abort(404)

    if current_user.role == "citizen":
        allowed = report.citizen_id == current_user.id

    elif current_user.role == "department_officer":
        allowed = report.assigned_officer_id == current_user.id

    elif current_user.role == "verification_officer":
        allowed = report.status == "Pending Verification"

    elif current_user.role == "admin":
        allowed = True

    else:
        allowed = False

    if not allowed:
        abort(403)

    if kind == "complaint":
        filename = report.image_filename
        folder = os.path.join(
            current_app.config["UPLOAD_FOLDER"], "complaints"
        )
    else:
        filename = report.completion_image
        folder = os.path.join(
            current_app.config["UPLOAD_FOLDER"], "completion_evidence"
        )

    if not filename:
        abort(404)

    response = send_from_directory(folder, filename, as_attachment=False)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app
)
from flask_login import current_user

from app import db
from app.access import roles_required
from app.department_map import DEPARTMENT_IDS
from app.models.user import User
from app.models.report import Report
from app.models.history import History

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/dashboard")
@roles_required("admin")
def dashboard():
    total_reports = Report.query.count()
    total_users = User.query.count()

    pending = Report.query.filter_by(
        status="Pending Verification"
    ).count()

    resolved = Report.query.filter_by(
        status="Resolved"
    ).count()

    reports = Report.query.order_by(
        Report.created_at.desc()
    ).all()

    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    officers = User.query.filter_by(
        role="department_officer",
        is_active=True
    ).order_by(User.full_name.asc()).all()

    return render_template(
        "admin/dashboard.html",
        total_reports=total_reports,
        total_users=total_users,
        pending=pending,
        resolved=resolved,
               reports=reports,
        users=users,
        officers=officers,
        department_ids=DEPARTMENT_IDS
    )


@admin.route("/assign/<int:report_id>", methods=["POST"])
@roles_required("admin")
def assign_report(report_id):
    report = Report.query.get_or_404(report_id)

    if report.status in ("Pending Verification", "Resolved"):
        flash(
            f"Cannot reassign {report.complaint_id} "
            f"because its status is {report.status}."
        )
        return redirect(url_for("admin.dashboard"))

    officer_id = request.form.get("officer_id", type=int)
    officer_id = request.form.get("officer_id", type=int)

    officer = User.query.filter_by(
        id=officer_id,
        role="department_officer",
        is_active=True
    ).first()

    if not officer:
        flash("Select a valid active department officer.")
        return redirect(url_for("admin.dashboard"))

    expected_department_id = DEPARTMENT_IDS.get(report.department)

    if expected_department_id is None:
        flash("This complaint has an unsupported department.")
        return redirect(url_for("admin.dashboard"))

    if officer.department_id != expected_department_id:
        flash(
            f"This complaint belongs to {report.department}. "
            "Select an officer from the correct department."
        )
        return redirect(url_for("admin.dashboard"))

    old_status = report.status
    old_officer_id = report.assigned_officer_id

    report.assigned_officer_id = officer.id
    report.status = "Assigned"

    try:
        db.session.add(History(
            report_id=report.id,
            changed_by=current_user.id,
            old_status=old_status,
            new_status="Assigned",
            remarks=(
                f"Assigned to {officer.full_name} "
                f"({report.department} department)."
            )
        ))

        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Complaint assignment failed.")
        flash("Could not assign the complaint.")
        return redirect(url_for("admin.dashboard"))

    flash(f"{report.complaint_id} assigned successfully.")
    return redirect(url_for("admin.dashboard"))


@admin.route("/user/<int:user_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.")
        return redirect(url_for("admin.dashboard"))

    if user.role == "admin" and user.is_active:
        active_admins = User.query.filter_by(
            role="admin",
            is_active=True
        ).count()

        if active_admins <= 1:
            flash("The last active administrator cannot be deactivated.")
            return redirect(url_for("admin.dashboard"))

    user.is_active = not user.is_active

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("User account update failed.")
        flash("Could not update the account.")
        return redirect(url_for("admin.dashboard"))

    flash("User account updated successfully.")
    return redirect(url_for("admin.dashboard"))

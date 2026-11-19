from flask import Blueprint, redirect, url_for
from flask_login import login_required, current_user

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/dashboard")
@login_required
def index():
    role = current_user.role

    destinations = {
        "citizen": "citizen.dashboard",
        "department_officer": "department.dashboard",
        "verification_officer": "verification.dashboard",
        "admin": "admin.dashboard",
    }

    endpoint = destinations.get(role)

    if endpoint is None:
        return "Your account has an unrecognized role. Contact the administrator.", 403

    return redirect(url_for(endpoint))

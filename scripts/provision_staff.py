import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.models.user import User
from app.department_map import DEPARTMENT_IDS

VALID_ROLES = {
    "1": "admin",
    "2": "department_officer",
    "3": "verification_officer",
}

app = create_app()

def provision():
    print("\n===================================")
    print(" CIVICHAZARD AI - STAFF PROVISION")
    print("===================================")

    email = input("\nEnter the registered account email: ").strip().lower()

    if not email:
        print("Email cannot be empty.")
        return

    user = User.query.filter_by(email=email).first()

    if not user:
        print("Account not found. Register the account first.")
        return

    if not user.is_active:
        print("This account is inactive. Reactivate it through an authorized process first.")
        return

    print("\nSelect role:")
    print("1. Administrator")
    print("2. Department Officer")
    print("3. Verification Officer")

    role_choice = input("Enter choice (1-3): ").strip()
    role = VALID_ROLES.get(role_choice)

    if not role:
        print("Invalid role selection.")
        return

    department_id = None

    if role == "department_officer":
        departments = list(DEPARTMENT_IDS.items())

        print("\nSelect department:")
        for index, (name, department_id_value) in enumerate(departments, 1):
            print(f"{index}. {name}")

        choice = input("Enter department choice: ").strip()

        if not choice.isdigit() or not (1 <= int(choice) <= len(departments)):
            print("Invalid department selection.")
            return

        department_name, department_id = departments[int(choice) - 1]

    else:
        department_name = None

    print("\nAccount selected:", user.full_name)
    print("New role:", role)

    if department_name:
        print("Department:", department_name)

    print("\nThis operation changes the existing account's permissions.")
    confirmation = input("Type YES to confirm: ").strip()

    if confirmation != "YES":
        print("Operation cancelled.")
        return

    user.role = role
    user.department_id = department_id

    try:
        db.session.commit()
        print("\nSUCCESS: Account permissions updated.")
    except Exception:
        db.session.rollback()
        print("\nERROR: Could not update the account.")
        raise

with app.app_context():
    provision()


from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured in the .env file.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from app.models import User, Report, History

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from app.routes import main
    from app.authentication.routes import auth
    from app.citizen.routes import citizen
    from app.dashboard import dashboard
    from app.media import media

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(citizen)
    app.register_blueprint(dashboard)
    app.register_blueprint(media)

    from app.department.routes import department
    from app.verification.routes import verification
    from app.admin.routes import admin

    app.register_blueprint(department)
    app.register_blueprint(verification)
    app.register_blueprint(admin)

    with app.app_context():
        db.create_all()

    return app


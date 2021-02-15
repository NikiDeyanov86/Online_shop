from flask import redirect, url_for
from flask_login import LoginManager
from models import User

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(login_id=user_id).first()


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))

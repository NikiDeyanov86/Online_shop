import uuid
import os

from flask import Flask
from flask import render_template, request, redirect, make_response, url_for
from functools import wraps

from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db_session, init_db
from login import login_manager
from models import User

from datetime import datetime

app = Flask(__name__)
app.secret_key = "ssucuuh398nuwetubr33rcuhne"
login_manager.init_app(app)
init_db()


def admin_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_login'))
        role = login_manager.reload_user().get_role()
        if role != "admin":
            return login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


@app.teardown_appcontext
def shutdown_context(exception=None):
    db_session.remove()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template("register.html")
    else:
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(username=username, email=email, password=password)

        db_session.add(user)
        db_session.commit()

        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('login.html')
    else:
        name_email = request.form['name_email']
        password = request.form['password']

        user = User.query.filter((User.username == name_email) | (
            User.email == name_email)).first()

        if user and check_password_hash(user.password, password):
            user.login_id = str(uuid.uuid4())
            db_session.commit()
            login_user(user)

            return redirect(url_for('home'))


@app.route('/admin')
@admin_login_required
def admin():
    return render_template('admin.html')


@app.route('/admin/register', methods=['GET', 'POST'])
@admin_login_required
def admin_register():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template("admin_register.html")
    else:
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        user = User(username=username, email=email, password=password)

        db_session.add(user)
        db_session.commit()

        return redirect(url_for('admin'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'login_id' in current_user.__dict__:
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('admin_login.html')
    else:
        name_email = request.form['name_email']
        password = request.form['password']

        user = User.query.filter((User.username == name_email) | (
            User.email == name_email)).first()

        if user and check_password_hash(user.password, password):
            user.login_id = str(uuid.uuid4())
            db_session.commit()
            login_user(user)

            return redirect(url_for('admin'))


@ app.route('/logout')
@ login_required
def logout():
    current_user.login_id = None
    db_session.commit()
    logout_user()

    return redirect(url_for('home'))



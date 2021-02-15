import uuid
import os

from flask import Flask
from flask import render_template, request, redirect, make_response, url_for

from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db_session, init_db
# from login import login_manager
# from models import

from datetime import datetime

app = Flask(__name__)
app.secret_key = "ssucuuh398nuwetubr33rcuhne"
# login_manager.init_app(app)
init_db()


@app.teardown_appcontext
def shutdown_context(exception=None):
    db_session.remove()


@app.route('/')
def home():
    return render_template('index.html')

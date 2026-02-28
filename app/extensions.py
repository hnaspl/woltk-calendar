"""Shared Flask extension instances (imported by models and app factory)."""

from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()
login_manager: LoginManager = LoginManager()
bcrypt: Bcrypt = Bcrypt()

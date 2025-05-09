import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv, find_dotenv
import secrets

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    migrate = Migrate(app, db)

    CORS(app)

    load_dotenv(find_dotenv())

    # Configure PostgreSQL database connection
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/bookings_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure secret key for JWT
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(16))

    db.init_app(app)

    from .bookingsbp import bookingsbp as bookings_blueprint
    app.register_blueprint(bookings_blueprint)

    from .authbp import authbp as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .agentsbp import agentsbp as agents_blueprint
    app.register_blueprint(agents_blueprint)

    return app


app = create_app()

with app.app_context():
    # db.drop_all()
    db.create_all()
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv, find_dotenv

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    CORS(app)

    load_dotenv(find_dotenv())

    # Configure SQLite database connection
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///dbname.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from .bookingsbp import bookingsbp as bookings_blueprint

    app.register_blueprint(bookings_blueprint)

    return app


app = create_app()


with app.app_context():
    db.create_all()
    # db.drop_all()


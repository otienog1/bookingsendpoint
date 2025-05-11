import os
import logging
import traceback
from flask import Flask, request, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv, find_dotenv
from app_logging import configure_logging
import secrets
import uuid

db = SQLAlchemy()


def create_app():
    app_ = Flask(__name__)
    migrate = Migrate(app_, db)

    CORS(app_)

    load_dotenv(find_dotenv())

    # Configure PostgreSQL database connection
    app_.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/bookings_db"
    )
    app_.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    # Add SQLAlchemy echo for debugging if needed
    app_.config["SQLALCHEMY_ECHO"] = False

    # Configure secret key for JWT
    app_.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(16))

    # Configure logging first
    configure_logging(app_)

    # Set request ID for each request
    @app_.before_request
    def before_request():
        g.request_id = str(uuid.uuid4())[:8]
        app_.logger.debug(f"New request: {request.method} {request.path} - Request ID: {g.request_id}")

    # Add request ID to logger
    @app_.after_request
    def after_request(response):
        request_id = getattr(g, 'request_id', 'no-request-id')
        app_.logger.debug(f"Request {request_id} completed with status code {response.status_code}")

        if hasattr(logging, 'LogRecord'):
            old_factory = logging.getLogRecordFactory()

            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.request_id = request_id
                return record

            logging.setLogRecordFactory(record_factory)

        return response

    # Log unhandled exceptions
    @app_.errorhandler(Exception)
    def handle_exception(e):
        app_.logger.error(f"Unhandled exception: {str(e)}")
        app_.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

    # Setup database
    db.init_app(app_)

    from .bookingsbp import bookingsbp as bookings_blueprint
    app_.register_blueprint(bookings_blueprint)

    from .authbp import authbp as auth_blueprint
    app_.register_blueprint(auth_blueprint)

    from .agentsbp import agentsbp as agents_blueprint
    app_.register_blueprint(agents_blueprint)

    # Log successful initialization
    app_.logger.info("Application initialized successfully")

    # Debug path - can be accessed to trigger test logs for verification
    @app_.route('/debug/test-logging', methods=['GET'])
    def test_logging():
        app_.logger.debug("This is a DEBUG log")
        app_.logger.info("This is an INFO log")
        app_.logger.warning("This is a WARNING log")
        app_.logger.error("This is an ERROR log")
        try:
            raise ValueError("Test exception")
        except Exception as e:
            app_.logger.exception("This is an EXCEPTION log")
        return jsonify({"status": "Logging test complete"})

    return app_


app = create_app()

# with app.app_context():
    # db.drop_all()
    # db.create_all()
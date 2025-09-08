import logging
import traceback
from flask import Flask, request, g, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
from app_logging import configure_logging
import uuid

# Import configuration
from config import get_config

mongo = PyMongo()

def create_app():
    app_ = Flask(__name__)

    # Load configuration based on environment
    app_.config.from_object(get_config())

    # Initialize extensions
    mongo.init_app(app_)

    # Configure CORS with settings from config
    CORS(app_,
         origins=app_.config.get('CORS_ALLOWED_ORIGINS', ['*']),
         supports_credentials=app_.config.get('CORS_ALLOW_CREDENTIALS', True))

    # Configure logging
    configure_logging(app_)

    # Set request ID for each request
    @app_.before_request
    def before_request():
        g.request_id = str(uuid.uuid4())[:8]
        app_.logger.debug(f"New request: {request.method} {request.path} - Request ID: {g.request_id}")

    # Set up logging record factory once
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        try:
            record.request_id = getattr(g, 'request_id', 'no-request-id')
        except RuntimeError:
            # Outside of application context
            record.request_id = 'no-request-id'
        return record

    logging.setLogRecordFactory(record_factory)

    # Add request ID to logger
    @app_.after_request
    def after_request(response):
        request_id = getattr(g, 'request_id', 'no-request-id')
        app_.logger.debug(f"Request {request_id} completed with status code {response.status_code}")
        return response

    # Log unhandled exceptions
    @app_.errorhandler(Exception)
    def handle_exception(e):
        app_.logger.error(f"Unhandled exception: {str(e)}")
        app_.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

    # Register blueprints
    from .bookingsbp import bookingsbp as bookings_blueprint
    app_.register_blueprint(bookings_blueprint)

    from .authbp import authbp as auth_blueprint
    app_.register_blueprint(auth_blueprint)

    from .agentsbp import agentsbp as agents_blueprint
    app_.register_blueprint(agents_blueprint)

    # Log successful initialization with config info
    app_.logger.info(f"Application initialized successfully in {app_.config.get('ENV', 'development')} mode")
    app_.logger.info(
        f"Token durations - Access: {app_.config['ACCESS_TOKEN_DURATION']}, Refresh: {app_.config['REFRESH_TOKEN_DURATION']}")

    # Optional: Initialize Redis for token blacklisting
    if app_.config.get('ENABLE_TOKEN_BLACKLIST'):
        try:
            import redis
            app_.redis = redis.from_url(app_.config['REDIS_URL'])
            app_.logger.info("Redis connected for token blacklisting")
        except Exception as e:
            app_.logger.error(f"Redis connection failed: {e}")
            app_.redis = None

    # Debug endpoints
    @app_.route('/debug/config', methods=['GET'])
    def debug_config():
        """Show current configuration (remove in production)"""
        if app_.debug:
            return jsonify({
                'environment': app_.config.get('ENV', 'unknown'),
                'debug': app_.debug,
                'access_token_duration': str(app_.config['ACCESS_TOKEN_DURATION']),
                'refresh_token_duration': str(app_.config['REFRESH_TOKEN_DURATION']),
                'remember_access_duration': str(app_.config['REMEMBER_ACCESS_TOKEN_DURATION']),
                'remember_refresh_duration': str(app_.config['REMEMBER_REFRESH_TOKEN_DURATION']),
                'cors_origins': app_.config.get('CORS_ALLOWED_ORIGINS', [])
            })
        return jsonify({'error': 'Not available in production'}), 404

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

# MongoDB will create collections automatically when first document is inserted
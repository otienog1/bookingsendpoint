import os
import logging
from logging.handlers import RotatingFileHandler
from flask import request, g


class RequestFormatter(logging.Formatter):
    """Custom formatter to include request information"""

    def format(self, record):
        record.url = request.url if request else 'No request'
        record.method = request.method if request else 'No method'
        record.ip = request.remote_addr if request else 'No IP'
        record.request_id = getattr(g, 'request_id', 'no-request-id') if g else 'no-request-id'
        return super().format(record)


def configure_logging(app):
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Set up log file handler with rotation
    log_file = os.path.join(logs_dir, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)

    # Define log format for file handler
    file_formatter = RequestFormatter(
        '[%(asctime)s] [%(request_id)s] [%(levelname)s] [%(ip)s] [%(method)s] [%(url)s] - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # Define console handler for development
    console_handler = logging.StreamHandler()
    console_formatter = RequestFormatter(
        '%(asctime)s [%(request_id)s] %(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)

    # Configure Flask app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # Add SQLAlchemy logging if needed
    if app.config.get('SQLALCHEMY_ECHO', False):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.engine').addHandler(file_handler)

    # Flask will use the app logger for its own messages
    app.logger.info('Logging configured successfully')
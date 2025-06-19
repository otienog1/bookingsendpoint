# config.py - Place this in your root directory
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration"""
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/bookings_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    # Token Durations
    ACCESS_TOKEN_DURATION = timedelta(
        seconds=int(os.getenv("ACCESS_TOKEN_DURATION", 86400))  # 24 hours default
    )
    REFRESH_TOKEN_DURATION = timedelta(
        seconds=int(os.getenv("REFRESH_TOKEN_DURATION", 604800))  # 7 days default
    )
    REMEMBER_ACCESS_TOKEN_DURATION = timedelta(
        seconds=int(os.getenv("REMEMBER_ACCESS_TOKEN_DURATION", 604800))  # 7 days default
    )
    REMEMBER_REFRESH_TOKEN_DURATION = timedelta(
        seconds=int(os.getenv("REMEMBER_REFRESH_TOKEN_DURATION", 2592000))  # 30 days default
    )

    # Security Settings
    TOKEN_REFRESH_WINDOW = int(os.getenv("TOKEN_REFRESH_WINDOW", 300))  # 5 minutes
    MAX_REFRESH_ATTEMPTS = int(os.getenv("MAX_REFRESH_ATTEMPTS", 3))
    REFRESH_COOLDOWN = int(os.getenv("REFRESH_COOLDOWN", 60))

    # Redis (optional for token blacklisting)
    REDIS_URL = os.getenv("REDIS_URL", None)
    ENABLE_TOKEN_BLACKLIST = os.getenv("ENABLE_TOKEN_BLACKLIST", "False").lower() == "true"

    # CORS
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    CORS_ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000"
    ).split(",")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # Shorter token durations for testing
    # ACCESS_TOKEN_DURATION = timedelta(minutes=5)  # Uncomment for testing


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

    # Enforce secure cookies in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Require SECRET_KEY in production
    if not os.getenv("SECRET_KEY"):
        raise ValueError("SECRET_KEY must be set in production!")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

    # Shorter durations for testing
    ACCESS_TOKEN_DURATION = timedelta(minutes=5)
    REFRESH_TOKEN_DURATION = timedelta(minutes=30)
    REMEMBER_ACCESS_TOKEN_DURATION = timedelta(minutes=10)
    REMEMBER_REFRESH_TOKEN_DURATION = timedelta(hours=1)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
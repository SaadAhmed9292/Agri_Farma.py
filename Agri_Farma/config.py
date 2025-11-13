# config.py — AgriFarma configuration
# Usage:
#   from config import get_config
#   app.config.from_object(get_config())

import os
from datetime import timedelta

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")

def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB = f"sqlite:///{os.path.join(BASE_DIR, 'agrifarma.db')}"

class BaseConfig:
    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "agrifarma_session")
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "http")

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DB)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }

    # Security
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    WTF_CSRF_ENABLED = True

    # Uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))
    MAX_CONTENT_LENGTH = env_int("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    # Email (for password reset integration)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = env_int("MAIL_PORT", 587)
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # Pagination defaults
    DEFAULT_PER_PAGE = env_int("DEFAULT_PER_PAGE", 12)

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = env_bool("SQLALCHEMY_ECHO", False)

class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SESSION_COOKIE_SECURE = False

class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"

def get_config():
    env = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    if env in ("prod", "production"):
        return ProductionConfig
    if env in ("test", "testing", "ci"):
        return TestingConfig
    return DevelopmentConfig

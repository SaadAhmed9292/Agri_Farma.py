# passwords.py — Password reset token helpers using itsdangerous
# Usage:
#   from passwords import generate_reset_token, verify_reset_token
#   token = generate_reset_token(email)
#   email = verify_reset_token(token, max_age=3600)

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

RESET_SALT = 'agrifarma-reset'

def _serializer():
    # Uses Flask SECRET_KEY; ensure app context is active when calling
    secret = current_app.config.get('SECRET_KEY')
    return URLSafeTimedSerializer(secret)

def generate_reset_token(email: str) -> str:
    """Create a time-limited token encoding the user email."""
    return _serializer().dumps(email, salt=RESET_SALT)

def verify_reset_token(token: str, max_age: int = 3600):
    """
    Validate the token and return the email if valid.
    max_age is in seconds (default 1 hour).
    """
    try:
        email = _serializer().loads(token, salt=RESET_SALT, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None

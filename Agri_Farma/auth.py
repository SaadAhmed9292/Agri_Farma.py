
# auth.py - decorators for role checks
from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*role_names):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            user_roles = {r.name for r in current_user.roles}
            if not any(r in user_roles for r in role_names):
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator

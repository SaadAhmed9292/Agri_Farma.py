# uploads.py — File upload utilities for AgriFarma
# Usage:
#   from uploads import save_upload, allowed_image
#   path = save_upload(file, app.config['UPLOAD_FOLDER'], 'products')

import os
from typing import Optional
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB safety check

def allowed_image(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS

def _within_size_limit(file) -> bool:
    # Some servers provide content_length; otherwise, read size in memory (avoid for very large files)
    length = getattr(file, 'content_length', None)
    if length is not None:
        return length <= MAX_IMAGE_SIZE
    try:
        pos = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(pos)
        return size <= MAX_IMAGE_SIZE
    except Exception:
        # If size detection fails, allow it and rely on Flask MAX_CONTENT_LENGTH
        return True

def save_upload(file, upload_root: str, subfolder: str = '') -> Optional[str]:
    """
    Saves an uploaded file under upload_root/subfolder and returns a web path like '/static/uploads/...'
    Returns None if invalid.
    """
    if not file or not getattr(file, 'filename', ''):
        return None

    filename = secure_filename(file.filename)
    if not allowed_image(filename):
        return None
    if not _within_size_limit(file):
        return None

    folder = os.path.join(upload_root, subfolder) if subfolder else upload_root
    os.makedirs(folder, exist_ok=True)

    # Avoid collisions by prefixing a counter if needed
    base, ext = os.path.splitext(filename)
    target = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(target):
        filename = f"{base}_{counter}{ext}"
        target = os.path.join(folder, filename)
        counter += 1

    file.save(target)

    # Convert filesystem path to web path for templates
    # e.g., 'static/uploads/products/img.jpg' -> '/static/uploads/products/img.jpg'
    web_path = target.replace('\\', '/')
    if 'static/' in web_path:
        web_path = '/' + web_path.split('static/', 1)[1]
        web_path = '/static/' + web_path.split('/static/', 1)[-1] if not web_path.startswith('/static/') else web_path
    else:
        # Fallback: if UPLOAD_ROOT not under static, return absolute path (you may serve via send_from_directory)
        web_path = target
    return web_path

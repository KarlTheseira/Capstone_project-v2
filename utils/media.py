import os
from werkzeug.utils import secure_filename
from uuid import uuid4

UPLOAD_FOLDER = "static/uploads"

def save_media(file):
    """
    Saves an uploaded file to the static/uploads folder.
    Returns (filename, file_url).
    """
    if not file:
        return None, None

    ext = os.path.splitext(file.filename)[1]
    filename = secure_filename(f"{uuid4().hex}{ext}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(filepath)

    file_url = f"/{filepath}"
    return filename, file_url

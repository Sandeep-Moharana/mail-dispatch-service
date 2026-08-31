import os
import uuid
from werkzeug.utils import secure_filename

# Strict allowlist of file extensions to prevent executable uploads
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'csv', 'txt'}

def allowed_file(filename):
    """Checks if the file extension is strictly within the allowlist."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_and_save(file, upload_folder):
    """
    Sanitizes the filename, ensures uniqueness, and saves it to the secure temp directory.
    Returns the absolute path to the saved file, or None if invalid.
    """
    if file and allowed_file(file.filename):
        # Strip dangerous characters (prevents directory traversal attacks)
        safe_filename = secure_filename(file.filename)
        
        # Append a UUID to prevent naming collisions if multiple clients 
        # upload a file named "report.pdf" at the exact same millisecond
        unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
        
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Save the file to the local disk buffer
        file.save(file_path)
        return file_path
        
    return None
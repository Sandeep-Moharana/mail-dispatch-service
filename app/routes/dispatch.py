from flask import Blueprint, request, jsonify, current_app
from app.services.auth import verify_token
from app.services.db_queue import queue_email_job
from app.utils.security import sanitize_and_save

# Create a Blueprint for our API routing
dispatch_bp = Blueprint('dispatch', __name__)

@dispatch_bp.route('/api/v1/mail/dispatch', methods=['POST'])
def dispatch_mail():
    # 1. Authentication (The Bouncer)
    auth_header = request.headers.get('Authorization')
    is_valid, auth_result = verify_token(auth_header)
    
    if not is_valid:
        return jsonify({"error": "Unauthorized", "details": auth_result}), 401

    # 2. Extract Metadata
    recipient = request.form.get('to')
    subject = request.form.get('subject')
    body = request.form.get('body', '') # Body is optional

    if not recipient or not subject:
        return jsonify({"error": "Bad Request", "details": "Missing 'to' or 'subject' field"}), 400

    # 3. Process Attachments securely
    saved_file_paths = []
    # request.files.getlist handles multiple files sent under the 'attachments' key
    uploaded_files = request.files.getlist('attachments')
    
    for file in uploaded_files:
        if file.filename == '':
            continue
            
        saved_path = sanitize_and_save(file, current_app.config['TEMP_UPLOAD_FOLDER'])
        if saved_path:
            saved_file_paths.append(saved_path)
        else:
            return jsonify({"error": "Bad Request", "details": f"Invalid or dangerous file detected: {file.filename}"}), 400

    # 4. Ingest into the Queue (MySQL)
    try:
        job_id = queue_email_job(recipient, subject, body, saved_file_paths)
        return jsonify({
            "status": "queued",
            "job_id": job_id,
            "message": "Email job successfully ingested into the dispatch queue."
        }), 202
    except Exception as e:
        # In a true enterprise app, you'd log the actual exception but return a generic 500 to the client
        return jsonify({"error": "Internal Server Error", "details": "Failed to queue job"}), 500
import time
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.services.db_queue import get_queued_jobs, update_job_status
from app.config import Config

def send_email(to_address, subject, body, attachment_paths):
    """Handles the actual SMTP handshake and MIME construction."""
    msg = MIMEMultipart()
    msg['From'] = Config.SMTP_USER
    msg['To'] = to_address
    msg['Subject'] = subject

    # Attach the email body
    if body:
        msg.attach(MIMEText(body, 'html'))

    # Process and attach files
    for file_path in attachment_paths:
        if os.path.exists(file_path):
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            # Extract just the original filename, ignoring our secure prefix UUID if desired
            filename = os.path.basename(file_path)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)

    # Dispatch via SMTP
    server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
    try:
        server.starttls()  # Upgrade the connection to secure TLS
        server.login(Config.SMTP_USER, Config.SMTP_APP_PASSWORD)
        server.send_message(msg)
    finally:
        server.quit()

def process_queue():
    """Continuously polls the database and dispatches emails."""
    print("Background worker started. Polling for queued emails...")
    
    while True:
        try:
            jobs = get_queued_jobs(limit=5)
            
            if not jobs:
                time.sleep(5) # Pause for 5 seconds before checking again
                continue
                
            for job in jobs:
                log_id = job['log_id']
                recipient = job['recipient_email']
                subject = job['subject']
                body = job['body']
                attachments = json.loads(job['attachments']) # Decode JSON back to a Python list
                
                print(f"Processing Job ID {log_id} for {recipient}...")
                
                try:
                    # 1. Send the email
                    send_email(recipient, subject, body, attachments)
                    
                    # 2. Update status to Sent
                    update_job_status(log_id, 'Sent')
                    print(f"Job ID {log_id} successfully sent.")
                    
                    # 3. Clean up temporary files to save disk space
                    for file_path in attachments:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            
                except Exception as e:
                    print(f"Failed to process Job ID {log_id}: {e}")
                    update_job_status(log_id, 'Failed')
                    
        except Exception as queue_error:
            print(f"Database connection error: {queue_error}")
            time.sleep(10) # Back off if the database goes down

if __name__ == '__main__':
    # Execute the infinite polling loop
    process_queue()
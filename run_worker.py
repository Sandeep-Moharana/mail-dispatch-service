import time
import json
import os
import smtplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.services.db_queue import fetch_and_lock_jobs, update_job_status, reclaim_zombie_jobs
from app.config import Config

MAX_WORKER_THREADS = 5

def process_single_job(job):
    """Isolated function executed by an individual worker thread."""
    log_id = job['log_id']
    recipient = job['recipient_email']
    subject = job['subject']
    body = job['body']
    current_retries = job['retry_count']
    attachments = json.loads(job['attachments'])
    
    print(f"[Thread] Processing Job ID {log_id} (Attempt {current_retries + 1}) for {recipient}...")
    
    msg = MIMEMultipart()
    msg['From'] = Config.SMTP_USER
    msg['To'] = recipient
    msg['Subject'] = subject

    if body:
        msg.attach(MIMEText(body, 'html'))

    for file_path in attachments:
        if os.path.exists(file_path):
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            filename = os.path.basename(file_path)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)

    try:
        server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        update_job_status(log_id, current_retries, success=True)
        print(f"[Thread] Job ID {log_id} successfully sent.")
        
        for file_path in attachments:
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print(f"[Thread] Failed to process Job ID {log_id}: {e}")
        update_job_status(log_id, current_retries, success=False)

def process_queue_parallel():
    print(f"Parallel worker started with {MAX_WORKER_THREADS} threads. Polling database...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS) as executor:
        while True:
            try:
                # 1. Reclaim any jobs that crashed mid-processing in previous cycles
                reclaim_zombie_jobs(timeout_minutes=10)
                
                # 2. Fetch exactly the amount of jobs as available threads
                jobs = fetch_and_lock_jobs(limit=MAX_WORKER_THREADS)
                
                if not jobs:
                    time.sleep(5)
                    continue
                
                # 3. Dispatch batch to thread pool
                futures = [executor.submit(process_single_job, job) for job in jobs]
                
                # Block the main loop until this specific batch finishes 
                for future in as_completed(futures):
                    future.result() 
                    
            except Exception as queue_error:
                print(f"Database connection error: {queue_error}")
                time.sleep(10)

if __name__ == '__main__':
    process_queue_parallel()
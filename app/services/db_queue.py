import pymysql
import json
from app.config import Config

def get_db_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False # Disabled for row locking
    )

def init_db():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS Dispatch_Audit_Log (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                body TEXT,
                attachments TEXT, 
                status ENUM('Queued', 'Processing', 'Sent', 'Failed', 'Dead_Letter') DEFAULT 'Queued',
                retry_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql)
        connection.commit()
    finally:
        connection.close()

def queue_email_job(recipient, subject, body, attachment_paths):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO Dispatch_Audit_Log (recipient_email, subject, body, attachments, status)
            VALUES (%s, %s, %s, %s, 'Queued')
            """
            attachments_json = json.dumps(attachment_paths)
            cursor.execute(sql, (recipient, subject, body, attachments_json))
            job_id = cursor.lastrowid
        connection.commit()
        return job_id
    finally:
        connection.close()

def fetch_and_lock_jobs(limit=5):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql_select = """
                SELECT * FROM Dispatch_Audit_Log 
                WHERE status IN ('Queued', 'Failed') AND retry_count < 3 
                LIMIT %s FOR UPDATE SKIP LOCKED
            """
            cursor.execute(sql_select, (limit,))
            jobs = cursor.fetchall()
            
            if not jobs:
                connection.commit()
                return []
                
            job_ids = [job['log_id'] for job in jobs]
            format_strings = ','.join(['%s'] * len(job_ids))
            sql_update = f"UPDATE Dispatch_Audit_Log SET status = 'Processing' WHERE log_id IN ({format_strings})"
            
            cursor.execute(sql_update, tuple(job_ids))
            connection.commit()
            return jobs
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        connection.close()

def reclaim_zombie_jobs(timeout_minutes=10):
    """Finds jobs stuck in 'Processing' and resets them to 'Failed' for a retry."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                UPDATE Dispatch_Audit_Log 
                SET status = 'Failed', retry_count = retry_count + 1
                WHERE status = 'Processing' AND updated_at < (NOW() - INTERVAL %s MINUTE)
            """
            cursor.execute(sql, (timeout_minutes,))
        connection.commit()
    finally:
        connection.close()

def update_job_status(log_id, current_retries, success=True):
    connection = get_db_connection()
    try:
        if success:
            new_status = 'Sent'
            new_retries = current_retries
        else:
            new_retries = current_retries + 1
            new_status = 'Failed' if new_retries < 3 else 'Dead_Letter'
            
        with connection.cursor() as cursor:
            sql = "UPDATE Dispatch_Audit_Log SET status = %s, retry_count = %s WHERE log_id = %s"
            cursor.execute(sql, (new_status, new_retries, log_id))
        connection.commit()
    finally:
        connection.close()
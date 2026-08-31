import pymysql
import json
from app.config import Config

def get_db_connection():
    """Establishes and returns a fresh connection to the MySQL database."""
    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    """Initializes the database schema if it does not already exist."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # We use TEXT for attachments to store a JSON array of file paths
            sql = """
            CREATE TABLE IF NOT EXISTS Dispatch_Audit_Log (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                body TEXT,
                attachments TEXT, 
                status ENUM('Queued', 'Sent', 'Failed') DEFAULT 'Queued',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(sql)
        connection.commit()
    finally:
        connection.close()

def queue_email_job(recipient, subject, body, attachment_paths):
    """API Gateway uses this to insert a new job into the queue."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO Dispatch_Audit_Log (recipient_email, subject, body, attachments, status)
            VALUES (%s, %s, %s, %s, 'Queued')
            """
            # Serialize the Python list of paths into a JSON string for MySQL
            attachments_json = json.dumps(attachment_paths)
            cursor.execute(sql, (recipient, subject, body, attachments_json))
            job_id = cursor.lastrowid
        connection.commit()
        return job_id
    finally:
        connection.close()

def get_queued_jobs(limit=10):
    """Background worker uses this to fetch the next batch of emails."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM Dispatch_Audit_Log WHERE status = 'Queued' LIMIT %s"
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        connection.close()

def update_job_status(log_id, new_status):
    """Background worker uses this to mark a job as Sent or Failed."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE Dispatch_Audit_Log SET status = %s WHERE log_id = %s"
            cursor.execute(sql, (new_status, log_id))
        connection.commit()
    finally:
        connection.close()
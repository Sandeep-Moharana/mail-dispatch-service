import os
from dotenv import load_dotenv
import tempfile

load_dotenv()

class Config:
    # Flask Core
    SECRET_KEY = os.getenv("FLASK_SECRET", "default_flask_fallback_secret")
    
    # Security constraints (16 MB limit to prevent memory exhaustion DoS)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", 16)) * 1024 * 1024 
    JWT_SECRET = os.getenv("JWT_SECRET")
    
    # Database Connectors
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "mail_dispatch_db")
    
    # SMTP Protocol
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
    
    # Cross-platform secure temporary directory mapping
    # Uses Windows Temp on your local machine, /tmp on Linux production
    TEMP_UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "secure_docs")
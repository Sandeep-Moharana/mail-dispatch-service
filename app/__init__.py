import os
from flask import Flask
from app.config import Config

def create_app():
    """Construct the core application."""
    app = Flask(__name__)
    
    # Load the centralized configuration
    app.config.from_object(Config)

    # Ensure the secure temporary directory exists on server start
    os.makedirs(app.config['TEMP_UPLOAD_FOLDER'], exist_ok=True)

    return app
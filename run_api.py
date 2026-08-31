from app import create_app
from app.routes.dispatch import dispatch_bp
from app.services.db_queue import init_db

# Construct the core Flask application
app = create_app()

# Register the API routes
app.register_blueprint(dispatch_bp)

if __name__ == '__main__':
    print("Initializing Database Schema...")
    init_db()
    
    print("Starting Secure Mail Dispatch API...")
    # Run the server on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
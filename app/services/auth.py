import jwt
from flask import current_app

def verify_token(auth_header):
    """
    Verifies the JWT token from the Authorization header.
    Returns a tuple: (is_valid: bool, result: dict/str)
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, "Missing or invalid Authorization header format."
    
    # Extract the token by stripping the "Bearer " prefix
    token = auth_header.split(" ")[1]
    
    try:
        # Enforcing HS256 explicitly 
        decoded_payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET'],
            algorithms=["HS256"]
        )
        return True, decoded_payload
        
    except jwt.ExpiredSignatureError:
        return False, "Token has expired."
    except jwt.InvalidTokenError:
        return False, "Invalid or tampered token signature."
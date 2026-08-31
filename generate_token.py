import jwt
import os
from dotenv import load_dotenv

load_dotenv()
secret = os.getenv("JWT_SECRET")

# Create a payload representing a dummy authorized client (e.g., the Threat Detection Service)
payload = {
    "client_id": "test_client_001",
    "role": "admin"
}

# Sign the token using HS256 and your .env secret
token = jwt.encode(payload, secret, algorithm="HS256")

print("\nCopy this token into Thunder Client:")
print(f"Bearer {token}\n")
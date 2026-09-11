import os
import time
import requests
import jwt
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

API_URL = "http://127.0.0.1:5000/api/v1/mail/dispatch"
SECRET_KEY = os.getenv("JWT_SECRET")
TARGET_EMAIL = "your-email-id@gmail.com" 
TOTAL_REQUESTS = 15

def generate_auth_token():
    payload = {"client_id": "load_tester_99", "role": "admin"}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def send_mock_request(request_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "to": TARGET_EMAIL,
        "subject": f"Parallel Load Test #{request_id}",
        "body": f"This is automated test payload #{request_id} simulating high-volume traffic."
    }
    
    # Create a temporary dummy file in memory for the attachment
    files = {
        "attachments": (f"dummy_report_{request_id}.txt", b"Mock secure data", "text/plain")
    }
    
    try:
        response = requests.post(API_URL, headers=headers, data=data, files=files)
        return f"Request {request_id}: {response.status_code} - {response.json()}"
    except Exception as e:
        return f"Request {request_id} Failed: {e}"

def run_load_test():
    token = generate_auth_token()
    print(f"Firing {TOTAL_REQUESTS} concurrent requests to the API...\n")
    
    start_time = time.time()
    
    # Fire all requests at the exact same time
    with ThreadPoolExecutor(max_workers=TOTAL_REQUESTS) as executor:
        futures = [executor.submit(send_mock_request, i, token) for i in range(1, TOTAL_REQUESTS + 1)]
        
        for future in as_completed(futures):
            print(future.result())
            
    print(f"\nLoad generation finished in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    run_load_test()
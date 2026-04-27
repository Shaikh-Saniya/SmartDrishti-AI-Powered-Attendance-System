import requests
from io import BytesIO

url = "http://127.0.0.1:8000/api/v1/attendance/process-group"
# We need to get a token first
auth_url = "http://127.0.0.1:8000/api/v1/auth/login"
data = {"username": "saniya.shaikh@gmail.com", "password": "password"} # I'll assume standard test creds

try:
    print("Logging in...")
    r = requests.post(auth_url, data=data)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        token = "dummy"
    else:
        token = r.json()["access_token"]
        print("Logged in")

    print("Uploading file...")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": ("test.jpg", BytesIO(b"test"), "image/jpeg")}
    data = {"subject": "Math"}
    
    # Try an OPTIONS request first
    print("Sending OPTIONS request...")
    opt = requests.options(url, headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization"})
    print(f"OPTIONS status: {opt.status_code}")
    print(f"OPTIONS headers: {opt.headers}")

    print("Sending POST request...")
    r = requests.post(url, headers=headers, files=files, data=data)
    print(f"POST status: {r.status_code}")
    print(f"POST response: {r.text}")

except Exception as e:
    print(f"Error: {e}")

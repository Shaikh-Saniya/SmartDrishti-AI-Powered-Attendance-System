import requests
import time
import os

BASE = 'http://localhost:8000/api/v1'

def main():
    print("Fetching a test face image...")
    import shutil
    shutil.copy(r'C:\Dristhi-main\backend\uploads\student_images\0f2c656d-02f8-4a14-9d6d-4e00de82da4e_20260426_162505_b0097d89.jpg', 'test_face.jpg')
        
    print("Logging in...")
    login_resp = requests.post(f'{BASE}/auth/login', data={'username': 'admin@example.com', 'password': 'admin123'})
    token = login_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("Registering a student with the face image...")
    student_data = {
        'roll_number': 'ML007',
        'name': 'ML Test Student 2',
        'class_name': 'ML Class'
    }
    with open('test_face.jpg', 'rb') as f:
        files = {
            'image': ('test_face.jpg', f, 'image/jpeg')
        }
        resp = requests.post(f'{BASE}/students', data=student_data, files=files, headers=headers)
    
    print(f"Student Registration Status: {resp.status_code}")
    if resp.status_code != 201:
        print(resp.text)
        return
        
    student_id = resp.json()['id']
    print(f"Student created with ID: {student_id}")
    
    print("Processing group attendance with the same image...")
    with open('test_face.jpg', 'rb') as f:
        files = {
            'image': ('group.jpg', f, 'image/jpeg')
        }
        data = {
            'subject': 'ML Testing',
            'date': '2026-04-14'
        }
        resp = requests.post(f'{BASE}/attendance/process-group', data=data, files=files, headers=headers)
        
    print(f"Process Group Status: {resp.status_code}")
    if resp.status_code != 202:
        print(resp.text)
        return
        
    task_id = resp.json()['id']
    print(f"Task created with ID: {task_id}")
    
    print("Polling task status...")
    for _ in range(30):
        time.sleep(1)
        resp = requests.get(f'{BASE}/tasks/{task_id}/status', headers=headers)
        status_data = resp.json()
        print(f"Status: {status_data['status']}")
        if status_data['status'] in ['completed', 'failed']:
            print("Final Result:", status_data)
            break
            
    # Cleanup
    print("Cleaning up...")
    requests.delete(f'{BASE}/students/{student_id}', headers=headers)
    if os.path.exists('test_face.jpg'):
        os.remove('test_face.jpg')

if __name__ == '__main__':
    main()

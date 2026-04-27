import hashlib
import os

dir_path = "uploads/student_images"
files = [f for f in os.listdir(dir_path) if f.endswith('.jpg')]
for f in files:
    h = hashlib.md5(open(os.path.join(dir_path, f), 'rb').read()).hexdigest()
    print(f"{f}: {h}")

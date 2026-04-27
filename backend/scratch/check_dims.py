import cv2
import os

dir_path = "uploads/student_images"
files = [f for f in os.listdir(dir_path) if f.endswith('.jpg')]
for f in files:
    path = os.path.join(dir_path, f)
    img = cv2.imread(path)
    if img is not None:
        print(f"{f}: {img.shape}")
    else:
        print(f"{f}: Failed to load")

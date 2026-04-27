import cv2
import numpy as np
import os
from app.ml.insightface_loader import face_analyzer
from app.core.config import settings

def test_embeddings():
    # Load model
    face_analyzer.load_model(
        model_name=settings.INSIGHTFACE_MODEL_NAME,
        model_root=settings.INSIGHTFACE_ROOT,
    )
    
    img_dir = "uploads/student_images"
    files = [f for f in os.listdir(img_dir) if f.endswith(".jpg")][:3]
    
    for f in files:
        path = os.path.join(img_dir, f)
        print(f"\nProcessing: {path}")
        
        img = cv2.imread(path)
        if img is None:
            print("Failed to read image")
            continue
            
        faces = face_analyzer.detect_faces(img, min_confidence=0.01)
        print(f"Detected {len(faces)} faces (at 0.01 threshold)")
        
        # Check actual scores
        actual_faces = [f for f in faces if f.det_score >= 0.5]
        print(f"Detected {len(actual_faces)} faces (at 0.5 threshold)")
        
        if faces:
            emb = face_analyzer.get_embedding(faces[0])
            print(f"Embedding (first 5): {emb[:5]}")
            print(f"Norm: {np.linalg.norm(emb)}")

if __name__ == "__main__":
    test_embeddings()

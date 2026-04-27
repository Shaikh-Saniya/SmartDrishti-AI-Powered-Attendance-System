import traceback
import sys
import os

# Ensure backend root is in path
sys.path.append(os.getcwd())

try:
    from app.ml.insightface_loader import face_analyzer
    print("Attempting to load model...")
    face_analyzer.load_model()
    print("SUCCESS: Model loaded")
except Exception:
    print("FAILURE: Model loading failed")
    traceback.print_exc()

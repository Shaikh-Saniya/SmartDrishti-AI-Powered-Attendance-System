"""
End-to-end face recognition sanity test.
This script:
1. Loads two registered student images from disk
2. Generates embeddings for both images using the same model
3. Computes cosine similarity between them
4. Compares the STORED embedding from DB to the freshly computed one

This tells us definitively if the model or the DB is the problem.
"""
import asyncio
import json
import os
import cv2
import numpy as np
from sqlalchemy import text
from app.db.session import async_session_factory
from app.ml.insightface_loader import face_analyzer
from app.core.config import settings


async def run_sanity_test():
    # 1. Load model
    face_analyzer.load_model(
        model_name=settings.INSIGHTFACE_MODEL_NAME,
        model_root=settings.INSIGHTFACE_ROOT,
    )
    
    img_dir = "uploads/student_images"
    files = sorted([f for f in os.listdir(img_dir) if f.endswith(".jpg")])
    
    if not files:
        print("ERROR: No student images found in uploads/student_images!")
        print("Please register students first, then run this test.")
        return

    print(f"\nFound {len(files)} student images.\n")

    # 2. Test: compute embeddings from two different photos and compare them
    live_embeddings = []
    for f in files[:4]:
        path = os.path.join(img_dir, f)
        img = cv2.imread(path)
        if img is None:
            print(f"FAILED to load: {path}")
            continue
        faces = face_analyzer.detect_faces(img, min_confidence=0.3)
        if not faces:
            print(f"NO FACE DETECTED in: {f}  (size: {img.shape})")
            continue
        emb = face_analyzer.get_embedding(faces[0])
        norm = np.linalg.norm(emb)
        live_embeddings.append((f, emb))
        print(f"OK  {f}: embedding norm={norm:.4f}, first_3={emb[:3]}")

    # 3. Test: compare live embeddings to each other
    print("\n--- Live-to-Live Similarity ---")
    for i in range(len(live_embeddings)):
        for j in range(i + 1, len(live_embeddings)):
            a_name, a_emb = live_embeddings[i]
            b_name, b_emb = live_embeddings[j]
            sim = float(np.dot(a_emb / np.linalg.norm(a_emb), b_emb / np.linalg.norm(b_emb)))
            print(f"  {a_name} vs {b_name}: {sim:.4f}")

    # 4. Test: load DB embeddings and compare to live
    print("\n--- DB-to-Live Similarity ---")
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT student_id, embedding FROM embeddings"))
        db_rows = res.all()
        print(f"DB has {len(db_rows)} embeddings.")

        for db_row in db_rows[:3]:
            sid = db_row[0]
            raw = db_row[1]
            if isinstance(raw, str):
                db_emb = np.array(json.loads(raw), dtype=np.float32)
            else:
                db_emb = np.array(raw, dtype=np.float32)
            
            db_norm = np.linalg.norm(db_emb)
            print(f"\n  DB Student {sid}: norm={db_norm:.4f}")
            
            for fname, live_emb in live_embeddings:
                live_norm_emb = live_emb / np.linalg.norm(live_emb)
                db_norm_emb = db_emb / np.linalg.norm(db_emb) if db_norm > 0 else db_emb
                sim = float(np.dot(live_norm_emb, db_norm_emb))
                print(f"    vs {fname}: {sim:.4f}")


if __name__ == "__main__":
    asyncio.run(run_sanity_test())

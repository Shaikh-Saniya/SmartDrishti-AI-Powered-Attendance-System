import asyncio
import cv2
import numpy as np
from app.db.session import async_session_factory
from app.ml.insightface_loader import face_analyzer
from app.ml.face_matcher import find_best_match
from app.core.config import settings

async def test_recognition():
    # Load model
    face_analyzer.load_model(settings.INSIGHTFACE_MODEL_NAME, settings.INSIGHTFACE_ROOT)
    
    # Check if we have any students
    async with async_session_factory() as db:
        from sqlalchemy import text
        res = await db.execute(text("SELECT id, name FROM students WHERE is_active = true LIMIT 5"))
        students = res.all()
        print(f"Active students: {students}")
        
        res = await db.execute(text("SELECT count(*) FROM embeddings"))
        print(f"Embeddings count: {res.scalar()}")

    # Find an unknown face to test against (or just load an image if we had one)
    # Since I don't have an image, I'll try to compare an existing embedding against itself
    async with async_session_factory() as db:
        from sqlalchemy import text
        res = await db.execute(text("SELECT embedding FROM embeddings LIMIT 1"))
        row = res.first()
        if row:
            raw_emb = row[0]
            if hasattr(raw_emb, "tolist"):
                raw_emb = raw_emb.tolist()
            emb = np.array(raw_emb, dtype=np.float32)
            print(f"Testing self-similarity for embedding of length {len(emb)}")
            
            sid, sim = await find_best_match(db, emb, threshold=0.0)
            print(f"Self-match result: sid={sid}, similarity={sim}")
        else:
            print("No embeddings found to test.")

if __name__ == "__main__":
    asyncio.run(test_recognition())

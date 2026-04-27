import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory
from app.ml.face_matcher import cosine_similarity
import numpy as np

async def check_student_consistency():
    async with async_session_factory() as db:
        # Find students with multiple embeddings
        res = await db.execute(text("""
            SELECT student_id, count(*) 
            FROM embeddings 
            GROUP BY student_id 
            HAVING count(*) > 1 
            LIMIT 5
        """))
        students = res.all()
        
        if not students:
            print("No students with multiple embeddings found.")
            return

        for student_id, count in students:
            print(f"\nStudent ID: {student_id} (Embeddings: {count})")
            res = await db.execute(text("SELECT embedding FROM embeddings WHERE student_id = :sid"), {"sid": student_id})
            embs = [np.array(row[0], dtype=np.float32) for row in res.all()]
            
            # Compare first two
            sim = cosine_similarity(embs[0], embs[1])
            print(f"Similarity between first two photos: {sim:.4f}")

if __name__ == "__main__":
    asyncio.run(check_student_consistency())

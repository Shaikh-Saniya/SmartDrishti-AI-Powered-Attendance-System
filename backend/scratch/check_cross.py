import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory
from app.ml.face_matcher import cosine_similarity
import numpy as np

async def check_cross_similarity():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT student_id, embedding FROM embeddings LIMIT 10"))
        rows = res.all()
        if len(rows) < 2:
            print("Not enough embeddings to compare.")
            return

        def parse_emb(e):
            if isinstance(e, str):
                import json
                return np.array(json.loads(e), dtype=np.float32)
            return np.array(e, dtype=np.float32)

        embs = [(row[0], parse_emb(row[1])) for row in rows]
        
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                sim = cosine_similarity(embs[i][1], embs[j][1])
                print(f"Student {embs[i][0]} vs Student {embs[j][0]}: Similarity = {sim:.4f}")

if __name__ == "__main__":
    asyncio.run(check_cross_similarity())

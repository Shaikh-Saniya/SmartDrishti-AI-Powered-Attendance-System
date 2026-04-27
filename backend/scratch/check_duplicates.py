import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory
import numpy as np

async def check_duplicate_embeddings():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT id, student_id, embedding FROM embeddings LIMIT 20"))
        rows = res.all()
        for row in rows:
            emb = np.array(row[2], dtype=np.float32) if not isinstance(row[2], str) else np.array(eval(row[2]), dtype=np.float32)
            # Just print the first 10 values of each embedding
            print(f"ID: {row[0]}, Student: {row[1]}, First 5: {emb[:5]}")

if __name__ == "__main__":
    asyncio.run(check_duplicate_embeddings())

import asyncio
import numpy as np
from sqlalchemy import text
from app.db.session import async_session_factory

async def check_norms():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT id, embedding FROM embeddings LIMIT 10"))
        rows = res.all()
        for row in rows:
            emb_id = row[0]
            # Handle potential string or list/array
            raw_emb = row[1]
            if isinstance(raw_emb, str):
                import json
                raw_emb = json.loads(raw_emb)
            emb = np.array(raw_emb, dtype=np.float32)
            norm = np.linalg.norm(emb)
            print(f"Embedding ID: {emb_id}, Magnitude (Norm): {norm:.4f}")

if __name__ == "__main__":
    asyncio.run(check_norms())

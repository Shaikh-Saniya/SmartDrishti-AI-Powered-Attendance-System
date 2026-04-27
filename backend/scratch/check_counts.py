import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def check():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT count(*) FROM students"))
        print(f"Students count: {res.scalar()}")
        res = await db.execute(text("SELECT count(*) FROM embeddings"))
        print(f"Embeddings count: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(check())

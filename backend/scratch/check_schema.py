import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name = 'embeddings'"))
        for row in res:
            print(f"Column: {row[0]}, Data Type: {row[1]}, UDT Name: {row[2]}")

if __name__ == "__main__":
    asyncio.run(check())

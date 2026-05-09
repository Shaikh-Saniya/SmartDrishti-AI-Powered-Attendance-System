import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)

async def main():
    async with engine.begin() as conn:
        print("Altering table to add year column")
        await conn.execute(text('ALTER TABLE students ADD COLUMN IF NOT EXISTS year VARCHAR(50);'))
        print("Success")

if __name__ == "__main__":
    asyncio.run(main())

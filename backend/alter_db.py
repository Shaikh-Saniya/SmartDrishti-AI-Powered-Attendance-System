import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)

async def main():
    async with engine.begin() as conn:
        print("Altering table")
        await conn.execute(text('ALTER TABLE attendance ALTER COLUMN student_id DROP NOT NULL;'))
        await conn.execute(text('ALTER TABLE attendance ADD COLUMN IF NOT EXISTS name VARCHAR(100);'))
        await conn.execute(text('ALTER TABLE attendance ADD COLUMN IF NOT EXISTS roll_number VARCHAR(50);'))
        await conn.execute(text('ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_name VARCHAR(50);'))
        print("Success")

if __name__ == "__main__":
    asyncio.run(main())

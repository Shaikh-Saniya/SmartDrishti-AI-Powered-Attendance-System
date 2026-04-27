import asyncio
from app.db.session import async_session_factory
from sqlalchemy import text

async def check():
    try:
        async with async_session_factory() as db:
            e_count = (await db.execute(text('SELECT count(*) FROM embeddings'))).scalar()
            s_count = (await db.execute(text('SELECT count(*) FROM students'))).scalar()
            print(f'Embeddings count: {e_count}')
            print(f'Students count: {s_count}')
            
            # Check a few similarities if possible
            if e_count > 0:
                res = await db.execute(text('SELECT student_id FROM embeddings LIMIT 5'))
                ids = res.scalars().all()
                print(f'Sample student IDs with embeddings: {ids}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check())

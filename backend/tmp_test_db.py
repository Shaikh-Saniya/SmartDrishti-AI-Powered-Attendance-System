
import asyncio
import sys
import os

# Add the current directory to sys.path so we can import 'app'
sys.path.append(os.getcwd())

from app.db.session import engine
from sqlalchemy import text

async def test():
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
            print('DATABASE_CONNECTION_SUCCESS')
    except Exception as e:
        print(f'DATABASE_CONNECTION_FAILED: {e}')

if __name__ == "__main__":
    asyncio.run(test())

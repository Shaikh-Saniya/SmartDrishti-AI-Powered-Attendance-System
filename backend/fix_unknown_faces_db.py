import asyncio
import sys
import os

sys.path.append(os.getcwd())

from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
# Import all models so they are registered with Base
from app.models.student import Student, StudentImage, Embedding
from app.models.attendance import Attendance
from app.models.task_status import ProcessingTask
from app.models.unknown_face import UnknownFace
from app.models.user import User

async def main():
    async with engine.begin() as conn:
        print("Dropping unknown_faces table...")
        await conn.execute(text("DROP TABLE IF EXISTS unknown_faces CASCADE;"))
        print("Recreating unknown_faces table...")
        await conn.run_sync(Base.metadata.create_all)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())

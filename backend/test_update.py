import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.db.session import async_session_factory
from app.models.attendance import Attendance
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        # Get one attendance record
        result = await db.execute(select(Attendance).limit(1))
        record = result.scalar_one_or_none()
        if not record:
            print("No record found.")
            return

        print(f"Original status: {record.status}")
        
        # Change status
        new_status = "absent" if record.status == "present" else "present"
        record.status = new_status
        record.source = "manual"
        
        await db.commit()
        print(f"Updated status to: {new_status}")
        
        # Re-fetch
        result2 = await db.execute(select(Attendance).where(Attendance.id == record.id))
        record2 = result2.scalar_one()
        print(f"Re-fetched status: {record2.status}")

if __name__ == "__main__":
    asyncio.run(main())

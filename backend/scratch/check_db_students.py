import asyncio
import uuid
from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.models.student import Student

async def check_students():
    async with async_session_factory() as db:
        result = await db.execute(select(func.count()).select_from(Student))
        total_count = result.scalar()
        
        active_result = await db.execute(select(func.count()).select_from(Student).where(Student.is_active == True))
        active_count = active_result.scalar()
        
        print(f"Total students in DB: {total_count}")
        print(f"Active students in DB: {active_count}")
        
        if total_count > 0:
            all_students = await db.execute(select(Student).limit(10))
            for s in all_students.scalars().all():
                print(f"ID: {s.id}, Name: {s.name}, Active: {s.is_active}")

if __name__ == "__main__":
    asyncio.run(check_students())

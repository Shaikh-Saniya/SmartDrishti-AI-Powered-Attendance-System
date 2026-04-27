import asyncio
from app.db.session import async_session_factory
from sqlalchemy import select
from app.models.task_status import ProcessingTask

async def dump_tasks():
    async with async_session_factory() as db:
        res = await db.execute(select(ProcessingTask))
        tasks = res.scalars().all()
        with open('dump_out.txt', 'w') as f:
            for t in tasks:
                f.write(f"Task {t.id}: type={t.task_type}, status={t.status}\n")

if __name__ == '__main__':
    asyncio.run(dump_tasks())

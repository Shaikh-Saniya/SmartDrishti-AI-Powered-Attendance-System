import asyncio
import uuid
import logging
from app.services.face_service import process_group_image

logging.basicConfig(level=logging.INFO)

async def test_run():
    print("Testing ML directly...")
    task_id = uuid.uuid4()
    # Read our test face
    try:
        import requests
        image_data = requests.get('https://images.unsplash.com/photo-1542909168-82c3e7fdca5c?w=400').content
        b = image_data
    except Exception as e:
        print("No image:", e)
        return

    # Let's insert a dummy task so it can update it
    from app.db.session import async_session_factory
    from app.models.task_status import ProcessingTask
    async with async_session_factory() as db:
        task = ProcessingTask(id=task_id, task_type='group_attendance', status='pending')
        db.add(task)
        await db.commit()
    
    print("Task inserted in DB. Running process_group_image...")
    try:
        await process_group_image(
            task_id=task_id,
            image_bytes=b,
            subject='ML Testing'
        )
    except Exception as e:
        print("Error during process_group_image:", e)
        import traceback
        traceback.print_exc()
        
    print("Done. Checking DB status...")
    async with async_session_factory() as db:
        res = await db.get(ProcessingTask, task_id)
        if res:
            print("Final DB Status:", res.status)
            print("Final DB Result:", res.result)
            print("Final DB Error:", res.error_message)
        else:
            print("Task not found in DB!")

if __name__ == '__main__':
    asyncio.run(test_run())

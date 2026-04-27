import asyncio
import os
import shutil
from sqlalchemy import text
from app.db.session import async_session_factory
from app.core.config import settings

async def reset_database():
    print("Starting database reset...")
    
    async with async_session_factory() as db:
        try:
            # 1. Truncate tables with CASCADE to handle foreign keys
            print("Truncating tables: students, embeddings, attendance, unknown_faces...")
            await db.execute(text("TRUNCATE TABLE attendance, embeddings, unknown_faces, students CASCADE;"))
            await db.commit()
            print("OK Database tables truncated.")
            
            # 2. Clear upload directories
            upload_dirs = ["student_images", "unknown_faces", "attendance_images"]
            for sub in upload_dirs:
                dir_path = os.path.join(settings.UPLOAD_DIR, sub)
                if os.path.exists(dir_path):
                    print(f"Clearing directory: {dir_path}")
                    # Re-create the directory to keep it empty
                    shutil.rmtree(dir_path)
                    os.makedirs(dir_path, exist_ok=True)
            print("OK Uploaded files cleared.")
            
            print("\nReset complete! You can now start with fresh registrations.")
            
        except Exception as e:
            print(f"Error during reset: {e}")
            await db.rollback()

if __name__ == "__main__":
    # Confirm with a simulated prompt check if this was a one-off run
    asyncio.run(reset_database())

"""One-shot script: apply schema changes needed for unknown-face support.

Run from c:\Drishti\backend with the venv active:
    python apply_migration.py

What it does:
1. Makes attendance.student_id nullable
2. Adds attendance.name         VARCHAR(100)
3. Adds attendance.roll_number  VARCHAR(50)
4. Adds attendance.class_name   VARCHAR(50)
5. Drops the old UniqueConstraint on (student_id, date, subject) — it would
   prevent multiple unknown rows per date/subject.
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


# ── read DATABASE_URL from .env manually (no pydantic dependency) ──────────
def load_db_url() -> str:
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return "postgresql+asyncpg://postgres:password@localhost:5432/attendance_db"


async def main() -> None:
    db_url = load_db_url()
    print(f"Connecting to: {db_url}")
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        # 1. Make student_id nullable
        try:
            await conn.execute(
                text("ALTER TABLE attendance ALTER COLUMN student_id DROP NOT NULL;")
            )
            print("✅  student_id is now nullable")
        except Exception as e:
            print(f"⚠️  student_id already nullable or error: {e}")

        # 2. Add name column
        try:
            await conn.execute(
                text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS name VARCHAR(100);")
            )
            print("✅  name column added/exists")
        except Exception as e:
            print(f"⚠️  name: {e}")

        # 3. Add roll_number column
        try:
            await conn.execute(
                text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS roll_number VARCHAR(50);")
            )
            print("✅  roll_number column added/exists")
        except Exception as e:
            print(f"⚠️  roll_number: {e}")

        # 4. Add class_name column
        try:
            await conn.execute(
                text("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_name VARCHAR(50);")
            )
            print("✅  class_name column added/exists")
        except Exception as e:
            print(f"⚠️  class_name: {e}")

        # 5. Drop the old unique constraint that blocks multiple unknown rows
        try:
            await conn.execute(
                text(
                    "ALTER TABLE attendance "
                    "DROP CONSTRAINT IF EXISTS uq_attendance_student_date_subject;"
                )
            )
            print("✅  Dropped old unique constraint uq_attendance_student_date_subject")
        except Exception as e:
            print(f"⚠️  Dropping constraint: {e}")

    await engine.dispose()
    print("\nDone ✅")


if __name__ == "__main__":
    asyncio.run(main())

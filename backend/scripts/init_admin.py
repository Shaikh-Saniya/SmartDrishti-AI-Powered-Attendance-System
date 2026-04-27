"""Create default admin user script.

Usage:
    cd backend
    python scripts/init_admin.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.models.user import User


async def create_admin() -> None:
    """Create the default admin user if it doesn't exist."""
    admin_email = "saniya.shaikh@gmail.com"
    admin_password = "123456789"
    admin_name = "System Administrator"

    async with async_session_factory() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == admin_email)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user '{admin_email}' already exists. Skipping.")
            return

        # Create admin user
        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            full_name=admin_name,
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()

        print(f"✅ Admin user created successfully!")
        print(f"   Email:    {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Role:     admin")
        print()
        print("⚠️  Change the password after first login!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())

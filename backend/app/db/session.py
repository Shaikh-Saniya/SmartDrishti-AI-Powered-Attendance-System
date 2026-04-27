"""Async SQLAlchemy session management with connection pooling."""

import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=15,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(engine.sync_engine, "connect")
def register_vector_codec(dbapi_connection, connection_record):
    """Register pgvector codec with asyncpg on every new connection."""
    try:
        from pgvector.asyncpg import register_vector
        dbapi_connection.run_sync(register_vector)
        logger.debug("pgvector asyncpg codec registered on new connection.")
    except Exception as e:
        logger.warning("pgvector asyncpg codec registration failed (non-fatal): %s", e)


async def get_async_session() -> AsyncSession:
    """Create a new async session (used outside of dependency injection)."""
    return async_session_factory()

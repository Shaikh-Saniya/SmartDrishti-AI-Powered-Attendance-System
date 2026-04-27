"""Background cleanup service for old processing tasks."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.session import async_session_factory
from app.models.task_status import ProcessingTask

logger = logging.getLogger(__name__)

# Global reference to the cleanup task so it can be cancelled on shutdown
_cleanup_task: asyncio.Task | None = None


async def cleanup_old_tasks(max_age_days: int = 7) -> int:
    """Delete processing tasks older than max_age_days.

    Returns:
        Number of tasks deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    async with async_session_factory() as db:
        result = await db.execute(
            delete(ProcessingTask).where(ProcessingTask.created_at < cutoff)
        )
        await db.commit()
        count = result.rowcount  # type: ignore[union-attr]
        if count:
            logger.info("Cleaned up %d old processing tasks", count)
        return count


async def _run_periodic_cleanup(interval_seconds: int = 86400) -> None:
    """Run cleanup task periodically (default: daily)."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await cleanup_old_tasks()
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            break
        except Exception as e:
            logger.error("Cleanup task error: %s", str(e))


def start_cleanup_scheduler() -> None:
    """Start the background cleanup scheduler."""
    global _cleanup_task
    _cleanup_task = asyncio.create_task(_run_periodic_cleanup())
    logger.info("Background cleanup scheduler started (daily)")


def stop_cleanup_scheduler() -> None:
    """Stop the background cleanup scheduler."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Background cleanup scheduler stopped")

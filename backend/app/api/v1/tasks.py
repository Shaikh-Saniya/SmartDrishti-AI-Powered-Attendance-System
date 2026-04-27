"""Task status polling API route."""

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.dependencies.auth import get_current_active_user
from app.dependencies.db import get_db
from app.models.task_status import ProcessingTask
from app.models.user import User
from app.schemas.common import TaskStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> TaskStatusResponse:
    """Get the status and results of a background processing task."""
    result = await db.execute(
        select(ProcessingTask).where(ProcessingTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundException(detail="Task not found")

    return TaskStatusResponse.model_validate(task)

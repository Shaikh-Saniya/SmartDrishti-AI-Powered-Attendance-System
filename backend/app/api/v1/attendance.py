"""Attendance API routes: CRUD, group processing, and export."""

import logging
import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_default, rate_limit_upload
from app.dependencies.auth import get_current_active_user
from app.dependencies.db import get_db
from app.models.task_status import ProcessingTask
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from app.schemas.common import MessageResponse, PaginatedResponse, TaskStatusResponse
from app.services import attendance_service, export_service
from app.services.face_service import process_group_image
from app.utils.file_upload import validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/process-group", response_model=TaskStatusResponse, status_code=202)
async def process_group(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Group image for attendance"),
    subject: str = Form(..., description="Subject name"),
    date_str: str | None = Form(default=None, alias="date", description="Date (YYYY-MM-DD)"),
    class_name: str | None = Form(default=None, description="Class name (e.g. CSE-A)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _rate: None = Depends(rate_limit_upload),
) -> TaskStatusResponse:
    """Upload a group image for face recognition and auto-attendance.

    Returns task_id immediately; poll /tasks/{task_id}/status for results.
    """
    image_bytes = await validate_upload_file(image)

    att_date: date | None = None
    if date_str:
        att_date = date.fromisoformat(date_str)

    task = ProcessingTask(
        task_type="group_attendance",
        status="pending",
    )
    db.add(task)
    await db.flush()
    task_id = task.id

    import asyncio
    asyncio.create_task(
        process_group_image(
            task_id=task_id,
            image_bytes=image_bytes,
            subject=subject,
            att_date=att_date,
            marked_by=current_user.id,
            class_name=class_name,
        )
    )

    logger.info("Group processing task %s created by %s", task_id, current_user.email)
    return TaskStatusResponse.model_validate(task)


@router.get("/classes", response_model=list[str])
async def get_classes(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """Return distinct class_name values present in the attendance table."""
    return await attendance_service.get_distinct_classes(db)


@router.get("/trend", response_model=list[dict])
async def get_attendance_trend(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """Return attendance trends grouped by class and subject."""
    return await attendance_service.get_subject_trend(db)


@router.get("/summary", response_model=dict)
async def get_attendance_summary(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> dict:
    """Return summary statistics for attendance."""
    return await attendance_service.get_attendance_summary(db)


@router.get("", response_model=PaginatedResponse[AttendanceResponse])
async def list_attendance(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    date_filter: date | None = Query(default=None, alias="date"),
    subject: str | None = Query(default=None),
    student_id: uuid.UUID | None = Query(default=None),
    class_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[AttendanceResponse]:
    """Get attendance records with optional filters (date, subject, class_name, student_id)."""
    items_data, total = await attendance_service.list_attendance(
        db,
        page=page,
        limit=limit,
        date_filter=date_filter,
        subject_filter=subject,
        student_id_filter=student_id,
        class_name_filter=class_name,
    )
    items = [AttendanceResponse.model_validate(item) for item in items_data]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("/manual", response_model=AttendanceResponse, status_code=201)
async def manual_attendance(
    data: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _rate: None = Depends(rate_limit_default),
) -> AttendanceResponse:
    """Manually mark a single attendance record."""
    record = await attendance_service.create_attendance(
        db, data, marked_by=current_user.id, source="manual"
    )
    return AttendanceResponse.model_validate(record)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    attendance_id: uuid.UUID,
    data: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> AttendanceResponse:
    """Update attendance record status."""
    record = await attendance_service.update_attendance(db, attendance_id, data)
    return AttendanceResponse.model_validate(record)


@router.delete("/{attendance_id}", response_model=MessageResponse)
async def delete_attendance(
    attendance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Delete an attendance record."""
    await attendance_service.delete_attendance(db, attendance_id)
    return MessageResponse(message="Attendance record deleted")


@router.get("/export")
async def export_attendance(
    start_date: date | None = None,
    end_date: date | None = None,
    subject: str | None = None,
    class_name: str | None = None,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> Response:
    """Export attendance records as CSV or Excel.

    Respects all active filters: start_date, end_date, subject, class_name.
    """
    content, content_type, filename = await export_service.export_attendance(
        db,
        start_date=start_date,
        end_date=end_date,
        subject=subject,
        class_name=class_name,
        export_format=format,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

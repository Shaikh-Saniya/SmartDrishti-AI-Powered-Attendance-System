"""Student management API routes."""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_default, rate_limit_upload
from app.dependencies.auth import get_current_active_user
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.student import StudentCreate, StudentListResponse, StudentResponse, StudentUpdate
from app.services import student_service
from app.utils.file_upload import validate_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(
    roll_number: str = Form(...),
    name: str = Form(...),
    class_name: str = Form(...),
    department: str | None = Form(None),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
    _rate: None = Depends(rate_limit_default),
) -> StudentResponse:
    """Create a new student record (supports FormData and optional immediate image upload)."""
    logger.info("CREATING STUDENT - Received: roll=%s, name=%s, class_name=%s", roll_number, name, class_name)
    data = StudentCreate(
        roll_number=roll_number,
        name=name,
        class_name=class_name,
        department=department,
        email=email,
        phone=phone
    )
    student = await student_service.create_student(db, data)
    
    # If an image was uploaded in the same request, process it
    if image:
        contents = await validate_upload_file(image)
        await student_service.add_student_images(db, student.id, [contents])
        # Refresh to include the image in the response
        student = await student_service.get_student(db, student.id)
        
    return StudentResponse.model_validate(student)


@router.get("", response_model=PaginatedResponse[StudentListResponse])
async def list_students(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    class_filter: str | None = Query(default=None, alias="class"),
    department: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[StudentListResponse]:
    """List all students with pagination and filters."""
    students, total = await student_service.list_students(
        db, page=page, limit=limit,
        class_filter=class_filter,
        department_filter=department,
        search=search,
    )
    items = [StudentListResponse.model_validate(s) for s in students]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> StudentResponse:
    """Get a student by ID."""
    student = await student_service.get_student(db, student_id)
    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: uuid.UUID,
    data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> StudentResponse:
    """Update student information."""
    student = await student_service.update_student(db, student_id, data)
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}", response_model=MessageResponse)
async def delete_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Soft-delete a student."""
    await student_service.soft_delete_student(db, student_id)
    return MessageResponse(message="Student deactivated successfully")


@router.post("/{student_id}/images", response_model=MessageResponse, status_code=201)
async def add_student_images(
    student_id: uuid.UUID,
    images: list[UploadFile] = File(..., description="Student face images (max 5)"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
    _rate: None = Depends(rate_limit_upload),
) -> MessageResponse:
    """Upload face images for a student (max 5 total)."""
    # Validate all uploaded files
    contents_list: list[bytes] = []
    for image in images:
        contents = await validate_upload_file(image)
        contents_list.append(contents)

    created = await student_service.add_student_images(db, student_id, contents_list)
    return MessageResponse(message=f"{len(created)} image(s) added successfully")


@router.delete("/{student_id}/images/{image_id}", response_model=MessageResponse)
async def delete_student_image(
    student_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Delete a specific student image."""
    await student_service.delete_student_image(db, student_id, image_id)
    return MessageResponse(message="Image deleted successfully")

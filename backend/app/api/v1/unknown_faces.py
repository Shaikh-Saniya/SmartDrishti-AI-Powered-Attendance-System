"""Unknown faces API routes."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.dependencies.auth import get_current_active_user
from app.dependencies.db import get_db
from app.models.unknown_face import UnknownFace
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.utils.file_upload import delete_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unknown-faces", tags=["Unknown Faces"])


class UnknownFaceResponse:
    """Inline response model for unknown faces."""
    pass


from pydantic import BaseModel
from datetime import datetime


class UnknownFaceOut(BaseModel):
    """Unknown face API response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    image_path: str
    detected_at: datetime
    assigned_to: uuid.UUID | None
    notes: str | None
    processed: bool


class AssignRequest(BaseModel):
    """Request body for assigning unknown face to student."""

    student_id: uuid.UUID


@router.get("", response_model=PaginatedResponse[UnknownFaceOut])
async def list_unknown_faces(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    processed: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[UnknownFaceOut]:
    """List unknown faces with pagination."""
    query = select(UnknownFace)
    if processed is not None:
        query = query.where(UnknownFace.processed == processed)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(UnknownFace.detected_at.desc())
    result = await db.execute(query)
    faces = list(result.scalars().all())

    items = [UnknownFaceOut.model_validate(f) for f in faces]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.get("/{face_id}/image")
async def get_unknown_face_image(
    face_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Get the image file of an unknown face."""
    result = await db.execute(select(UnknownFace).where(UnknownFace.id == face_id))
    face = result.scalar_one_or_none()
    if face is None:
        raise NotFoundException(detail="Unknown face not found")

    file_path = Path(face.image_path)
    if not file_path.exists():
        raise NotFoundException(detail="Image file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=file_path.name,
    )


@router.post("/{face_id}/assign", response_model=MessageResponse)
async def assign_unknown_face(
    face_id: uuid.UUID,
    data: AssignRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Assign an unknown face to a student.

    This also adds the embedding to the student's embedding set.
    """
    result = await db.execute(select(UnknownFace).where(UnknownFace.id == face_id))
    face = result.scalar_one_or_none()
    if face is None:
        raise NotFoundException(detail="Unknown face not found")

    # Update the unknown face record
    face.assigned_to = data.student_id
    face.processed = True

    # Add embedding to student's embeddings
    from app.models.student import Embedding

    emb = Embedding(
        student_id=data.student_id,
        embedding=face.embedding,
    )
    db.add(emb)

    await db.flush()
    logger.info("Assigned unknown face %s to student %s", face_id, data.student_id)
    return MessageResponse(message="Unknown face assigned to student successfully")


@router.delete("/{face_id}", response_model=MessageResponse)
async def delete_unknown_face(
    face_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Delete an unknown face record and its image."""
    result = await db.execute(select(UnknownFace).where(UnknownFace.id == face_id))
    face = result.scalar_one_or_none()
    if face is None:
        raise NotFoundException(detail="Unknown face not found")

    # Delete image file
    delete_file(face.image_path)

    await db.delete(face)
    await db.flush()
    logger.info("Deleted unknown face %s", face_id)
    return MessageResponse(message="Unknown face deleted")

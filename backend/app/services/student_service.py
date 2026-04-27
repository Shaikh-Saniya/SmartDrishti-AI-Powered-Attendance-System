"""Student service: CRUD operations and image/embedding management."""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.ml.insightface_loader import face_analyzer
from app.models.student import Embedding, Student, StudentImage
from app.schemas.student import StudentCreate, StudentUpdate
from app.utils.file_upload import delete_file, save_upload_file

logger = logging.getLogger(__name__)


async def create_student(
    db: AsyncSession,
    data: StudentCreate,
) -> Student:
    """Create a new student record.

    Args:
        db: Async database session.
        data: Student creation data.

    Returns:
        The created Student object.

    Raises:
        BadRequestException: If a student with the same roll_number already exists in the same class.
    """
    # Check for duplicate roll_number within the same class (composite uniqueness)
    existing = await db.execute(
        select(Student).where(
            Student.roll_number == data.roll_number,
            Student.class_ == data.class_name,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise BadRequestException(
            detail=f"Roll number '{data.roll_number}' already exists in class '{data.class_name}'."
        )

    student = Student(
        roll_number=data.roll_number,
        name=data.name,
        class_=data.class_name,  # Map class_name to class_ (class is a reserved keyword)
        department=data.department,
        email=data.email,
        phone=data.phone,
    )
    db.add(student)
    await db.flush()
    
    # Reload from DB to eagerly populate the 'images' relationship and avoid MissingGreenlet
    await db.refresh(student)
    student = await get_student(db, student.id)
    
    logger.info("Created student: %s (roll: %s, class: %s)", student.id, data.roll_number, data.class_name)
    return student


async def get_student(db: AsyncSession, student_id: uuid.UUID) -> Student:
    """Get a student by ID.

    Raises:
        NotFoundException: If student not found.
    """
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.images))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundException(detail=f"Student {student_id} not found")
    return student


async def list_students(
    db: AsyncSession,
    page: int = 1,
    limit: int = 50,
    class_filter: str | None = None,
    department_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[Student], int]:
    """List students with pagination and filters.

    Returns:
        Tuple of (students_list, total_count).
    """
    query = select(Student).where(Student.is_active == True)

    if class_filter:
        query = query.where(Student.class_ == class_filter)
    if department_filter:
        query = query.where(Student.department == department_filter)
    if search:
        query = query.where(
            Student.name.ilike(f"%{search}%") | Student.roll_number.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Student.name)
    result = await db.execute(query)
    students = list(result.scalars().all())

    return students, total


async def update_student(
    db: AsyncSession,
    student_id: uuid.UUID,
    data: StudentUpdate,
) -> Student:
    """Update student record fields."""
    student = await get_student(db, student_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    await db.flush()
    logger.info("Updated student: %s", student_id)
    return student


async def soft_delete_student(db: AsyncSession, student_id: uuid.UUID) -> Student:
    """Soft-delete a student (set is_active = False)."""
    student = await get_student(db, student_id)
    student.is_active = False
    await db.flush()
    logger.info("Soft-deleted student: %s", student_id)
    return student


async def add_student_images(
    db: AsyncSession,
    student_id: uuid.UUID,
    image_contents_list: list[bytes],
) -> list[StudentImage]:
    """Add images to a student and generate face embeddings.

    Args:
        db: Async database session.
        student_id: ID of the student.
        image_contents_list: List of raw image bytes.

    Returns:
        List of created StudentImage records.
    """
    student = await get_student(db, student_id)

    # Check max images (5 total)
    existing_count_result = await db.execute(
        select(func.count()).where(StudentImage.student_id == student_id)
    )
    existing_count = existing_count_result.scalar() or 0
    if existing_count + len(image_contents_list) > 5:
        raise BadRequestException(
            detail=f"Maximum 5 images per student. Currently: {existing_count}"
        )

    created_images: list[StudentImage] = []
    import cv2
    import numpy as np

    for i, contents in enumerate(image_contents_list):
        # Save file
        save_path = save_upload_file(
            contents=contents,
            subdirectory="student_images",
            prefix=str(student_id),
        )

        # Create image record
        is_primary = existing_count == 0 and i == 0
        image_record = StudentImage(
            student_id=student_id,
            image_path=str(save_path),
            is_primary=is_primary,
        )
        db.add(image_record)
        created_images.append(image_record)

        # Generate embedding from image
        try:
            img_array = np.frombuffer(contents, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to decode uploaded image. Please ensure it is a valid JPG/PNG."
                )

            faces = face_analyzer.detect_faces(img, min_confidence=0.3)

            if not faces:
                # Don't swallow this — tell the user immediately
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No face detected in image '{save_path.name}'. "
                        "Please upload a clear, well-lit photo showing the student's face."
                    )
                )

            # Use the first (largest/most confident) face
            # get_embedding returns face.normed_embedding which is already L2-normalized
            embedding = face_analyzer.get_embedding(faces[0])

            # Convert to plain Python float list for pgvector storage
            embedding_list = [float(x) for x in embedding.tolist()]

            emb_record = Embedding(
                student_id=student_id,
                embedding=embedding_list,
            )
            db.add(emb_record)
            logger.info(
                "Generated embedding (norm=%.4f) for student %s",
                float(np.linalg.norm(embedding)),
                student_id,
            )

        except HTTPException:
            # Re-raise HTTP errors directly — don't swallow them
            raise
        except Exception as e:
            logger.error("Unexpected error generating embedding for student %s: %s", student_id, str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Internal error while processing image: {str(e)}"
            )

    await db.flush()
    return created_images


async def delete_student_image(
    db: AsyncSession,
    student_id: uuid.UUID,
    image_id: uuid.UUID,
) -> None:
    """Delete a specific student image."""
    result = await db.execute(
        select(StudentImage).where(
            StudentImage.id == image_id,
            StudentImage.student_id == student_id,
        )
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise NotFoundException(detail="Image not found")

    # Delete file from disk
    delete_file(image.image_path)

    await db.delete(image)
    await db.flush()
    logger.info("Deleted image %s for student %s", image_id, student_id)

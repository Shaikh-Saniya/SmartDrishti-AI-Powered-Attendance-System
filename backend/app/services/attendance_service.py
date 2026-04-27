"""Attendance service: query, create, update, and delete attendance records."""

import logging
import uuid
from datetime import date, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.attendance import Attendance
from app.models.student import Student
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate

logger = logging.getLogger(__name__)


async def create_attendance(
    db: AsyncSession,
    data: AttendanceCreate,
    marked_by: uuid.UUID | str,
    source: str = "manual",
) -> Attendance:
    """Create a single attendance record.

    Raises:
        BadRequestException: If duplicate record exists (for known students only).
    """
    if data.student_id:
        existing = await db.execute(
            select(Attendance).where(
                Attendance.student_id == str(data.student_id),
                Attendance.date == data.date,
                Attendance.subject == data.subject,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException(
                detail="Attendance already recorded for this student, date, and subject"
            )

    record = Attendance(
        student_id=str(data.student_id) if data.student_id else None,
        subject=data.subject,
        date=data.date,
        time=data.time,
        status=data.status,
        marked_by=str(marked_by) if marked_by else None,
        source=source,
    )
    db.add(record)
    await db.flush()
    await db.commit()
    logger.info("Created attendance for student %s on %s", data.student_id, data.date)
    return record


async def mark_attendance_auto(
    db: AsyncSession,
    student_id: uuid.UUID | str,
    subject: str,
    att_date: date,
    att_time: time,
    marked_by: uuid.UUID | str | None = None,
) -> Attendance | None:
    """Auto-mark attendance from face recognition."""
    existing = await db.execute(
        select(Attendance).where(
            Attendance.student_id == str(student_id),
            Attendance.date == att_date,
            Attendance.subject == subject,
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Attendance already exists for %s on %s/%s", student_id, att_date, subject)
        return None

    record = Attendance(
        student_id=str(student_id),
        subject=subject,
        date=att_date,
        time=att_time,
        status="present",
        marked_by=str(marked_by) if marked_by else None,
        source="auto",
    )
    db.add(record)
    await db.flush()
    await db.commit()
    return record


async def get_distinct_classes(db: AsyncSession) -> list[str]:
    """Return distinct non-null class_ values from the Student table."""
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(Student.class_))
        .where(Student.class_.isnot(None))
        .order_by(Student.class_)
    )
    rows = result.scalars().all()
    return list(rows)


async def list_attendance(
    db: AsyncSession,
    page: int = 1,
    limit: int = 50,
    date_filter: date | None = None,
    subject_filter: str | None = None,
    student_id_filter: uuid.UUID | str | None = None,
    class_name_filter: str | None = None,
) -> tuple[list[dict], int]:
    """List attendance records with optional filters."""
    # OUTER JOIN: keeps rows where student_id IS NULL (unknown faces)
    query = (
        select(Attendance, Student.name, Student.roll_number, Student.class_)
        .outerjoin(Student, Attendance.student_id == Student.id)
    )

    conditions = []
    if date_filter:
        conditions.append(Attendance.date == date_filter)
    if subject_filter:
        conditions.append(Attendance.subject == subject_filter)
    if student_id_filter:
        conditions.append(Attendance.student_id == str(student_id_filter))
    if class_name_filter:
        conditions.append(Attendance.class_name == class_name_filter)

    for cond in conditions:
        query = query.where(cond)

    # Count total (same filters)
    count_q = (
        select(func.count(Attendance.id))
        .outerjoin(Student, Attendance.student_id == Student.id)
    )
    for cond in conditions:
        count_q = count_q.where(cond)
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(
        Attendance.class_name.asc().nullslast(),
        Attendance.date.desc(),
        Attendance.time.desc(),
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        attendance = row[0]
        student_name = row[1] if len(row) > 1 else None
        student_roll = row[2] if len(row) > 2 else None
        student_class = row[3] if len(row) > 3 else None

        item = {
            "id": attendance.id,
            "student_id": attendance.student_id,
            "name": attendance.name or student_name or "Unknown",
            "roll_number": attendance.roll_number or student_roll or "UNKNOWN",
            "class_name": attendance.class_name or student_class or "Unknown",
            "subject": attendance.subject,
            "date": attendance.date,
            "time": attendance.time,
            "status": attendance.status,
            "marked_by": attendance.marked_by,
            "source": attendance.source,
            "created_at": attendance.created_at,
            "updated_at": attendance.updated_at,
        }
        items.append(item)

    return items, total


async def update_attendance(
    db: AsyncSession,
    attendance_id: uuid.UUID | str,
    data: AttendanceUpdate,
) -> Attendance:
    """Update any editable fields on an attendance record."""
    result = await db.execute(select(Attendance).where(Attendance.id == str(attendance_id)))
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(detail="Attendance record not found")

    update_data = data.model_dump(exclude_unset=True)
    
    if "status" in update_data:
        record.status = update_data["status"]
    if "name" in update_data:
        record.name = update_data["name"]
    if "roll_number" in update_data:
        record.roll_number = update_data["roll_number"]
    if "class_name" in update_data:
        record.class_name = update_data["class_name"]
    if "subject" in update_data:
        record.subject = update_data["subject"]

    record.source = "manual"

    await db.flush()
    await db.commit()
    logger.info("Updated attendance %s", attendance_id)
    return record


async def delete_attendance(db: AsyncSession, attendance_id: uuid.UUID | str) -> None:
    """Delete an attendance record."""
    result = await db.execute(select(Attendance).where(Attendance.id == str(attendance_id)))
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(detail="Attendance record not found")

    await db.delete(record)
    await db.flush()
    await db.commit()
    logger.info("Deleted attendance %s", attendance_id)


async def get_subject_trend(db: AsyncSession) -> list[dict]:
    """Get the number of attendance records per subject, grouped by class."""
    from app.models.student import Student
    from sqlalchemy import distinct
    
    # Get all subjects that exist in the system
    subjects_result = await db.execute(select(distinct(Attendance.subject)).where(Attendance.subject.isnot(None)))
    all_subjects = subjects_result.scalars().all()
    if not all_subjects:
        # Fallback to standard subjects if no attendance yet
        all_subjects = ["Mathematics", "Physics", "Chemistry", "Computer Science", "DBMS", "Operating Systems"]
        
    # Get all known classes
    classes_result = await db.execute(select(distinct(Student.class_)).where(Student.class_.isnot(None)))
    all_classes = classes_result.scalars().all()
    
    query = (
        select(Attendance.class_name, Attendance.subject, func.count(Attendance.id))
        .where(Attendance.status == "present")
        .where(Attendance.class_name.isnot(None))
        .where(Attendance.class_name != "Unknown")
        .group_by(Attendance.class_name, Attendance.subject)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Organize data by class
    class_trends = {cls: {subj: 0 for subj in all_subjects} for cls in all_classes}
    
    for row in rows:
        cls_name, subject, count = row[0], row[1], row[2]
        if cls_name in class_trends and subject in class_trends[cls_name]:
            class_trends[cls_name][subject] = count
            
    # Format response
    response = []
    for cls_name, subj_counts in class_trends.items():
        trend = []
        for subj in all_subjects:
            trend.append({
                "subject": subj,
                "count": subj_counts.get(subj, 0)
            })
        response.append({
            "class_name": cls_name,
            "trend": trend
        })
        
    # If there are absolutely no classes registered yet, return a dummy placeholder so the chart doesn't break
    if not response:
        trend = [{"subject": s, "count": 0} for s in all_subjects]
        response.append({"class_name": "No Classes Yet", "trend": trend})
        
    return response


async def get_attendance_summary(db: AsyncSession) -> dict:
    """Calculate summary statistics: average attendance, best class, worst class."""
    from app.models.student import Student
    from sqlalchemy import distinct
    
    # 1. Get class sizes
    class_sizes_result = await db.execute(
        select(Student.class_, func.count(Student.id))
        .where(Student.class_.isnot(None))
        .group_by(Student.class_)
    )
    class_sizes = {row[0]: row[1] for row in class_sizes_result.all()}
    
    if not class_sizes:
        return {
            "avg_attendance_percentage": 0,
            "best_class": "N/A",
            "worst_class": "N/A",
            "best_class_percentage": 0,
            "worst_class_percentage": 0
        }

    # 2. Get total present records per class
    present_result = await db.execute(
        select(Attendance.class_name, func.count(Attendance.id))
        .where(Attendance.status == "present")
        .where(Attendance.class_name.isnot(None))
        .group_by(Attendance.class_name)
    )
    present_counts = {row[0]: row[1] for row in present_result.all()}
    
    # 3. Get total sessions (unique subjects marked per class as a proxy)
    sessions_result = await db.execute(
        select(Attendance.class_name, func.count(distinct(Attendance.subject)))
        .where(Attendance.class_name.isnot(None))
        .group_by(Attendance.class_name)
    )
    sessions_counts = {row[0]: row[1] for row in sessions_result.all()}
    
    class_percentages = {}
    for cls, size in class_sizes.items():
        if size == 0:
            continue
        sessions = sessions_counts.get(cls, 1) # avoid div by zero
        if sessions == 0:
            sessions = 1
        present = present_counts.get(cls, 0)
        
        max_possible = size * sessions
        if max_possible > 0:
            percentage = (present / max_possible) * 100
            class_percentages[cls] = min(percentage, 100.0) # Cap at 100
        else:
            class_percentages[cls] = 0.0

    if not class_percentages:
         return {
            "avg_attendance_percentage": 0,
            "best_class": "N/A",
            "worst_class": "N/A",
            "best_class_percentage": 0,
            "worst_class_percentage": 0
        }
        
    avg_percentage = sum(class_percentages.values()) / len(class_percentages)
    best_class = max(class_percentages, key=class_percentages.get)
    worst_class = min(class_percentages, key=class_percentages.get)
    
    return {
        "avg_attendance_percentage": round(avg_percentage, 1),
        "best_class": best_class,
        "best_class_percentage": round(class_percentages[best_class], 1),
        "worst_class": worst_class,
        "worst_class_percentage": round(class_percentages[worst_class], 1)
    }

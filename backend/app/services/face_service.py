"""Face processing service: background task for group image processing."""

import logging
import uuid
from datetime import date, datetime, time, timezone

import cv2
import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import FaceDetectionException
from app.db.session import async_session_factory
from app.ml.face_matcher import find_best_match, l2_normalize
from app.ml.insightface_loader import face_analyzer
from app.models.attendance import Attendance
from app.models.student import Student
from app.models.task_status import ProcessingTask
from app.models.unknown_face import UnknownFace
from app.utils.file_upload import save_upload_file

logger = logging.getLogger(__name__)


async def process_group_image(
    task_id: uuid.UUID,
    image_bytes: bytes,
    subject: str,
    att_date: date | None = None,
    marked_by: uuid.UUID | None = None,
    class_name: str | None = None,
) -> None:
    """Background task: detect faces in group image and mark attendance.

    For RECOGNIZED faces: copies name/roll_number/class_name from Student table
    into the Attendance row so the data is always self-contained.

    For UNKNOWN faces: creates an Attendance row with name='Unknown',
    roll_number='UNKNOWN', class_name='Unknown' and student_id=NULL.
    Also saves the UnknownFace crop for later identification.

    Args:
        task_id: Processing task ID for status tracking.
        image_bytes: Raw image bytes.
        subject: Subject name for attendance.
        att_date: Attendance date (defaults to today).
        marked_by: User who triggered the processing.
        class_name: Optional class context provided by the teacher.
    """
    if att_date is None:
        att_date = date.today()
    att_time = datetime.now().time()

    async with async_session_factory() as db:
        try:
            # Mark task as processing
            await db.execute(
                update(ProcessingTask)
                .where(ProcessingTask.id == task_id)
                .values(status="processing")
            )
            await db.commit()

            # Decode image
            img_array = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise FaceDetectionException(detail="Failed to decode image")

            # Detect faces
            faces = face_analyzer.detect_faces(
                img, min_confidence=settings.FACE_DETECTION_THRESHOLD
            )

            if not faces:
                await _update_task(db, task_id, "failed", error="No faces detected in image")
                return

            recognized: list[dict] = []
            unknown_count = 0

            for i, face in enumerate(faces):
                try:
                    logger.info(
                        "ATTENDANCE DEBUG: embedding attr=%s, first5=%s",
                        "normed_embedding",
                        face.normed_embedding[:5] if hasattr(face, 'normed_embedding') else "MISSING"
                    )

                    embedding = face.normed_embedding

                    student_id_str, similarity = await find_best_match(
                        db, embedding, settings.COSINE_SIMILARITY_THRESHOLD
                    )

                    if student_id_str:
                        # ── Recognized face ──────────────────────────────
                        student_id = uuid.UUID(student_id_str)

                        # Fetch student details so we can store them on the attendance row
                        student_row = await db.execute(
                            select(Student).where(Student.id == student_id)
                        )
                        student = student_row.scalar_one_or_none()

                        # Determine the class name to mark attendance under
                        marked_class_name = class_name if class_name else (student.class_ if student else "Unknown")

                        # Authorization Check: Student can only mark attendance in their own class
                        if class_name and student and student.class_ and student.class_ != class_name:
                            logger.warning("Unauthorized attendance attempt: %s registered in %s, attempted in %s", student.name, student.class_, class_name)
                            recognized.append({
                                "student_id": student_id_str,
                                "name": student.name,
                                "similarity": round(similarity, 4),
                                "face_index": i,
                                "marked_class": class_name,
                                "unauthorized": True,
                                "registered_class": student.class_
                            })
                            continue

                        # Idempotency check
                        existing = await db.execute(
                            select(Attendance).where(
                                Attendance.student_id == student_id,
                                Attendance.date == att_date,
                                Attendance.subject == subject,
                                Attendance.class_name == marked_class_name,
                            )
                        )
                        if not existing.scalar_one_or_none():
                            record = Attendance(
                                student_id=student_id,
                                name=student.name if student else None,
                                roll_number=student.roll_number if student else None,
                                class_name=marked_class_name,
                                subject=subject,
                                date=att_date,
                                time=att_time,
                                status="present",
                                marked_by=marked_by,
                                source="auto",
                            )
                            db.add(record)

                        recognized.append({
                            "student_id": student_id_str,
                            "name": student.name if student else "Unknown",
                            "similarity": round(similarity, 4),
                            "face_index": i,
                            "marked_class": marked_class_name,
                            "unauthorized": False
                        })

                    else:
                        # ── Unknown face ──────────────────────────────────
                        logger.info("Face %d is UNKNOWN (Best match similarity: %.4f)", i, similarity)
                        
                        # Add to the results list even if unknown, so frontend can show similarity
                        recognized.append({
                            "student_id": None,
                            "name": "Unknown",
                            "similarity": round(similarity, 4),
                            "face_index": i,
                            "marked_class": class_name or "Unknown",
                            "unrecognized": True
                        })

                        # Save face crop to UnknownFace table for later ID
                        if face.bbox is not None:
                            bbox = face.bbox.astype(int)
                            x1, y1, x2, y2 = bbox
                            face_crop = img[
                                max(0, y1):min(img.shape[0], y2),
                                max(0, x1):min(img.shape[1], x2),
                            ]
                            if face_crop.size > 0:
                                _, face_bytes = cv2.imencode(".jpg", face_crop)
                                save_path = save_upload_file(
                                    contents=face_bytes.tobytes(),
                                    subdirectory="unknown_faces",
                                    prefix=f"unknown_{task_id}",
                                )
                                unknown = UnknownFace(
                                    image_path=str(save_path),
                                    embedding=embedding.tolist(),
                                )
                                db.add(unknown)

                        # Create an Attendance row for every unknown face
                        unknown_att = Attendance(
                            student_id=None,
                            name="Unknown",
                            roll_number="UNKNOWN",
                            class_name=class_name or "Unknown",
                            subject=subject,
                            date=att_date,
                            time=att_time,
                            status="present",
                            marked_by=marked_by,
                            source="auto",
                        )
                        db.add(unknown_att)
                        unknown_count += 1

                except Exception as e:
                    logger.error("Error processing face %d: %s", i, str(e), exc_info=True)

            await db.commit()

            result_data = {
                "recognized": recognized,
                "unknown_count": unknown_count,
                "total_faces": len(faces),
            }
            await _update_task(db, task_id, "completed", result=result_data)

        except Exception as e:
            logger.error("Task %s failed: %s", task_id, str(e), exc_info=True)
            await db.rollback()
            await _update_task(db, task_id, "failed", error=str(e))


async def _update_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    """Update processing task status and result."""
    values: dict = {"status": status}
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error_message"] = error

    await db.execute(
        update(ProcessingTask).where(ProcessingTask.id == task_id).values(**values)
    )
    await db.commit()
    logger.info("Task %s updated to '%s'", task_id, status)

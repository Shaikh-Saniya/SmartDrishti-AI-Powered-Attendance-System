"""Attendance export service: CSV and Excel generation."""

import csv
import io
import logging
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.student import Student

logger = logging.getLogger(__name__)


async def export_attendance(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    subject: str | None = None,
    class_name: str | None = None,
    export_format: str = "csv",
) -> tuple[bytes, str, str]:
    """Export attendance records to CSV or Excel.

    Reads name / roll_number / class_name directly from the Attendance row
    (self-contained since previous fix), so unknown faces are included and
    deleted students do NOT appear.

    Args:
        db: Async database session.
        start_date: Filter by start date (inclusive).
        end_date:   Filter by end date (inclusive).
        subject:    Filter by subject name.
        class_name: Filter by class name (e.g. 'CSE-A').
        export_format: 'csv' or 'xlsx'.

    Returns:
        Tuple of (file_bytes, content_type, filename).
    """
    # OUTER JOIN — keeps unknown faces (student_id IS NULL)
    query = (
        select(Attendance, Student.name, Student.roll_number, Student.class_)
        .outerjoin(Student, Attendance.student_id == Student.id)
        .order_by(Attendance.class_name.asc().nullslast(), Attendance.date, Attendance.time)
    )

    if start_date:
        query = query.where(Attendance.date >= start_date)
    if end_date:
        query = query.where(Attendance.date <= end_date)
    if subject:
        query = query.where(Attendance.subject == subject)
    if class_name:
        query = query.where(Attendance.class_name == class_name)

    result = await db.execute(query)
    query_rows = result.all()

    # Build plain row tuples from the Attendance object and joined Student
    headers = ["Date", "Time", "Subject", "Status", "Source", "Roll Number", "Name", "Class"]
    rows = []
    for row in query_rows:
        att = row[0]
        student_name = row[1] if len(row) > 1 else None
        student_roll = row[2] if len(row) > 2 else None
        student_class = row[3] if len(row) > 3 else None
        
        rows.append((
            str(att.date) if att.date else "",
            str(att.time) if att.time else "",
            att.subject or "",
            att.status or "",
            att.source or "",
            student_roll or att.roll_number or "UNKNOWN",
            student_name or att.name or "Unknown",
            att.class_name or student_class or "Unknown",
        ))

    logger.info("Exporting %d attendance records", len(rows))

    if export_format == "xlsx":
        return _generate_xlsx(headers, rows)
    return _generate_csv(headers, rows)


def _generate_csv(headers: list[str], rows: list) -> tuple[bytes, str, str]:
    """Generate CSV bytes from attendance data."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(list(row))

    content = output.getvalue().encode("utf-8")
    return content, "text/csv", "attendance_export.csv"


def _generate_xlsx(headers: list[str], rows: list) -> tuple[bytes, str, str]:
    """Generate a styled Excel file from attendance data."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"

    # Header style
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font   = header_font
        cell.fill   = header_fill
        cell.alignment = header_align

    # Data rows
    for row_idx, row in enumerate(rows, 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical="center")

    # Auto-adjust column widths
    for col in ws.columns:
        max_width = max((len(str(cell.value or "")) for cell in col), default=8) + 4
        ws.column_dimensions[col[0].column_letter].width = min(max_width, 35)

    # Freeze header row
    ws.freeze_panes = "A2"

    output = io.BytesIO()
    wb.save(output)
    content = output.getvalue()

    return (
        content,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "attendance_export.xlsx",
    )

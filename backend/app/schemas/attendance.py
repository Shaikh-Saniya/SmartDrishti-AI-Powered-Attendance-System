"""Pydantic v2 schemas for attendance and processing."""

import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceCreate(BaseModel):
    """Manually create attendance record."""

    student_id: Optional[uuid.UUID] = None
    subject: str = Field(..., min_length=1, max_length=100)
    date: date
    time: time
    status: str = Field(default="present", pattern="^(present|absent|late)$")


class AttendanceUpdate(BaseModel):
    """Update an existing attendance record — all editable fields.

    All fields except status are optional.
    Empty string values must be sent as null/None by the caller.
    """

    status: str = Field(..., pattern="^(present|absent|late)$")
    name: Optional[str] = None
    roll_number: Optional[str] = None
    class_name: Optional[str] = None
    subject: Optional[str] = None          # no min_length — frontend validates



class AttendanceResponse(BaseModel):
    """Attendance data in API responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    student_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    roll_number: Optional[str] = None
    class_name: Optional[str] = None
    subject: str
    date: date
    time: time
    status: str
    marked_by: Optional[uuid.UUID] = None
    source: str
    created_at: datetime
    updated_at: datetime


class ProcessGroupRequest(BaseModel):
    """Request body for group image processing."""

    subject: str = Field(..., min_length=1, max_length=100)
    date: Optional[date] = None
    notes: Optional[str] = None


class ProcessGroupResult(BaseModel):
    """Result of group image processing."""

    recognized: list[dict] = Field(default_factory=list)
    unknown_count: int = 0
    total_faces: int = 0
    errors: list[str] = Field(default_factory=list)
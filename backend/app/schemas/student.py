"""Pydantic v2 schemas for student management."""

import uuid
from datetime import datetime

from fastapi import Form
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    """Request body for creating a new student."""

    roll_number: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    class_name: str = Field(..., min_length=1, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)

    @classmethod
    def as_form(
        cls,
        roll_number: str = Form(...),
        name: str = Form(...),
        class_name: str = Form(...),
        department: str | None = Form(None),
        email: str | None = Form(None),
        phone: str | None = Form(None),
    ):
        return cls(
            roll_number=roll_number,
            name=name,
            class_name=class_name,
            department=department,
            email=email,
            phone=phone,
        )

    model_config = {"populate_by_name": True}


class StudentUpdate(BaseModel):
    """Request body for updating a student."""

    name: str | None = Field(default=None, max_length=255)
    class_name: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)

    model_config = {"populate_by_name": True}


class StudentImageResponse(BaseModel):
    """Student image data in API responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    image_path: str
    is_primary: bool
    created_at: datetime


class StudentResponse(BaseModel):
    """Student data returned in API responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    roll_number: str
    name: str
    class_: str
    department: str | None
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[StudentImageResponse] = []


class StudentListResponse(BaseModel):
    """Student data for list views (no images)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    roll_number: str
    name: str
    class_: str
    department: str | None
    is_active: bool

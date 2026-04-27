"""Pydantic v2 schemas for user and authentication."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    """Login request body."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """User data returned in API responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class TokenRefresh(BaseModel):
    """Refresh token request body."""

    refresh_token: str


class UserCreate(BaseModel):
    """Create user request (admin only)."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="teacher", pattern="^(admin|teacher)$")

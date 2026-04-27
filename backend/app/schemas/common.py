"""Common Pydantic schemas: pagination, error responses, task status."""

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)

    @property
    def offset(self) -> int:
        """Compute offset for SQL query."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper for paginated list responses."""

    items: list[T]
    total: int
    page: int
    limit: int
    pages: int

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, limit: int
    ) -> "PaginatedResponse[T]":
        """Factory method to build a paginated response."""
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)


class ErrorResponse(BaseModel):
    """Structured error response."""

    detail: str
    code: str


class TaskStatusResponse(BaseModel):
    """Response for background task status."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    task_type: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    ml_model: str
    version: str = "1.0.0"


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str

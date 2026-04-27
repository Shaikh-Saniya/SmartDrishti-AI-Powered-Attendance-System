"""Custom exception classes and FastAPI exception handlers."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        detail: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.detail = detail
        self.code = code
        self.status_code = status_code
        super().__init__(detail)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    """Authentication failed."""

    def __init__(
        self, detail: str = "Could not validate credentials", code: str = "UNAUTHORIZED"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    """Insufficient permissions."""

    def __init__(
        self, detail: str = "Insufficient permissions", code: str = "FORBIDDEN"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_403_FORBIDDEN)


class BadRequestException(AppException):
    """Invalid request data."""

    def __init__(
        self, detail: str = "Bad request", code: str = "BAD_REQUEST"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class RateLimitException(AppException):
    """Rate limit exceeded."""

    def __init__(
        self, detail: str = "Too many requests", code: str = "RATE_LIMIT_EXCEEDED"
    ) -> None:
        super().__init__(
            detail=detail, code=code, status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class FileTooLargeException(AppException):
    """Uploaded file exceeds size limit."""

    def __init__(self, detail: str = "File too large", code: str = "FILE_TOO_LARGE") -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class InvalidFileTypeException(AppException):
    """Uploaded file type not allowed."""

    def __init__(
        self, detail: str = "Invalid file type", code: str = "INVALID_FILE_TYPE"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class FaceDetectionException(AppException):
    """Face detection failed."""

    def __init__(
        self, detail: str = "Face detection failed", code: str = "FACE_DETECTION_FAILED"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_400_BAD_REQUEST)


class MLModelException(AppException):
    """ML model error."""

    def __init__(
        self, detail: str = "ML model error", code: str = "ML_MODEL_ERROR"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------- FastAPI Exception Handlers ----------


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "code": exc.code
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "code": "HTTP_ERROR"
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "code": "INTERNAL_ERROR"
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """Handle Pydantic/FastAPI validation errors with friendly messages."""
    errors = []
    
    # Check if detail is a list (typical for RequestValidationError)
    try:
        details = exc.errors() if hasattr(exc, "errors") else []
    except Exception:
        details = []
        
    for error in details:
        loc = error.get("loc", [])
        msg = error.get("msg", "Invalid value")
        
        # Friendly field names
        field_path = ".".join(str(l) for l in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else "Field"
        if "roll_number" in field_path: field_path = "Roll number"
        elif "class_name" in field_path: field_path = "Class name"
        elif "full_name" in field_path: field_path = "Full name"
        elif "password" in field_path: field_path = "Password"
        
        errors.append(f"{field_path}: {msg}")
    
    friendly_msg = " | ".join(errors) if errors else "Invalid information provided"
    
    # Log the validation error for debugging
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("Validation Error: %s", friendly_msg)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": friendly_msg,
            "code": "VALIDATION_ERROR"
        },
    )


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

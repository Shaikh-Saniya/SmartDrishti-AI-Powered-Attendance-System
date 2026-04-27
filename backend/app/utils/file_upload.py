"""Secure file upload handling with validation."""

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FileTooLargeException, InvalidFileTypeException
from app.utils.logger import get_logger

logger = get_logger(__name__)

MIME_TYPE_MAP: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/jpg": "jpg",
}


async def validate_upload_file(file: UploadFile) -> bytes:
    """Read, validate size, and verify MIME type of uploaded file."""
    contents = await file.read()

    # Check size
    if len(contents) > settings.max_upload_bytes:
        raise FileTooLargeException(
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
        )

    # ✅ CHANGED: removed magic
    mime_type = file.content_type
    if mime_type not in MIME_TYPE_MAP:
        raise InvalidFileTypeException(
            detail=f"Unsupported file type: {mime_type}. Allowed: JPEG, PNG"
        )

    # Also check file extension
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in settings.allowed_extensions_list:
            raise InvalidFileTypeException(
                detail=f"Invalid file extension: .{ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

    return contents


def save_upload_file(
    contents: bytes,
    subdirectory: str,
    prefix: str = "",
) -> Path:
    """Save file bytes to the upload directory."""

    # ✅ CHANGED: removed magic
    mime_type = "image/jpeg"
    ext = MIME_TYPE_MAP.get(mime_type, "jpg")

    # Generate unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"

    # Build save path using pathlib for Windows compatibility
    save_dir = settings.upload_path / subdirectory
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    # Write file
    save_path.write_bytes(contents)
    logger.info("File saved: %s (%d bytes)", save_path, len(contents))

    return save_path


def delete_file(file_path: str | Path) -> bool:
    """Safely delete a file from the filesystem."""
    path = Path(file_path)
    if path.exists():
        path.unlink()
        logger.info("File deleted: %s", path)
        return True
    return False


def get_temp_path() -> Path:
    """Get the temp upload directory path, creating it if needed."""
    temp_dir = settings.upload_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def cleanup_temp_files() -> int:
    """Remove all files in the temp directory. Returns count removed."""
    temp_dir = get_temp_path()
    count = 0
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            if f.is_file():
                f.unlink()
                count += 1
    return count
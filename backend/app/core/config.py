"""Core configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Face Attendance System"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-min-32-chars"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/attendance_db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # ML / InsightFace
    INSIGHTFACE_MODEL_NAME: str = "buffalo_l"
    INSIGHTFACE_ROOT: str = "./models"
    FACE_DETECTION_THRESHOLD: float = 0.5
    COSINE_SIMILARITY_THRESHOLD: float = 0.10
    CPU_MODE: bool = True

    # File Uploads
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png"
    UPLOAD_DIR: str = "./uploads"

    # Rate Limiting (requests per minute)
    RATE_LIMIT_UPLOAD: int = 10
    RATE_LIMIT_DEFAULT: int = 100

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://127.0.0.1:3000",
        "http://[::1]:3000"
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # Derived properties
    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        """List of allowed file extensions."""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        return Path(self.UPLOAD_DIR).resolve()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()

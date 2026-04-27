"""FastAPI application with lifespan management."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestIDMiddleware
from app.dependencies.db import get_db
from app.ml.insightface_loader import face_analyzer
from app.schemas.common import HealthResponse
from app.services.cleanup_service import start_cleanup_scheduler, stop_cleanup_scheduler
from app.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # ----- Startup -----
    setup_logging()
    logger.info("Starting %s...", settings.APP_NAME)

    # pgvector codec is now registered via SQLAlchemy events in db/session.py

    # Load InsightFace model once at startup
    try:
        face_analyzer.load_model(
            model_name=settings.INSIGHTFACE_MODEL_NAME,
            model_root=settings.INSIGHTFACE_ROOT,
        )
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.error("Failed to load ML model: %s", str(e))
        logger.warning("Application will start without ML capabilities")

    # Start background cleanup scheduler
    start_cleanup_scheduler()

    yield

    # ----- Shutdown -----
    stop_cleanup_scheduler()
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Face Clustering Attendance System — Admin/Teacher Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ----- Middleware -----
# Order: Last added is processed first (outermost).
# We want CORS to be the outermost so it handles preflights and adds headers to all responses.
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Exception Handlers -----
register_exception_handlers(app)

# ----- API Routers -----
from app.api.v1.auth import router as auth_router
from app.api.v1.students import router as students_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.unknown_faces import router as unknown_faces_router
from app.api.v1.tasks import router as tasks_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(students_router, prefix=settings.API_V1_PREFIX)
app.include_router(attendance_router, prefix=settings.API_V1_PREFIX)
app.include_router(unknown_faces_router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks_router, prefix=settings.API_V1_PREFIX)


# ----- Health & Metrics -----
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check: verify DB connection and ML model status."""
    from app.db.session import engine

    db_status = "unhealthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error("Health check DB error: %s", str(e))

    ml_status = "loaded" if face_analyzer.is_loaded else "not_loaded"

    overall = "healthy" if db_status == "healthy" else "unhealthy"
    return HealthResponse(
        status=overall,
        database=db_status,
        ml_model=ml_status,
    )


@app.get("/metrics", tags=["Health"])
async def metrics() -> dict:
    """Basic application metrics."""
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "ml_model_loaded": face_analyzer.is_loaded,
    }

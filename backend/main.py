"""
Syllabus AI Study Assistant — Main Application
===============================================
FastAPI entry point with modular route registration,
middleware setup, and health monitoring.

Run with: uvicorn main:app --reload --port 8000
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from core.middleware import setup_middleware
from models.database import health_check_db
from services import rag_service, llm_service

# ── Logging Setup ────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO if settings.is_development else logging.WARNING,
    format="%(asctime)s │ %(name)-12s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("syllabus_ai")


# ── Application Lifespan ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info(f"  Environment: {settings.app_env}")
    logger.info(f"  Port: {settings.app_port}")
    logger.info("=" * 60)

    # Ensure document directories exist with section subdirectories
    for subject_code in ["COA", "APJ", "DAA", "DM", "OB"]:
        doc_dir = Path(settings.document_storage_dir) / subject_code
        doc_dir.mkdir(parents=True, exist_ok=True)
        # Create section subdirectories (A, B, C) for each subject
        for section in ["A", "B", "C"]:
            section_dir = doc_dir / section
            section_dir.mkdir(parents=True, exist_ok=True)

    # Ensure ChromaDB directory exists
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)

    logger.info("✓ Directory structure initialized")
    logger.info("✓ Application ready")
    logger.info("-" * 60)

    yield  # Application runs

    logger.info("Shutting down...")


# ── FastAPI Application ──────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered study assistant for university exam preparation. "
        "Grounded strictly in uploaded syllabus materials using RAG."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── Middleware ────────────────────────────────────────────────
setup_middleware(app)


# ── Route Registration ───────────────────────────────────────

from routes.subjects import router as subjects_router
from routes.chat import router as chat_router
from routes.documents import router as documents_router
from routes.study_plan import router as study_plan_router
from routes.memory import router as memory_router
from routes.study_mode import router as study_mode_router
from routes.admin import router as admin_router
from routes.feedback import router as feedback_router

app.include_router(subjects_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(study_plan_router)
app.include_router(memory_router)
app.include_router(study_mode_router)
app.include_router(admin_router)
app.include_router(feedback_router)


# ── Health & Status Endpoints ────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — application info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.app_env,
        "docs": "/docs" if settings.is_development else "disabled"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive system health check."""
    # Check all subsystems
    db_health = health_check_db()
    llm_health = await llm_service.health_check()

    try:
        rag_health = await rag_service.health_check()
    except Exception:
        rag_health = {"status": "not_initialized"}

    overall_status = "healthy"
    if llm_health.get("status") == "error":
        overall_status = "degraded"
    if db_health.get("status") == "error":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "services": {
            "database": db_health,
            "llm": llm_health,
            "rag": rag_health
        }
    }


@app.get("/api/status", tags=["Health"])
async def api_status():
    """Quick API status check."""
    return {
        "success": True,
        "message": "Syllabus AI Study Assistant is running",
        "modules": {
            "subjects": "active",
            "chat": "active",
            "documents": "active",
            "memory": "active",
            "study_mode": "active"
        }
    }

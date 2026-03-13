"""
Middleware configuration for Nexora Study Assistant.
Handles CORS, request logging, and error formatting.
"""

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings

logger = logging.getLogger("syllabus_ai")


def setup_middleware(app: FastAPI) -> None:
    """Configure all application middleware."""

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Logging ──────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        logger.info(f"→ {request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"✗ {request.method} {request.url.path} — {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "detail": str(exc) if settings.is_development else None
                }
            )

        duration = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] {duration}ms"
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration}ms"
        return response

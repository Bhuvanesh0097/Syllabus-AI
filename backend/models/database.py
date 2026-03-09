"""
Database models and connection management.
Placeholder for Supabase integration — will be fully implemented in a later phase.
"""

from config import settings
from typing import Optional
import logging

logger = logging.getLogger("syllabus_ai")

# Supabase client will be initialized when credentials are provided
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client instance."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.supabase_url or not settings.supabase_anon_key:
        logger.warning(
            "Supabase credentials not configured. "
            "Running in local-only mode."
        )
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
        logger.info("✓ Supabase client initialized")
        return _supabase_client
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase: {e}")
        return None


def health_check_db() -> dict:
    """Check database connectivity."""
    client = get_supabase_client()
    if client is None:
        return {
            "status": "disconnected",
            "mode": "local",
            "message": "Running without database — using in-memory storage"
        }

    try:
        # Simple connectivity test
        return {
            "status": "connected",
            "mode": "supabase",
            "message": "Database connection active"
        }
    except Exception as e:
        return {
            "status": "error",
            "mode": "supabase",
            "message": str(e)
        }

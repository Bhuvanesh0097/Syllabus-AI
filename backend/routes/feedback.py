"""
Feedback Routes — endpoints for submitting and retrieving user feedback.
Saves feedback to a local JSON file.
Completely isolated — does not affect chat, RAG, LLM, or any other service.
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])
logger = logging.getLogger("syllabus_ai")

# ── Feedback storage path ────────────────────────────────────
FEEDBACK_FILE = Path(__file__).parent.parent / "data" / "feedback.json"


# ── Schemas ──────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    """Incoming feedback submission."""
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    comment: Optional[str] = Field(None, max_length=1000)
    student_name: Optional[str] = None
    section: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool = True
    message: str = ""
    feedback_id: str = ""
    whatsapp_link: str = ""


# ── Helper Functions ─────────────────────────────────────────

def _load_feedback() -> list:
    """Load existing feedback from the JSON file."""
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def _save_feedback(entries: list):
    """Save feedback entries to the JSON file."""
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str)


def _generate_whatsapp_link(rating: int, comment: str, student_name: str = "") -> str:
    """
    Generate a WhatsApp wa.me link with pre-filled feedback message.
    Uses the business WhatsApp number: +91 8825921420
    """
    import urllib.parse

    phone = "918825921420"  # Business WhatsApp number (no + sign for wa.me)

    # Build star display
    stars = "⭐" * rating + "☆" * (5 - rating)

    # Format the message
    lines = [
        "📋 *Nexora — Student Feedback*",
        "",
        f"⭐ *Rating:* {stars} ({rating}/5)",
    ]

    if student_name:
        lines.append(f"👤 *Student:* {student_name}")

    if comment:
        lines.append(f"💬 *Comment:* {comment}")

    lines.append("")
    lines.append(f"📅 *Date:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    lines.append("")
    lines.append("— Sent from Nexora Study Assistant")

    message = "\n".join(lines)
    encoded = urllib.parse.quote(message)

    return f"https://wa.me/{phone}?text={encoded}"


# ── Endpoints ────────────────────────────────────────────────

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback with a star rating and optional comment.
    Saves to local storage and returns a WhatsApp share link.
    """
    feedback_id = str(uuid.uuid4())[:8]

    # Build feedback entry
    entry = {
        "id": feedback_id,
        "rating": request.rating,
        "comment": request.comment or "",
        "student_name": request.student_name or "Anonymous",
        "section": request.section or "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Save to JSON file
    try:
        entries = _load_feedback()
        entries.append(entry)
        _save_feedback(entries)
        logger.info(f"✓ Feedback saved: {feedback_id} — {request.rating}⭐")
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {e}")

    # Generate WhatsApp link
    whatsapp_link = _generate_whatsapp_link(
        rating=request.rating,
        comment=request.comment or "",
        student_name=request.student_name or ""
    )

    return FeedbackResponse(
        success=True,
        message="Thank you for your feedback! 🎉",
        feedback_id=feedback_id,
        whatsapp_link=whatsapp_link
    )


@router.get("/all")
async def get_all_feedback():
    """Get all submitted feedback (admin view)."""
    entries = _load_feedback()
    avg_rating = (
        sum(e["rating"] for e in entries) / len(entries) if entries else 0
    )
    return {
        "success": True,
        "total": len(entries),
        "average_rating": round(avg_rating, 1),
        "feedback": list(reversed(entries)),  # Newest first
    }

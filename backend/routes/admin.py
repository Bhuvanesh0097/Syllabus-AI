"""
Admin Routes — PIN verification for Knowledge Base access.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from config import settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class PinRequest(BaseModel):
    pin: str = Field(..., min_length=1)


@router.post("/verify-pin")
async def verify_pin(request: PinRequest):
    """Verify admin PIN to unlock Knowledge Base access."""
    if request.pin == settings.admin_pin:
        return {"success": True, "message": "Access granted"}
    return {"success": False, "message": "Invalid PIN"}

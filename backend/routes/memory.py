"""
Memory Routes — endpoints for student profile, progress, and welcome-back.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from services import memory_service

router = APIRouter(prefix="/api/memory", tags=["Memory"])


class StudentProfileRequest(BaseModel):
    """Request to save a student profile."""
    name: str
    department: str = "CSE"
    year: str = "2nd Year"
    semester: str = "4th Semester"
    section: str = ""


@router.get("/progress")
async def get_progress():
    """Get overall student progress."""
    progress = await memory_service.get_progress("default_student")
    return {"success": True, "progress": progress}


@router.get("/progress/{subject_code}")
async def get_subject_progress(subject_code: str):
    """Get progress for a specific subject."""
    summary = await memory_service.get_study_summary(
        "default_student", subject_code.upper()
    )
    return {"success": True, "summary": summary}


@router.post("/profile")
async def save_profile(request: StudentProfileRequest):
    """Save or update the student's profile."""
    profile = await memory_service.save_student_profile(
        student_id="default_student",
        name=request.name,
        department=request.department,
        year=request.year,
        semester=request.semester,
        section=request.section,
    )
    return {"success": True, "profile": profile}


@router.get("/profile")
async def get_profile():
    """Get the student's saved profile."""
    profile = await memory_service.get_student_profile("default_student")
    if profile:
        return {"success": True, "exists": True, "profile": profile}
    return {"success": True, "exists": False, "profile": None}


@router.get("/welcome-back")
async def get_welcome_back():
    """
    Get welcome-back data for a returning student.
    Returns previous session info, study suggestions, and personalized context.
    """
    data = await memory_service.get_welcome_back_data("default_student")
    if data:
        return {"success": True, "returning": True, "data": data}
    return {"success": True, "returning": False, "data": None}


@router.get("/welcome-back/{name}")
async def get_welcome_back_by_name(name: str):
    """
    Check if a student by name has previous sessions.
    Used by the Landing page to detect returning students.
    """
    # First try to find student by name
    profile = await memory_service.find_student_by_name(name)
    if profile and profile.get("total_interactions", 0) > 0:
        student_id = profile.get("student_id", "default_student")
        data = await memory_service.get_welcome_back_data(student_id)
        return {"success": True, "returning": True, "data": data}
    return {"success": True, "returning": False, "data": None}

"""
Study Plan Routes — endpoint for RAG-powered study plan generation.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services import study_plan_service

logger = logging.getLogger("syllabus_ai")

router = APIRouter(prefix="/api/study-plan", tags=["Study Plan"])


class StudyPlanRequest(BaseModel):
    subject_code: str = Field(..., min_length=1)
    units: Optional[List[int]] = Field(default=None)
    hours_per_day: Optional[float] = Field(default=None, ge=0.5, le=12)
    section: Optional[str] = None
    days_available: Optional[int] = Field(default=None, ge=1, le=30)
    custom_request: Optional[str] = None


@router.post("/generate")
async def generate_plan(request: StudyPlanRequest):
    """
    Generate a RAG-powered, day-by-day structured study plan.

    Retrieves actual syllabus topics from uploaded PDFs,
    then uses an expert planner LLM prompt to produce
    a professional exam-focused schedule.
    """
    try:
        result = await study_plan_service.generate_study_plan(
            subject_code=request.subject_code,
            units=request.units or [1, 2, 3, 4, 5],
            hours_per_day=request.hours_per_day or 2.0,
            section=request.section,
            days_available=request.days_available,
            custom_request=request.custom_request,
        )
    except Exception as e:
        logger.error(f"Study plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {e}")

    return {"success": True, "plan": result}


class StudyPlanRefineRequest(BaseModel):
    subject_code: str = Field(..., min_length=1)
    current_plan: str = Field(..., min_length=1)
    modification_request: str = Field(..., min_length=1)
    section: Optional[str] = None


@router.post("/refine")
async def refine_plan(request: StudyPlanRefineRequest):
    """
    Refine an existing study plan based on user feedback.
    Takes the current plan and a modification request,
    returns an updated plan.
    """
    try:
        result = await study_plan_service.refine_study_plan(
            subject_code=request.subject_code,
            current_plan=request.current_plan,
            modification_request=request.modification_request,
            section=request.section,
        )
    except Exception as e:
        logger.error(f"Study plan refinement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refine study plan: {e}")

    return {"success": True, "plan": result}

"""
Subject Routes — endpoints for subject and unit information.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.schemas import SubjectListResponse, SubjectSchema, GenericResponse
from services import rag_service

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])

# Load subject data
_subjects_data = None


def _load_subjects():
    """Load subjects from JSON file."""
    global _subjects_data
    if _subjects_data is not None:
        return _subjects_data

    data_path = Path(__file__).parent.parent / "data" / "subjects.json"
    with open(data_path, "r", encoding="utf-8") as f:
        _subjects_data = json.load(f)
    return _subjects_data


@router.get("/", response_model=SubjectListResponse)
async def get_all_subjects():
    """Get all available subjects with their units."""
    data = _load_subjects()
    return SubjectListResponse(
        subjects=[SubjectSchema(**s) for s in data["subjects"]],
        metadata=data["metadata"]
    )


@router.get("/{subject_code}")
async def get_subject(subject_code: str):
    """Get a specific subject by code."""
    data = _load_subjects()
    subject = next(
        (s for s in data["subjects"] if s["code"].upper() == subject_code.upper()),
        None
    )

    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_code}' not found")

    return {"success": True, "subject": subject}


@router.get("/{subject_code}/units/{unit_number}")
async def get_unit(subject_code: str, unit_number: int):
    """Get a specific unit from a subject."""
    data = _load_subjects()
    subject = next(
        (s for s in data["subjects"] if s["code"].upper() == subject_code.upper()),
        None
    )

    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_code}' not found")

    unit = next(
        (u for u in subject["units"] if u["number"] == unit_number),
        None
    )

    if not unit:
        raise HTTPException(
            status_code=404,
            detail=f"Unit {unit_number} not found in '{subject_code}'"
        )

    return {
        "success": True,
        "subject": {"code": subject["code"], "name": subject["name"]},
        "unit": unit
    }


@router.get("/{subject_code}/stats")
async def get_subject_stats(
    subject_code: str,
    section: Optional[str] = Query(None, description="Section A, B, or C")
):
    """Get document/RAG stats for a subject, optionally filtered by section."""
    try:
        stats = await rag_service.get_collection_stats(subject_code, section)
        return {"success": True, "subject_code": subject_code, "section": section, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


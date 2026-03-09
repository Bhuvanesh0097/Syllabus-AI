"""
Study Mode Routes — endpoints for 2-mark and 10-mark exam preparation modes.
Generates structured question lists from uploaded syllabus materials via RAG + LLM.
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from services import llm_service, rag_service

logger = logging.getLogger("syllabus_ai")

router = APIRouter(prefix="/api/study-mode", tags=["Study Mode"])

# ── Load subject data ────────────────────────────────────────
_subjects_data = {}
try:
    subjects_path = Path(__file__).parent.parent / "data" / "subjects.json"
    with open(subjects_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for subject in data.get("subjects", []):
            _subjects_data[subject["code"]] = subject
except Exception:
    pass


def _get_subject_info(code: str) -> dict:
    return _subjects_data.get(code, {"name": code, "short_name": code, "units": []})


def _get_unit_title(subject_code: str, unit_number: int) -> str:
    info = _get_subject_info(subject_code)
    for unit in info.get("units", []):
        if unit.get("number") == unit_number:
            return unit.get("title", f"Unit {unit_number}")
    return f"Unit {unit_number}"


# ── Request/Response Models ──────────────────────────────────

class StudyModeRequest(BaseModel):
    subject_code: str = Field(..., min_length=1)
    unit_number: int = Field(..., ge=1, le=5)
    mode: str = Field(..., pattern="^(2_mark|10_mark)$")
    section: Optional[str] = None


class QuestionItem(BaseModel):
    id: int
    question: str


class StudyModeQuestionsResponse(BaseModel):
    success: bool = True
    subject_code: str
    unit_number: int
    unit_title: str
    subject_name: str
    mode: str
    questions: List[QuestionItem]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnswerRequest(BaseModel):
    subject_code: str = Field(..., min_length=1)
    unit_number: int = Field(..., ge=1, le=5)
    mode: str = Field(..., pattern="^(2_mark|10_mark)$")
    question: str = Field(..., min_length=1)
    section: Optional[str] = None


class AnswerResponse(BaseModel):
    success: bool = True
    question: str
    answer: str
    mode: str
    subject_code: str
    unit_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# GET QUESTIONS — Extract questions from syllabus via RAG + LLM
# ═══════════════════════════════════════════════════════════════

@router.post("/questions", response_model=StudyModeQuestionsResponse)
async def get_study_questions(request: StudyModeRequest):
    """
    Generate a list of exam questions (2-mark or 10-mark) for a specific unit.
    Uses RAG to retrieve syllabus context, then LLM to extract questions.
    """
    subject_info = _get_subject_info(request.subject_code)
    subject_name = subject_info.get("name", request.subject_code)
    unit_title = _get_unit_title(request.subject_code, request.unit_number)

    # Step 1: Retrieve RAG context for the entire unit (with section for section-specific collections)
    context = ""
    try:
        context = await rag_service.retrieve_context(
            query=f"All important topics concepts definitions theorems in {unit_title}",
            subject_code=request.subject_code,
            unit_number=request.unit_number,
            section=request.section,
            top_k=10  # Get more context for comprehensive question generation
        )
        logger.info(f"Study mode RAG context: {len(context)} chars for {request.subject_code} Unit {request.unit_number} Section {request.section}")
    except Exception as e:
        logger.warning(f"RAG retrieval failed for study mode: {e}")

    # Step 2: Generate questions via LLM
    try:
        questions = await llm_service.generate_study_questions(
            subject_name=subject_name,
            unit_title=unit_title,
            unit_number=request.unit_number,
            mode=request.mode,
            context=context
        )
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )

    return StudyModeQuestionsResponse(
        subject_code=request.subject_code,
        unit_number=request.unit_number,
        unit_title=unit_title,
        subject_name=subject_name,
        mode=request.mode,
        questions=[
            QuestionItem(id=i + 1, question=q)
            for i, q in enumerate(questions)
        ]
    )


# ═══════════════════════════════════════════════════════════════
# GET ANSWER — Generate exam-ready answer for a specific question
# ═══════════════════════════════════════════════════════════════

@router.post("/answer", response_model=AnswerResponse)
async def get_question_answer(request: AnswerRequest):
    """
    Generate an exam-ready answer for a specific question.
    Uses RAG context + LLM with appropriate answer style.
    """
    subject_info = _get_subject_info(request.subject_code)
    subject_name = subject_info.get("name", request.subject_code)
    unit_title = _get_unit_title(request.subject_code, request.unit_number)

    # Step 1: Retrieve RAG context specific to the question (with section)
    context = ""
    try:
        context = await rag_service.retrieve_context(
            query=request.question,
            subject_code=request.subject_code,
            unit_number=request.unit_number,
            section=request.section,
            top_k=5
        )
    except Exception as e:
        logger.warning(f"RAG retrieval failed for answer: {e}")

    # Step 2: Generate the answer via existing LLM service
    try:
        answer, quality = await llm_service.generate_response(
            user_message=request.question,
            context=context,
            subject_name=subject_name,
            unit_title=unit_title,
            answer_style=request.mode,  # "2_mark" or "10_mark"
        )
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {str(e)}"
        )

    return AnswerResponse(
        question=request.question,
        answer=answer,
        mode=request.mode,
        subject_code=request.subject_code,
        unit_number=request.unit_number,
    )

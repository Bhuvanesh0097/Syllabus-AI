"""
Pydantic schemas for request/response validation.
Single source of truth for all data structures across the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class AnswerStyle(str, Enum):
    """Supported answer styles for exam preparation."""
    TWO_MARK = "2_mark"
    TEN_MARK = "10_mark"
    EXPLANATION = "explanation"
    SUMMARY = "summary"
    QUICK_REVISION = "quick_revision"


class StudyPlanType(str, Enum):
    """Types of study plans the AI can generate."""
    FULL_PREP = "full_preparation"
    QUICK_REVISION = "quick_revision"
    NIGHT_BEFORE = "night_before_exam"
    CUSTOM = "custom"


# ═══════════════════════════════════════════════════════════════
# Subject & Unit Schemas
# ═══════════════════════════════════════════════════════════════

class UnitSchema(BaseModel):
    number: int
    title: str
    topics: List[str] = []


class SubjectSchema(BaseModel):
    code: str
    name: str
    short_name: str
    description: str
    icon: str
    color: str
    units: List[UnitSchema]


class SubjectListResponse(BaseModel):
    success: bool = True
    subjects: List[SubjectSchema]
    metadata: Dict[str, Any] = {}


# ═══════════════════════════════════════════════════════════════
# Chat Schemas
# ═══════════════════════════════════════════════════════════════

class ChatMessageRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., min_length=1, max_length=5000)
    subject_code: Optional[str] = None
    unit_number: Optional[int] = None
    section: Optional[str] = None
    answer_style: Optional[AnswerStyle] = None
    chat_id: Optional[str] = None
    tone: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """AI response to a chat message."""
    success: bool = True
    chat_id: str
    message: str
    subject_code: Optional[str] = None
    unit_number: Optional[int] = None
    sources: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistoryItem(BaseModel):
    """A single message in chat history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    subject_code: Optional[str] = None
    unit_number: Optional[int] = None


class ChatSession(BaseModel):
    """A complete chat session."""
    chat_id: str
    title: str
    subject_code: Optional[str] = None
    messages: List[ChatHistoryItem] = []
    created_at: datetime
    updated_at: datetime


class ChatListResponse(BaseModel):
    """List of chat sessions."""
    success: bool = True
    chats: List[ChatSession]


class StartSessionRequest(BaseModel):
    """Request to start a new study session with AI greeting."""
    student_name: str = Field(..., min_length=1, max_length=100)
    subject_code: str = Field(..., min_length=1)
    unit_number: int = Field(..., ge=1, le=5)
    section: Optional[str] = None
    department: str = "CSE"
    year: str = "2nd Year"
    semester: str = "4th Semester"


class StartSessionResponse(BaseModel):
    """Response with AI greeting and session info."""
    success: bool = True
    chat_id: str
    greeting: str
    subject_code: str
    unit_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# Document Schemas
# ═══════════════════════════════════════════════════════════════

class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    success: bool = True
    filename: str
    subject_code: str
    unit_number: Optional[int] = None
    section: Optional[str] = None
    chunks_created: int = 0
    message: str = ""


class DocumentListItem(BaseModel):
    """Metadata for an uploaded document."""
    filename: str
    subject_code: str
    unit_number: Optional[int] = None
    upload_date: datetime
    size_bytes: int
    chunk_count: int


class DocumentListResponse(BaseModel):
    success: bool = True
    documents: List[DocumentListItem]


# ═══════════════════════════════════════════════════════════════
# Study Plan Schemas
# ═══════════════════════════════════════════════════════════════

class StudyPlanRequest(BaseModel):
    """Request to generate a study plan."""
    subject_code: Optional[str] = None  # None = all subjects
    available_hours: float = Field(..., gt=0, le=72)
    plan_type: StudyPlanType = StudyPlanType.FULL_PREP
    units_to_cover: Optional[List[int]] = None
    custom_instructions: Optional[str] = None


class StudyPlanBlock(BaseModel):
    """A single block in the study plan."""
    time_slot: str
    duration_minutes: int
    subject_code: str
    unit_number: int
    topic: str
    activity: str
    priority: str  # "high", "medium", "low"


class StudyPlanResponse(BaseModel):
    """Generated study plan."""
    success: bool = True
    plan_type: StudyPlanType
    total_hours: float
    blocks: List[StudyPlanBlock]
    tips: List[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# Memory Schemas
# ═══════════════════════════════════════════════════════════════

class MemoryEntry(BaseModel):
    """A single memory entry for a student."""
    subject_code: str
    unit_number: int
    topic: str
    interaction_type: str  # "studied", "asked_question", "completed_quiz"
    confidence_level: Optional[float] = None  # 0.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StudentProgress(BaseModel):
    """Overall progress for a student."""
    subjects_progress: Dict[str, Dict[str, Any]] = {}
    total_interactions: int = 0
    topics_studied: List[str] = []
    last_active: Optional[datetime] = None
    strengths: List[str] = []
    weaknesses: List[str] = []


class MemoryResponse(BaseModel):
    success: bool = True
    progress: StudentProgress


# ═══════════════════════════════════════════════════════════════
# Generic Response
# ═══════════════════════════════════════════════════════════════

class GenericResponse(BaseModel):
    """Generic API response."""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None

"""
Chat Routes — endpoints for the AI chat system.
Handles message processing, chat history, session management, and greeting generation.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatListResponse,
    ChatSession,
    ChatHistoryItem,
    GenericResponse,
    StartSessionRequest,
    StartSessionResponse
)
from services import llm_service, rag_service, memory_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# ── In-Memory Chat Storage (Phase 1) ─────────────────────────
# Will be replaced with Supabase persistence in Phase 8
_chat_sessions: Dict[str, Dict] = {}

# ── Load subject data for name lookups ────────────────────────
_subjects_data = {}
try:
    subjects_path = Path(__file__).parent.parent / "data" / "subjects.json"
    with open(subjects_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for subject in data.get("subjects", []):
            _subjects_data[subject["code"]] = subject
except Exception:
    pass  # Will work without subject names


def _get_subject_info(code: str) -> dict:
    """Get subject info from loaded data."""
    return _subjects_data.get(code, {"name": code, "short_name": code, "units": []})


def _get_unit_title(subject_code: str, unit_number: int) -> str:
    """Get unit title from subject data."""
    info = _get_subject_info(subject_code)
    for unit in info.get("units", []):
        if unit.get("number") == unit_number:
            return unit.get("title", f"Unit {unit_number}")
    return f"Unit {unit_number}"


# ── Smart Subject/Unit Detection ──────────────────────────────
import re

# Subject name → code mapping (case-insensitive)
_SUBJECT_ALIASES = {}
for code, subj in _subjects_data.items():
    _SUBJECT_ALIASES[code.lower()] = code
    _SUBJECT_ALIASES[subj.get("name", "").lower()] = code
    _SUBJECT_ALIASES[subj.get("short_name", "").lower()] = code

# Common abbreviations
_SUBJECT_ALIASES.update({
    "coa": "COA", "computer organization": "COA",
    "apj": "APJ", "java": "APJ", "advanced java": "APJ",
    "daa": "DAA", "algorithms": "DAA", "algorithm": "DAA",
    "dm": "DM", "discrete math": "DM", "discrete mathematics": "DM",
    "ob": "OB", "organizational behaviour": "OB", "organizational behavior": "OB",
})


def _detect_subject_switch(message: str) -> Dict:
    """
    Detect if the student wants to switch subject or unit.
    Returns {"subject_code": ..., "unit_number": ...} or empty dict.
    
    Patterns matched:
      - "I want to study OB Unit 2"
      - "switch to DAA unit 3"
      - "let's do algorithms unit 1"
      - "change subject to discrete math"
      - "move to unit 4"
    """
    msg = message.lower().strip()
    result = {}

    # Check for subject mention
    for alias, code in _SUBJECT_ALIASES.items():
        if alias and len(alias) >= 2 and alias in msg:
            result["subject_code"] = code
            break

    # Check for unit mention
    unit_match = re.search(r'unit\s*(\d)', msg)
    if unit_match:
        unit_num = int(unit_match.group(1))
        if 1 <= unit_num <= 5:
            result["unit_number"] = unit_num

    # Only return if there's a switching intent
    switch_keywords = [
        "switch", "change", "move to", "go to", "want to study",
        "let's do", "let's study", "start studying", "prepare for",
        "switch to", "change to", "i want", "let me study",
    ]
    has_intent = any(kw in msg for kw in switch_keywords)

    # If both subject and unit detected, always return even without intent keywords
    if result.get("subject_code") and result.get("unit_number"):
        return result

    # If only one is detected, require switching intent
    if has_intent and result:
        return result

    return {}


# ═══════════════════════════════════════════════════════════════
# Start Session — AI Greeting with Unit Overview
# ═══════════════════════════════════════════════════════════════

@router.post("/start-session", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """
    Start a new study session.
    The AI generates a personalized greeting and unit overview.
    """
    chat_id = str(uuid.uuid4())

    # Get subject and unit info
    subject_info = _get_subject_info(request.subject_code)
    subject_name = subject_info.get("name", request.subject_code)
    unit_title = _get_unit_title(request.subject_code, request.unit_number)

    # Retrieve any RAG context for the unit (section-specific)
    context = ""
    try:
        context = await rag_service.retrieve_context(
            query=f"Overview of {unit_title} topics syllabus",
            subject_code=request.subject_code,
            unit_number=request.unit_number,
            section=request.section
        )
    except Exception:
        pass

    # Generate AI greeting with unit overview
    greeting = await llm_service.generate_greeting(
        student_name=request.student_name,
        subject_code=request.subject_code,
        subject_name=subject_name,
        unit_number=request.unit_number,
        unit_title=unit_title,
        section=request.section or "",
        context=context
    )

    # Create the chat session with the greeting as the first message
    _chat_sessions[chat_id] = {
        "chat_id": chat_id,
        "title": f"{subject_name} — {unit_title}",
        "subject_code": request.subject_code,
        "section": request.section or None,
        "student_name": request.student_name,
        "messages": [
            {
                "role": "assistant",
                "content": greeting,
                "timestamp": datetime.utcnow().isoformat(),
                "subject_code": request.subject_code,
                "unit_number": request.unit_number
            }
        ],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    # Record to memory — save profile + session
    try:
        await memory_service.save_student_profile(
            student_id="default_student",
            name=request.student_name,
            department=request.department,
            year=request.year,
            semester=request.semester,
            section=request.section or "",
        )
        await memory_service.record_session(
            student_id="default_student",
            subject_code=request.subject_code,
            unit_number=request.unit_number,
            session_type="study",
        )
        await memory_service.record_interaction(
            student_id="default_student",
            subject_code=request.subject_code,
            unit_number=request.unit_number,
            topic=f"Started study session — {unit_title}",
            interaction_type="session_start"
        )
    except Exception:
        pass

    return StartSessionResponse(
        chat_id=chat_id,
        greeting=greeting,
        subject_code=request.subject_code,
        unit_number=request.unit_number
    )


# ═══════════════════════════════════════════════════════════════
# Send Message — Main Chat Endpoint
# ═══════════════════════════════════════════════════════════════

@router.post("/message")
async def send_message(request: ChatMessageRequest):
    """
    Send a message to the AI assistant and get a response.
    Integrates RAG context retrieval and LLM generation.
    """
    # Get or create chat session
    chat_id = request.chat_id or str(uuid.uuid4())

    if chat_id not in _chat_sessions:
        _chat_sessions[chat_id] = {
            "chat_id": chat_id,
            "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
            "subject_code": request.subject_code,
            "messages": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    session = _chat_sessions[chat_id]

    # ── Smart Subject/Unit Switch Detection ──
    context_switch = _detect_subject_switch(request.message)
    effective_subject = context_switch.get("subject_code", request.subject_code)
    effective_unit = context_switch.get("unit_number", request.unit_number)

    # Update subject context
    if effective_subject:
        session["subject_code"] = effective_subject

    # Record user message
    session["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat(),
        "subject_code": effective_subject,
        "unit_number": effective_unit
    })

    # Step 1: Retrieve RAG context (using effective subject/unit and session section)
    context = ""
    session_section = session.get("section") or request.section
    if effective_subject:
        context = await rag_service.retrieve_context(
            query=request.message,
            subject_code=effective_subject,
            unit_number=effective_unit,
            section=session_section
        )

    # Enforce syllabus-only rule: if no context retrieved, tell the LLM explicitly
    if not context and effective_subject:
        context = (
            "[NO SYLLABUS DOCUMENTS FOUND]\n"
            "There are no uploaded syllabus materials for this subject/unit. "
            "You MUST inform the student: 'No syllabus documents have been uploaded for this unit yet. "
            "Please upload your study materials through the Knowledge Base page so I can help you with "
            "syllabus-specific answers.' Do NOT answer from general knowledge."
        )

    # Step 2: Build chat history for context
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in session["messages"][-10:]  # Last 10 messages
    ]

    # Step 3: Generate AI response
    quality = None
    try:
        # Get subject name for prompt context
        subject_info = _get_subject_info(effective_subject)
        subject_name = subject_info.get("name", effective_subject or "General")
        unit_title = _get_unit_title(effective_subject, effective_unit) if effective_unit else "General"

        # If context switch detected, prepend instruction
        user_msg = request.message
        if context_switch:
            switch_note = f"[The student wants to switch to {subject_name}"
            if context_switch.get("unit_number"):
                switch_note += f" Unit {context_switch['unit_number']}"
            switch_note += ". Acknowledge the switch and answer in the new context.]"
            user_msg = f"{switch_note}\n\n{request.message}"

        ai_response, quality = await llm_service.generate_response(
            user_message=user_msg,
            context=context,
            subject_name=subject_name,
            unit_title=unit_title,
            answer_style=request.answer_style.value if request.answer_style else "explanation",
            chat_history=chat_history[:-1],  # Exclude current message
            tone=request.tone
        )
    except Exception as e:
        ai_response = (
            "I apologize, but I'm having trouble generating a response right now. "
            "Please make sure the Gemini API key is configured and try again."
        )

    # Record AI response
    session["messages"].append({
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.utcnow().isoformat(),
        "subject_code": effective_subject,
        "unit_number": effective_unit
    })

    session["updated_at"] = datetime.utcnow().isoformat()

    # Step 4: Record to memory (fire-and-forget)
    if effective_subject and effective_unit:
        try:
            await memory_service.record_interaction(
                student_id="default_student",
                subject_code=effective_subject,
                unit_number=effective_unit,
                topic=request.message[:100],
                interaction_type="asked_question"
            )
        except Exception:
            pass

    # Build response — include context_switch and quality info
    response = {
        "success": True,
        "chat_id": chat_id,
        "message": ai_response,
        "subject_code": effective_subject,
        "unit_number": effective_unit,
        "sources": [],
        "timestamp": datetime.utcnow().isoformat(),
    }
    if context_switch:
        response["context_switch"] = context_switch
    if quality:
        response["quality"] = quality

    return response


# ═══════════════════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════════════════

@router.get("/sessions", response_model=ChatListResponse)
async def get_chat_sessions():
    """Get all chat sessions."""
    sessions = []
    for session in _chat_sessions.values():
        sessions.append(ChatSession(
            chat_id=session["chat_id"],
            title=session["title"],
            subject_code=session.get("subject_code"),
            messages=[
                ChatHistoryItem(
                    role=m["role"],
                    content=m["content"],
                    timestamp=m["timestamp"],
                    subject_code=m.get("subject_code"),
                    unit_number=m.get("unit_number")
                )
                for m in session["messages"]
            ],
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        ))

    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return ChatListResponse(chats=sessions)


@router.get("/sessions/{chat_id}")
async def get_chat_session(chat_id: str):
    """Get a specific chat session with full history."""
    session = _chat_sessions.get(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")
    return {"success": True, "session": session}


@router.delete("/sessions/{chat_id}")
async def delete_chat_session(chat_id: str):
    """Delete a chat session."""
    if chat_id not in _chat_sessions:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")
    del _chat_sessions[chat_id]
    return GenericResponse(message=f"Chat '{chat_id}' deleted successfully")


@router.post("/sessions/new")
async def create_new_chat(
    subject_code: Optional[str] = None,
    title: Optional[str] = None
):
    """Create a new empty chat session."""
    chat_id = str(uuid.uuid4())
    _chat_sessions[chat_id] = {
        "chat_id": chat_id,
        "title": title or "New Chat",
        "subject_code": subject_code,
        "messages": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    return {
        "success": True,
        "chat_id": chat_id,
        "message": "New chat session created"
    }


@router.post("/detect-switch")
async def detect_subject_switch(request: ChatMessageRequest):
    """
    Detect if a message implies a subject/unit switch.
    Returns the detected subject_code and unit_number if found.
    """
    switch = _detect_subject_switch(request.message)
    if switch:
        subject_info = _get_subject_info(switch.get("subject_code", ""))
        return {
            "success": True,
            "detected": True,
            "subject_code": switch.get("subject_code"),
            "unit_number": switch.get("unit_number"),
            "subject_name": subject_info.get("name", switch.get("subject_code", "")),
        }
    return {"success": True, "detected": False}

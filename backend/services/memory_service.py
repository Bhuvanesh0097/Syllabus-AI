"""
Memory Service — persistent long-term student progress tracking.
Uses JSON files for durable storage across server restarts.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("syllabus_ai")

# ── Persistent Storage Directory ──────────────────────────────
MEMORY_DIR = Path(__file__).parent.parent / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _get_student_path(student_id: str) -> Path:
    """Get the JSON file path for a student."""
    safe_id = student_id.replace(" ", "_").replace("/", "_")
    return MEMORY_DIR / f"{safe_id}.json"


def _load_student(student_id: str) -> Dict:
    """Load student data from disk, or create new profile."""
    path = _get_student_path(student_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load student {student_id}: {e}")

    # New student profile
    return {
        "student_id": student_id,
        "name": "",
        "department": "",
        "year": "",
        "semester": "",
        "section": "",
        "subjects": {},
        "total_interactions": 0,
        "last_active": None,
        "first_seen": datetime.utcnow().isoformat(),
        "sessions": [],
    }


def _save_student(student_id: str, data: Dict) -> None:
    """Persist student data to disk."""
    path = _get_student_path(student_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save student {student_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# Student Profile Management
# ═══════════════════════════════════════════════════════════════

async def save_student_profile(
    student_id: str,
    name: str,
    department: str = "",
    year: str = "",
    semester: str = "",
    section: str = "",
) -> Dict:
    """Save or update a student's profile info."""
    data = _load_student(student_id)
    data["name"] = name
    data["department"] = department or data.get("department", "")
    data["year"] = year or data.get("year", "")
    data["semester"] = semester or data.get("semester", "")
    data["section"] = section or data.get("section", "")
    _save_student(student_id, data)
    logger.info(f"Profile saved: {student_id} ({name})")
    return data


async def get_student_profile(student_id: str) -> Optional[Dict]:
    """Get a student's profile, or None if they don't exist."""
    path = _get_student_path(student_id)
    if not path.exists():
        return None
    return _load_student(student_id)


async def find_student_by_name(name: str) -> Optional[Dict]:
    """Find a student profile by name (case-insensitive)."""
    name_lower = name.strip().lower()
    for path in MEMORY_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("name", "").strip().lower() == name_lower:
                    return data
        except Exception:
            continue
    return None


# ═══════════════════════════════════════════════════════════════
# Interaction Recording
# ═══════════════════════════════════════════════════════════════

async def record_interaction(
    student_id: str,
    subject_code: str,
    unit_number: int,
    topic: str = "",
    interaction_type: str = "studied",
    confidence: Optional[float] = None
) -> None:
    """Record a student interaction and persist it."""
    now = datetime.utcnow().isoformat()
    data = _load_student(student_id)

    # Ensure subject structure exists
    if subject_code not in data["subjects"]:
        data["subjects"][subject_code] = {
            "units": {},
            "total_interactions": 0,
            "last_active": None,
        }

    subj = data["subjects"][subject_code]
    unit_key = str(unit_number)

    if unit_key not in subj["units"]:
        subj["units"][unit_key] = {
            "topics_studied": [],
            "questions_asked": [],
            "last_visited": None,
            "confidence": 0.0,
            "interaction_count": 0,
        }

    unit = subj["units"][unit_key]

    # Track topic
    if topic and topic not in unit["topics_studied"]:
        unit["topics_studied"].append(topic)
        # Keep only last 50 topics per unit
        if len(unit["topics_studied"]) > 50:
            unit["topics_studied"] = unit["topics_studied"][-50:]

    unit["last_visited"] = now
    unit["interaction_count"] += 1

    if confidence is not None:
        prev = unit["confidence"]
        count = unit["interaction_count"]
        unit["confidence"] = round(((prev * (count - 1)) + confidence) / count, 3)

    subj["total_interactions"] += 1
    subj["last_active"] = now

    data["total_interactions"] += 1
    data["last_active"] = now

    _save_student(student_id, data)

    logger.info(
        f"Memory recorded: student={student_id}, "
        f"{subject_code}/Unit {unit_number} — {interaction_type}"
    )


async def record_session(
    student_id: str,
    subject_code: str,
    unit_number: int,
    session_type: str = "study",
) -> None:
    """Record a study session start for the student."""
    now = datetime.utcnow().isoformat()
    data = _load_student(student_id)

    session_entry = {
        "subject_code": subject_code,
        "unit_number": unit_number,
        "type": session_type,
        "timestamp": now,
    }

    data["sessions"].append(session_entry)

    # Keep only last 100 sessions
    if len(data["sessions"]) > 100:
        data["sessions"] = data["sessions"][-100:]

    data["last_active"] = now
    _save_student(student_id, data)


# ═══════════════════════════════════════════════════════════════
# Progress & Welcome Back
# ═══════════════════════════════════════════════════════════════

async def get_progress(student_id: str) -> Dict[str, Any]:
    """Get overall progress for a student."""
    data = _load_student(student_id)

    if data["total_interactions"] == 0:
        return {
            "total_interactions": 0,
            "subjects_progress": {},
            "topics_studied": [],
            "last_active": None,
        }

    subjects_progress = {}
    all_topics = []

    for subj_code, subj_data in data.get("subjects", {}).items():
        units_progress = {}
        for unit_num, unit_data in subj_data.get("units", {}).items():
            units_progress[unit_num] = {
                "topics_count": len(unit_data.get("topics_studied", [])),
                "confidence": round(unit_data.get("confidence", 0), 2),
                "interactions": unit_data.get("interaction_count", 0),
                "last_visited": unit_data.get("last_visited"),
            }
            all_topics.extend(unit_data.get("topics_studied", []))

        subjects_progress[subj_code] = {
            "units": units_progress,
            "total_interactions": subj_data.get("total_interactions", 0),
            "last_active": subj_data.get("last_active"),
        }

    return {
        "total_interactions": data["total_interactions"],
        "subjects_progress": subjects_progress,
        "topics_studied": all_topics[-20:],  # Last 20
        "last_active": data["last_active"],
    }


async def get_study_summary(
    student_id: str,
    subject_code: str
) -> Dict[str, Any]:
    """Get study summary for a specific subject."""
    data = _load_student(student_id)

    if subject_code not in data.get("subjects", {}):
        return {
            "subject_code": subject_code,
            "studied": False,
            "units_covered": [],
            "topics_count": 0,
        }

    subj_data = data["subjects"][subject_code]
    units_covered = []
    total_topics = 0

    for unit_num, unit_data in subj_data.get("units", {}).items():
        if unit_data.get("interaction_count", 0) > 0:
            units_covered.append(int(unit_num))
            total_topics += len(unit_data.get("topics_studied", []))

    return {
        "subject_code": subject_code,
        "studied": len(units_covered) > 0,
        "units_covered": sorted(units_covered),
        "topics_count": total_topics,
        "total_interactions": subj_data.get("total_interactions", 0),
        "last_active": subj_data.get("last_active"),
    }


async def get_welcome_back_data(student_id: str) -> Optional[Dict]:
    """
    Generate welcome-back context for a returning student.
    Returns None if the student is new (no previous sessions).
    """
    data = _load_student(student_id)

    if data["total_interactions"] == 0:
        return None

    # Find last session
    sessions = data.get("sessions", [])
    last_session = sessions[-1] if sessions else None

    # Find most studied subject
    most_studied_subject = None
    max_interactions = 0
    for subj_code, subj_data in data.get("subjects", {}).items():
        if subj_data.get("total_interactions", 0) > max_interactions:
            max_interactions = subj_data["total_interactions"]
            most_studied_subject = subj_code

    # Suggest next unit
    suggested_unit = None
    if last_session:
        last_unit = last_session.get("unit_number", 1)
        suggested_unit = min(last_unit + 1, 5)

    # Count total unique topics
    total_topics = 0
    for subj_data in data.get("subjects", {}).values():
        for unit_data in subj_data.get("units", {}).values():
            total_topics += len(unit_data.get("topics_studied", []))

    return {
        "name": data.get("name", "Student"),
        "total_interactions": data["total_interactions"],
        "total_topics": total_topics,
        "last_active": data.get("last_active"),
        "last_session": last_session,
        "most_studied_subject": most_studied_subject,
        "suggested_unit": suggested_unit,
        "subjects_studied": list(data.get("subjects", {}).keys()),
    }

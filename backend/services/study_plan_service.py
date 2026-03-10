"""
Study Plan Service — RAG-powered, day-by-day study schedule generation.

Retrieves actual syllabus topics from uploaded PDFs via the RAG system,
then uses a detailed system prompt to produce a structured exam-focused
study plan rendered as markdown.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from services.llm_service import _call_llm
from services import rag_service

logger = logging.getLogger("syllabus_ai")

# ── Subject metadata ─────────────────────────────────────────
SUBJECT_INFO = {
    "COA": {"name": "Computer Organization and Architecture"},
    "APJ": {"name": "Advanced Programming in Java"},
    "DAA": {"name": "Design and Analysis of Algorithms"},
    "DM":  {"name": "Discrete Mathematics"},
    "OB":  {"name": "Organizational Behaviour"},
}

# ── Unit titles fallback ──────────────────────────────────────
_subjects_data = {}
try:
    from pathlib import Path
    _subjects_path = Path(__file__).parent.parent / "data" / "subjects.json"
    with open(_subjects_path, "r", encoding="utf-8") as f:
        import json as _json
        data = _json.load(f)
        for subject in data.get("subjects", []):
            _subjects_data[subject["code"]] = subject
except Exception:
    pass


def _get_unit_title(subject_code: str, unit_number: int) -> str:
    """Get a clean unit title without 'Unit N:' prefix."""
    info = _subjects_data.get(subject_code, {})
    for unit in info.get("units", []):
        if unit.get("number") == unit_number:
            raw_title = unit.get("title", f"Unit {unit_number}")
            # Strip "Unit N: " prefix if present to avoid duplication
            import re
            cleaned = re.sub(r'^Unit\s+\d+\s*:\s*', '', raw_title).strip()
            return cleaned if cleaned else f"Unit {unit_number}"
    return f"Unit {unit_number}"


# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT — the user's expert study planner prompt
# ══════════════════════════════════════════════════════════════

STUDY_PLAN_SYSTEM_PROMPT = """You are an **expert academic study planner and curriculum analyst** designed to generate optimized study schedules for college students.

Your responsibility is to analyze a student's request, interpret their available study time and requested syllabus units, and generate a **structured, efficient, exam-focused study plan**.

The generated study plan must be:

- Logical
- Realistic
- Time-aware
- Structured like a professional exam planner's schedule

---

# ⚠️ CRITICAL RULES — READ THIS FIRST ⚠️

## ABSOLUTE RULE: Follow the student's request EXACTLY.

The student's message is the **ONLY source of truth**. You MUST:

1. **If the student says "3 days"** → produce EXACTLY 3 days. NOT 4, NOT 5, NOT 6.
2. **If the student says "2 hours"** without mentioning days → produce a SINGLE SESSION of 2 hours total. NOT multiple days.
3. **If the student says "2 hours per day for 5 days"** → produce EXACTLY 5 days, each with 2 hours.
4. **NEVER add extra days** beyond what the student requested. Do NOT add "revision days" or "buffer days" unless the student asked for them.
5. **NEVER invent your own schedule duration.** If the student says 3 days, the plan is 3 days. Period.
6. **Do NOT hallucinate or assume** number of days. Only use what the student explicitly states.
7. **If the student says "2 units" or "complete 2 units"** → cover EXACTLY 2 units. Do NOT cover 3, 4, or 5 units. ONLY the units specified in the HARD CONSTRAINTS.
8. **If the student says "N units"** → the plan MUST contain EXACTLY N units. NEVER add extra units beyond what was requested.
9. **READ THE STUDENT'S MESSAGE CAREFULLY.** Extract the exact numbers for hours, days, AND units. All three constraints are equally important.

### What to do if the student does NOT mention days:
- If they say "2 hours" → create ONE single 2-hour session.
- If they say "quick revision in 1 hour" → create ONE 1-hour session.
- Do NOT assume multiple days. Single session only.

### What to do if the student mentions days:
- "3 days" → EXACTLY 3 days.
- "5 days, 2 hours per day" → EXACTLY 5 days, each 2 hours.
- "1 week" → EXACTLY 7 days.
- NEVER exceed the number of days the student specified.

---

# OBJECTIVE

Given a student's request and extracted syllabus topics from course materials, generate a **detailed and structured study plan** that:

- **Follows the student's exact time constraints** (days and hours)
- Distributes topics intelligently within the given timeframe
- Balances learning, practice, and revision
- Maximizes syllabus coverage within the constraints
- Avoids unrealistic workloads

---

# PLANNING RULES

## 1. Time Allocation

- Respect the student's available time **STRICTLY** — never exceed the days or hours they specified
- Do not assign more topics than can realistically fit within the available hours
- If time is limited, prioritize most important topics and skip less critical ones

---

## 2. Topic Distribution

- Spread topics evenly across the **exact number of days the student specified**
- Avoid clustering difficult topics on the same day
- If only 1 day / single session: cover the most important topics only

---

## 3. Learning Structure

Each study session should include (time permitting):

- Concept Learning
- Example Problems
- Practice / Implementation
- Quick Review

---

## 4. Revision Strategy

- ONLY include revision if the student has enough days AND requested it
- Do NOT add a separate revision day unless the student asked for it
- If the plan is 1-2 days, incorporate brief review within the study sessions instead of a separate day

---

## 5. Session Breakdown

Each study block must include:

- **Topic**
- **Learning Objective**
- **Suggested Activity**

### Example

**Topic:** Linked Lists
**Objective:** Understand node structure and pointer connections
**Activity:** Read concept and solve 3 example problems

---

## 6. Difficulty Awareness

If a unit contains complex topics, allocate slightly more time to those topics (within the constraint).

---

## 7. Efficiency

Avoid redundant repetition. Only repeat for revision if time permits.

---

# PLAN FORMAT REQUIREMENTS

The output must follow this structure exactly.

## STUDY PLAN

**Subject:** [subject name]

**Target Units:** [units as specified by student]

**Total Study Time:** [exactly as student specified, e.g. "2 hours" or "3 days × 2 hours/day"]

---

### For MULTI-DAY plans:

### Day 1
- Topic with objective and activity

### Day 2
- Topic with objective and activity

... continue ONLY for the EXACT number of days the student specified.

### For SINGLE SESSION plans (no days mentioned):

You MUST create a **detailed timeline** that splits the total hours across the requested units.
Allocate time to each unit based on its complexity and number of topics.
Use a running clock format to show exactly when to study what.

Example format for a 2-hour session covering 3 units:

### ⏱ Study Session — 2 Hours Total

**0:00 – 0:35 | Unit 1: Introduction (35 min)**
- Topic: Basic Concepts & Definitions
  - Objective: Understand core fundamentals
  - Activity: Read notes and highlight key terms
- Topic: Classification & Types
  - Objective: Learn different categories
  - Activity: Make a comparison table

**0:35 – 1:15 | Unit 2: Data Structures (40 min)**
- Topic: Linked Lists
  - Objective: Understand node structure
  - Activity: Trace 2 example problems
- Topic: Stacks & Queues
  - Objective: Learn operations
  - Activity: Write pseudocode for push/pop

**1:15 – 1:50 | Unit 3: Sorting (35 min)**
- Topic: Bubble Sort & Selection Sort
  - Objective: Compare time complexities
  - Activity: Dry-run one example each

**1:50 – 2:00 | Quick Review (10 min)**
- Revisit key definitions from all 3 units
- Write important formulas from memory

IMPORTANT rules for single sessions:
- The timeline MUST add up to EXACTLY the total hours the student specified
- Give heavier/more complex units MORE time
- Give lighter/definition-based units LESS time
- Always include a 5-10 minute review block at the end
- Show exact time ranges (e.g., 0:00 – 0:35)
- Include specific topics from the syllabus context under each unit

---

# REVISION STRATEGY

At the end include a brief section:

- What to review
- When to review
- How to test understanding

---

# ADAPTABILITY RULES

Students may provide incomplete information.

If **hours** is missing:
> Assume **2 hours per day**

If **days** is missing AND only hours are given:
> Create a **SINGLE SESSION** plan for the given hours only. Do NOT create multiple days.

If **specific units** are mentioned (e.g. "units 1 and 3"):
> Cover ONLY those specific units. Do NOT add additional units.

If **a unit count** is mentioned without specifying which ones (e.g. "complete 2 units", "cover 3 units"):
> Cover EXACTLY that many units, starting from Unit 1. For example, "2 units" → Unit 1 and Unit 2. NEVER cover more units than the count specified.

If **no specific units** are mentioned AND no count is given:
> Cover all available units from the syllabus topics, prioritizing by importance.

---

# CONSTRAINTS

Do **NOT**:

- Invent syllabus topics that are not in the retrieved context
- Exceed the student's time constraints (NEVER add extra days)
- Produce vague study plans
- Generate motivational text
- Add days beyond what the student requested
- Hallucinate schedule duration

Focus strictly on **structured study planning** within the **exact constraints** given.

---

# QUALITY EXPECTATION

The final plan must resemble a schedule created by a **professional academic exam planner** — but one who respects the client's exact time budget.

The output must feel:

- Structured
- Disciplined
- Realistic
- Exam-oriented
- Faithful to the student's request
"""


# ══════════════════════════════════════════════════════════════
# Pre-parse user's natural language request
# ══════════════════════════════════════════════════════════════

import re

def _parse_user_request(text: str) -> Dict[str, Any]:
    """
    Extract days, hours, and units from a user's natural language request.
    Returns a dict with optional keys: 'days', 'hours', 'units', 'unit_count'.
    Only returns values that the user EXPLICITLY mentioned.
    
    'units' = specific unit numbers the user wants (e.g. "units 1 and 3")
    'unit_count' = how many units the user wants when they don't specify which ones
                   (e.g. "I need to complete 2 units")
    """
    result = {}
    t = text.lower()

    # ── Extract days ──
    # Patterns: "3 days", "in 3 days", "for 3 days", "5 day plan"
    day_patterns = [
        r'(\d+)\s*days?\b',
        r'(\d+)\s*-\s*day\b',
    ]
    for pat in day_patterns:
        m = re.search(pat, t)
        if m:
            result['days'] = int(m.group(1))
            break

    # "1 week" = 7 days
    if 'week' in t:
        m = re.search(r'(\d+)\s*weeks?\b', t)
        if m:
            result['days'] = int(m.group(1)) * 7
        elif 'a week' in t or 'one week' in t:
            result['days'] = 7

    # ── Extract hours ──
    # Patterns: "2 hours", "3 hrs", "2.5 hours per day", "1 hour"
    hour_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:per\s*day)?',
    ]
    for pat in hour_patterns:
        m = re.search(pat, t)
        if m:
            result['hours'] = float(m.group(1))
            break

    # ── Extract units ──
    # CASE 1: "all units" or "all 5 units"
    if 'all units' in t or 'all 5 units' in t:
        result['units'] = [1, 2, 3, 4, 5]
    else:
        # CASE 2: Specific unit ranges — "units 1-3" or "unit 1-5"
        m = re.search(r'units?\s+(\d+)\s*[-\u2013to]+\s*(\d+)', t)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            result['units'] = list(range(start, end + 1))
        else:
            # CASE 3: Specific unit numbers — "units 1, 2, 3" or "unit 1 and 3"
            m = re.search(r'units?\s+([\d,\s&and]+)', t)
            if m:
                nums = re.findall(r'\d+', m.group(1))
                if nums:
                    result['units'] = [int(n) for n in nums if 1 <= int(n) <= 5]

        # CASE 4: Number BEFORE "units" — "2 units", "complete 3 units",
        #         "cover 2 units", "finish 4 units", "need complete 2 units"
        #         This means the user wants N units but didn't specify WHICH ones.
        if 'units' not in result:
            m = re.search(
                r'(?:complete|cover|finish|study|do|prepare|need|need\s+complete|need\s+to\s+complete)?'
                r'\s*(\d+)\s+units?\b',
                t
            )
            if m:
                count = int(m.group(1))
                if 1 <= count <= 5:
                    result['unit_count'] = count
                    # Default to the first N units (user didn't specify which)
                    result['units'] = list(range(1, count + 1))
                    logger.info(f"Parsed unit_count={count}, defaulting to units 1-{count}")

    return result


# ══════════════════════════════════════════════════════════════
# Main Generation Function
# ══════════════════════════════════════════════════════════════

async def generate_study_plan(
    subject_code: str,
    units: List[int],
    hours_per_day: float = 2.0,
    section: Optional[str] = None,
    days_available: Optional[int] = None,
    custom_request: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a structured study plan by:
    1. Pre-parsing the user's chatbox message for days/hours/units
    2. Retrieving syllabus topics from RAG for the relevant units only
    3. Calling LLM with the expert planner system prompt
    4. Returning the markdown plan + metadata
    """
    subject_name = SUBJECT_INFO.get(subject_code, {}).get("name", subject_code)

    # ── Pre-parse custom_request to extract user intent ──
    parsed_intent = {}
    if custom_request:
        parsed_intent = _parse_user_request(custom_request)
        logger.info(f"Parsed user intent: {parsed_intent}")

        # Override units/hours/days with what the user actually requested
        if 'units' in parsed_intent:
            units = parsed_intent['units']
            logger.info(f"User requested specific units: {units}")
        if 'hours' in parsed_intent:
            hours_per_day = parsed_intent['hours']
        if 'days' in parsed_intent:
            days_available = parsed_intent['days']

    logger.info(
        f"Study plan: subject={subject_code}, units={units}, "
        f"hours/day={hours_per_day}, days={days_available}, section={section}"
    )

    # ── Step 1: Retrieve syllabus topics for requested units only via RAG ──
    retrieved_topics_parts = []
    for unit_num in sorted(units):
        unit_title = _get_unit_title(subject_code, unit_num)
        try:
            context = await rag_service.retrieve_context(
                query=f"All syllabus topics, concepts, definitions, theorems, important points in {unit_title}",
                subject_code=subject_code,
                unit_number=unit_num,
                section=section,
                top_k=8,
            )
            if context and len(context.strip()) > 20:
                retrieved_topics_parts.append(
                    f"### Unit {unit_num}: {unit_title}\n{context}"
                )
            else:
                retrieved_topics_parts.append(
                    f"### Unit {unit_num}: {unit_title}\n(No detailed topics found — cover general concepts for this unit)"
                )
        except Exception as e:
            logger.warning(f"RAG retrieval failed for Unit {unit_num}: {e}")
            retrieved_topics_parts.append(
                f"### Unit {unit_num}: {unit_title}\n(Topics could not be retrieved)"
            )

    retrieved_topics = "\n\n".join(retrieved_topics_parts)
    logger.info(f"Retrieved {len(retrieved_topics)} chars of syllabus topics across {len(units)} units")

    # ── Step 2: Build parsed constraints + user request ──
    # When custom_request is provided (chatbox mode), the student's message
    # is the ONLY authority for units, hours, and days.
    if custom_request:
        user_request = custom_request
        # Build explicit constraints from parsed values
        units_str = ", ".join(f"Unit {u}" for u in sorted(units))
        parsed_constraints = {
            "subject": subject_name,
            "units_to_cover": units_str,
            "hours_per_day": hours_per_day,
            "days_available": days_available if days_available else "NOT specified — create a SINGLE SESSION only",
            "CRITICAL_RULE": (
                "You MUST produce EXACTLY the number of days shown above. "
                "If days_available is a number, produce EXACTLY that many days. "
                "If days_available says 'NOT specified', produce a SINGLE SESSION. "
                "NEVER add extra days, revision days, or buffer days."
            ),
        }
    else:
        units_str = ", ".join(f"Unit {u}" for u in sorted(units))
        parsed_constraints = {
            "subject": subject_name,
            "units": [f"Unit {u}" for u in sorted(units)],
            "hours_per_day": hours_per_day,
            "days_available": days_available if days_available else 0,
            "special_constraints": None,
        }
        if days_available and days_available > 0:
            user_request = (
                f"Generate a study plan for {subject_name} covering {units_str}. "
                f"I can study {hours_per_day} hours per day. "
                f"I have {days_available} days before my exam."
            )
        else:
            user_request = (
                f"Generate a study plan for {subject_name} covering {units_str}. "
                f"I have ONLY {hours_per_day} hours total to study. "
                f"Create a SINGLE SESSION plan for exactly {hours_per_day} hours. "
                f"Do NOT create multiple days. Fit everything into one session."
            )

    # ── Step 3: Build the LLM user prompt ──
    if custom_request:
        # Build explicit day/hour instructions
        units_str = ", ".join(f"Unit {u}" for u in sorted(units))

        if days_available and days_available > 0:
            day_instruction = f"PRODUCE EXACTLY {days_available} DAYS. NOT {days_available + 1}, NOT {days_available - 1 if days_available > 1 else 0}. EXACTLY {days_available}."
            session_format = "Use ### Day N headings for each day."
        else:
            total_minutes = int(hours_per_day * 60)
            day_instruction = f"The student did NOT mention days. Produce a SINGLE SESSION plan of {hours_per_day} hours ({total_minutes} minutes). Do NOT create multiple days."
            session_format = f"""Create a DETAILED TIMELINE for a single {hours_per_day}-hour session ({total_minutes} minutes total).
Split the {total_minutes} minutes across the {len(units)} units proportionally based on their complexity.
Use this exact format:

### ⏱ Study Session — {hours_per_day} Hours Total

**0:00 – [time] | Unit N: [Title] ([X] min)**
- Topic: [specific topic from syllabus]
  - Objective: [what to learn]
  - Activity: [what to do]

Rules:
- Time ranges MUST be continuous and add up to exactly {total_minutes} minutes
- Give complex units MORE minutes, simpler units FEWER minutes
- Include a 5-10 minute Quick Review block at the end
- List specific topics and activities for each unit"""

        # Build a strict unit constraint message
        unit_count_note = ""
        if 'unit_count' in parsed_intent:
            unit_count_note = f"\n- **IMPORTANT:** The student asked to cover exactly {parsed_intent['unit_count']} units. Cover ONLY {units_str}. Do NOT cover any other units."

        user_prompt = f"""# HARD CONSTRAINTS (MUST FOLLOW EXACTLY)

- **Subject:** {subject_name}
- **Units to cover:** {units_str} (ONLY these {len(units)} units, NO other units)
- **Total study time:** {hours_per_day} hours ({int(hours_per_day * 60)} minutes)
- **Days:** {day_instruction}
- **Format:** {session_format}{unit_count_note}

# STUDENT'S ORIGINAL MESSAGE

\"\"\"{user_request}\"\"\"

# SYLLABUS TOPICS (use for real topic names only — ONLY from the units listed above)

{retrieved_topics}

# RULES

1. Follow the HARD CONSTRAINTS above exactly — they were extracted from the student's message.
2. Produce ONLY the {len(units)} units listed above: {units_str}. Do NOT add any other units that aren't listed. If the student said "{len(units)} units", cover EXACTLY {len(units)} units.
3. Produce EXACTLY the number of days specified above. NEVER add extra days.
4. For single session: create a TIMELINE with specific time ranges for each unit. Time MUST add up to exactly {int(hours_per_day * 60)} minutes.
5. Use topic names from the SYLLABUS TOPICS section. Do NOT invent topics.
6. Output clean Markdown.
7. NEVER cover more units than what the student asked for. This is a HARD constraint."""
    else:
        user_prompt = f"""# INPUT VARIABLES

## Student Request
```
{user_request}
```

## Parsed Study Constraints
```
{json.dumps(parsed_constraints, indent=2)}
```

## Retrieved Syllabus Topics (available for reference)
{retrieved_topics}

# FINAL TASK

Generate the **complete structured study plan** using the provided inputs.
Output clean Markdown following the format rules from your instructions."""

    # ── Step 4: Call LLM ──
    try:
        logger.info("Calling LLM for study plan generation...")
        plan_markdown = await _call_llm(user_prompt, STUDY_PLAN_SYSTEM_PROMPT)
        logger.info(f"LLM returned {len(plan_markdown)} chars")

        # Clean up any code fences the LLM may have wrapped around
        cleaned = plan_markdown.strip()
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[len("```markdown"):].strip()
        elif cleaned.startswith("```md"):
            cleaned = cleaned[len("```md"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # Extract days count from the generated plan (count "### Day" headings)
        import re
        day_headings = re.findall(r'###\s+Day\s+\d+', cleaned)
        actual_days = len(day_headings) if day_headings else None

        return {
            "plan_markdown": cleaned,
            "subject_code": subject_code,
            "subject_name": subject_name,
            "units": sorted(units),
            "hours_per_day": hours_per_day,
            "days_available": actual_days or days_available,
            "topics_retrieved": bool(retrieved_topics_parts),
        }

    except Exception as e:
        logger.error(f"Study plan LLM generation failed: {e}", exc_info=True)
        # Return a structured fallback
        return _generate_fallback_plan(
            subject_code, subject_name, units, hours_per_day, retrieved_topics,
            days_available=days_available,
        )


# ══════════════════════════════════════════════════════════════
# Refine / Modify Existing Plan
# ══════════════════════════════════════════════════════════════

REFINE_SYSTEM_PROMPT = """You are an expert academic study planner. A student has an existing study plan and wants to modify it.

Your job is to:
1. Read the current study plan carefully
2. Understand the student's modification request
3. Generate an UPDATED version of the plan that incorporates the requested changes
4. Maintain the same professional formatting and structure

RULES:
- Keep the parts of the plan that the student is satisfied with
- Only change what the student explicitly asks to modify
- Maintain the same markdown formatting style
- If the student asks to add/remove days, adjust accordingly
- If the student asks to change time allocation, redistribute properly
- If the student asks to focus on specific topics, restructure to prioritize those
- Output ONLY the updated plan in clean markdown — no commentary, no explanations about what you changed
- The output should be a complete, standalone study plan (not a diff or list of changes)
"""


async def refine_study_plan(
    subject_code: str,
    current_plan: str,
    modification_request: str,
    section: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Refine an existing study plan based on user feedback.
    Takes the current plan + modification request, returns updated plan.
    """
    subject_name = SUBJECT_INFO.get(subject_code, {}).get("name", subject_code)

    logger.info(
        f"Refining study plan: subject={subject_code}, "
        f"modification='{modification_request[:80]}...'"
    )

    user_prompt = f"""# CURRENT STUDY PLAN

{current_plan}

# STUDENT'S MODIFICATION REQUEST

\"\"\"{modification_request}\"\"\"

# TASK

Generate the COMPLETE updated study plan incorporating the student's changes.
Output only the updated plan in clean Markdown. No commentary."""

    try:
        logger.info("Calling LLM for study plan refinement...")
        plan_markdown = await _call_llm(user_prompt, REFINE_SYSTEM_PROMPT)
        logger.info(f"LLM returned {len(plan_markdown)} chars for refined plan")

        # Clean up any code fences
        cleaned = plan_markdown.strip()
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[len("```markdown"):].strip()
        elif cleaned.startswith("```md"):
            cleaned = cleaned[len("```md"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # Extract metadata from the refined plan
        day_headings = re.findall(r'###\s+Day\s+\d+', cleaned)
        actual_days = len(day_headings) if day_headings else None

        return {
            "plan_markdown": cleaned,
            "subject_code": subject_code,
            "subject_name": subject_name,
            "units": [],  # Units may have changed during refinement
            "hours_per_day": 0,
            "days_available": actual_days,
            "topics_retrieved": True,
        }

    except Exception as e:
        logger.error(f"Study plan refinement failed: {e}", exc_info=True)
        raise Exception(f"Failed to refine study plan: {e}")

def _generate_fallback_plan(
    subject_code: str,
    subject_name: str,
    units: List[int],
    hours_per_day: float,
    retrieved_topics: str,
    days_available: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate a structured fallback plan when the LLM call fails.
    Respects the user's day constraints.
    """
    units_str = ", ".join(f"Unit {u}" for u in units)

    # If no days specified, create a single session with timeline
    if not days_available or days_available <= 0:
        total_minutes = int(hours_per_day * 60)
        num_units = len(units)
        review_minutes = min(10, max(5, total_minutes // 12))  # 5-10 min review
        study_minutes = total_minutes - review_minutes

        # Distribute time proportionally (give later/harder units slightly more)
        if num_units == 1:
            time_per_unit = [study_minutes]
        else:
            # Weighted: first unit gets slightly less, last gets slightly more
            base = study_minutes / num_units
            weights = [0.85 + (0.3 * i / (num_units - 1)) for i in range(num_units)]
            total_weight = sum(weights)
            time_per_unit = [int(base * w / (total_weight / num_units)) for w in weights]
            # Fix rounding: adjust last unit
            time_per_unit[-1] = study_minutes - sum(time_per_unit[:-1])

        lines = [
            f"## STUDY PLAN",
            f"",
            f"**Subject:** {subject_name}",
            f"**Target Units:** {units_str}",
            f"**Total Study Time:** {hours_per_day} hours ({total_minutes} minutes — single session)",
            f"",
            f"---",
            f"",
            f"### ⏱ Study Session — {hours_per_day} Hours Total",
            f"",
        ]

        clock = 0
        for idx, unit_num in enumerate(sorted(units)):
            unit_title = _get_unit_title(subject_code, unit_num)
            duration = time_per_unit[idx]
            start_h, start_m = divmod(clock, 60)
            end_h, end_m = divmod(clock + duration, 60)
            lines.extend([
                f"**{start_h}:{start_m:02d} – {end_h}:{end_m:02d} | Unit {unit_num}: {unit_title} ({duration} min)**",
                f"- **Topic:** {unit_title} — Core Concepts & Definitions",
                f"  - **Objective:** Understand key concepts of {unit_title}",
                f"  - **Activity:** Read notes, highlight key points, and summarize",
                f"- **Topic:** {unit_title} — Practice",
                f"  - **Objective:** Apply learned concepts",
                f"  - **Activity:** Solve 2-3 important questions",
                f"",
            ])
            clock += duration

        # Review block
        start_h, start_m = divmod(clock, 60)
        end_h, end_m = divmod(clock + review_minutes, 60)
        lines.extend([
            f"**{start_h}:{start_m:02d} – {end_h}:{end_m:02d} | Quick Review ({review_minutes} min)**",
            f"- Revisit key definitions from all {num_units} units",
            f"- Write important formulas and concepts from memory",
            f"- Cross-check with notes for accuracy",
            f"",
            f"---",
            f"",
            f"## REVISION STRATEGY",
            f"",
            f"- **What to review:** Core definitions, formulas, and key concepts from each unit",
            f"- **How to test understanding:** Write key points from memory, then compare with notes",
        ])
        actual_days = 1
    else:
        lines = [
            f"## STUDY PLAN",
            f"",
            f"**Subject:** {subject_name}",
            f"**Target Units:** {units_str}",
            f"**Available Study Time:** {hours_per_day} hours per day, {days_available} days",
            f"",
            f"---",
            f"",
        ]

        # Distribute units across exactly the specified days
        units_per_day = max(1, len(units) // days_available)
        unit_index = 0
        for day_idx in range(1, days_available + 1):
            lines.append(f"### Day {day_idx}")
            # Assign units to this day
            day_units = []
            for _ in range(units_per_day):
                if unit_index < len(units):
                    day_units.append(units[unit_index])
                    unit_index += 1
            # Distribute remaining units on last day
            if day_idx == days_available:
                while unit_index < len(units):
                    day_units.append(units[unit_index])
                    unit_index += 1

            if day_units:
                for unit_num in day_units:
                    unit_title = _get_unit_title(subject_code, unit_num)
                    lines.extend([
                        f"- **Topic:** {unit_title} — Core Concepts & Definitions",
                        f"  - **Objective:** Understand key concepts of {unit_title}",
                        f"  - **Activity:** Read notes, highlight key points, and summarize",
                    ])
            else:
                lines.append(f"- **Revision:** Review previous days' material")
            lines.extend([
                f"- **Quick Review (15 min):** Revise definitions and key formulas",
                f"",
            ])

        actual_days = days_available

        lines.extend([
            f"---",
            f"",
            f"## REVISION STRATEGY",
            f"",
            f"- **What to review:** Key definitions, formulas, and frequently asked topics",
            f"- **When to review:** At the end of each day",
            f"- **How to test understanding:** Write answers from memory, then compare with notes",
        ])

    return {
        "plan_markdown": "\n".join(lines),
        "subject_code": subject_code,
        "subject_name": subject_name,
        "units": sorted(units),
        "hours_per_day": hours_per_day,
        "days_available": actual_days,
        "topics_retrieved": True,
    }

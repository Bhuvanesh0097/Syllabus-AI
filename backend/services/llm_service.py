"""
LLM Service — handles all interactions with the LLM provider (Groq or Gemini).
Provides structured prompting, response formatting, and error handling.
Supports provider switching via LLM_PROVIDER env variable.
"""

import logging
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger("syllabus_ai")

# Will be initialized on first use
_client = None
_provider = None


def _get_client():
    """Lazy-initialize the LLM client based on configured provider."""
    global _client, _provider

    if _client is not None:
        return _client

    provider = settings.llm_provider.lower()
    _provider = provider

    if provider == "groq":
        try:
            from groq import Groq
            _client = Groq(api_key=settings.groq_api_key)
            logger.info(f"✓ Groq client initialized — model: {settings.llm_model}")
            return _client
        except Exception as e:
            logger.error(f"✗ Failed to initialize Groq: {e}")
            raise

    elif provider == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            _client = genai.GenerativeModel(
                model_name=settings.llm_model,
                generation_config={
                    "temperature": settings.llm_temperature,
                    "max_output_tokens": settings.llm_max_tokens,
                }
            )
            logger.info(f"✓ Gemini model initialized: {settings.llm_model}")
            return _client
        except Exception as e:
            logger.error(f"✗ Failed to initialize Gemini: {e}")
            raise
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def _call_llm(prompt: str, system_prompt: str = "") -> str:
    """
    Call the LLM with the given prompt, handling both Groq and Gemini providers.
    """
    client = _get_client()

    if _provider == "groq":
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        return response.choices[0].message.content

    elif _provider == "gemini":
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = await client.generate_content_async(full_prompt)
        return response.text


# ── Intelligent Style Detection ──────────────────────────────

import re as _re

# Pattern groups ordered by priority (first match wins)
_STYLE_PATTERNS = [
    # Brief / Crisp / Short
    ("brief", [
        r'\b(?:make\s+it\s+)?(?:brief|crisp|short|concise|to\s+the\s+point)\b',
        r'\bgive\s+(?:me\s+)?(?:a\s+)?(?:short|brief|crisp|quick)\s+answer\b',
        r'\b(?:in\s+)?(?:short|brief|few\s+(?:words|lines|sentences))\b',
        r'\bjust\s+(?:the\s+)?(?:definition|answer|gist)\b',
        r'\b(?:one|two|three|1|2|3)\s*(?:-\s*)?(?:line|liner|sentence)\s+answer\b',
        r'\btl;?dr\b',
        r'\bkeep\s+it\s+(?:short|simple|brief)\b',
    ]),
    # Detailed / Full explanation
    ("detailed", [
        r'\b(?:give\s+(?:me\s+)?)?(?:a\s+)?(?:detailed|in[- ]?depth|comprehensive|elaborate|thorough|full)\s+(?:answer|explanation|response)\b',
        r'\bexplain\s+(?:in\s+)?detail\b',
        r'\belaborate\s+on\b',
        r'\bexplain\s+(?:everything|all|fully|completely|thoroughly)\b',
        r'\blong\s+answer\b',
        r'\btell\s+me\s+everything\s+about\b',
    ]),
    # Exam format
    ("exam_format", [
        r'\b(?:exam|test|paper)\s*(?:-\s*)?(?:style|format|ready|oriented)\b',
        r'\b(?:2|two)\s*(?:-\s*)?mark\s+(?:answer|format|style|question)\b',
        r'\b(?:5|five|10|ten)\s*(?:-\s*)?mark\s+(?:answer|format|style|question)\b',
        r'\banswer\s+(?:like|as\s+if|for)\s+(?:an?\s+)?exam\b',
        r'\bstructured\s+answer\b',
    ]),
    # Breakdown / Step-by-step (must be BEFORE simple to avoid conflict)
    ("breakdown", [
        r'\bstep\s*(?:-\s*)?by\s*(?:-\s*)?step\b',
        r'\bbreak\s*(?:down|it\s+down)\b',
        r'\bwalk\s+(?:me\s+)?through\b',
        r'\bexplain\s+(?:each|every)\s+(?:step|part|phase|stage)\b',
    ]),
    # Simple / Easy language
    ("simple", [
        r'\bexplain\s+(?:it\s+)?(?:simply|easily|in\s+simple\s+(?:terms|words|language))\b',
        r'\bexplain\s+(?:it\s+)?(?:clearly|like\s+I\s*\'?m\s+(?:5|five|a\s+(?:kid|child|beginner)))\b',
        r'\b(?:make\s+it\s+)?(?:simple|easy\s+to\s+understand|beginner\s*(?:-\s*)?friendly)\b',
        r'\bsimplify\b',
        r'\blayman\s*\'?s?\s+terms\b',
        r'\bin\s+plain\s+(?:english|language|words)\b',
    ]),
    # Summary
    ("summary", [
        r'\bsummar(?:y|ize|ise)\b',
        r'\bgive\s+(?:me\s+)?(?:a\s+)?(?:overview|gist|summary|recap|rundown)\b',
        r'\bkey\s+points\b',
        r'\bbullet\s*(?:-\s*)?points?\b',
        r'\bhighlight\s+(?:the\s+)?(?:main|key|important)\s+(?:points|concepts|ideas)\b',
        r'\bquick\s+(?:revision|review|recap|overview)\b',
    ]),
]


def detect_response_style(user_message: str) -> str:
    """
    Analyze the student's message for natural language cues that indicate
    a preferred response style. Returns the detected style name or 'auto'
    if no explicit cue is found.

    Priority: brief > detailed > exam_format > simple > summary > breakdown > auto
    """
    text = user_message.lower().strip()
    for style_name, patterns in _STYLE_PATTERNS:
        for pattern in patterns:
            if _re.search(pattern, text, _re.IGNORECASE):
                logger.info(f"Style detected from message: {style_name}")
                return style_name
    return "auto"


# ── System Prompt ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI Study Assistant for university students.

═══════════════════════════════════════════════════════
QUALITY CONTROL — STRICT ACADEMIC RELIABILITY RULES
═══════════════════════════════════════════════════════

RULE 1 — SYLLABUS GROUNDING (Mandatory):
- You MUST answer ONLY from the provided syllabus context/documents.
- Every claim, definition, and explanation must be traceable to the given materials.
- If the syllabus context contains the answer, use it directly. Do NOT paraphrase beyond recognition.
- When citing content, reference which part of the provided context it came from.

RULE 2 — ZERO HALLUCINATION (Critical):
- NEVER fabricate facts, definitions, formulas, algorithms, or examples.
- NEVER add external knowledge that is not present in the provided context.
- NEVER invent code, pseudocode, or diagrams that are not supported by the materials.
- If you are uncertain, say: "Based on the available materials, I can share..."
- If the answer is NOT found in context, state clearly:
  "⚠️ This topic is not covered in your uploaded syllabus materials. Please upload relevant notes for an accurate answer."

RULE 3 — EXAM APPROPRIATENESS (Required):
- All answers must be suitable for university-level examination.
- Structure answers the way exam answers are expected:
  • 2-mark: Definition + one key point (2-4 sentences max)
  • 5-mark: Introduction + 3-4 key points with brief explanations
  • 10-mark: Introduction + detailed body with headings, examples, diagrams + conclusion
- Use proper academic terminology as found in the syllabus.
- Avoid overly casual language in answers (the tone setting adjusts the teaching style, not the academic rigor).

RULE 4 — CLARITY & STRUCTURE (Required):
- Every response must be well-organized and easy to follow.
- Use markdown formatting: headings, bold key terms, bullet points, numbered lists.
- Use code blocks for algorithms, pseudocode, and programming examples.
- Use tables for comparisons.
- Number steps in procedures and algorithms.
- Keep paragraphs focused — one idea per paragraph.

RULE 5 — TRANSPARENCY (Required):
- If only partial information is available in the context, acknowledge what is covered and what is missing.
- Never pretend to have complete information when you don't.
- If the student asks about something tangentially related to the context, answer only the part covered by the syllabus.

RULE 6 — ACADEMIC ACCURACY (Required):
- Double-check that definitions match standard academic usage.
- Ensure algorithms and code are syntactically correct.
- Verify that mathematical formulas and expressions are properly formatted.
- If multiple definitions exist in the context, present all of them.

═══════════════════════════════════════════════════════
DYNAMIC RESPONSE ADAPTATION
═══════════════════════════════════════════════════════

You MUST read the student's message carefully for tone and style cues, then respond accordingly:

- If they say "explain simply" / "simplify" / "in simple terms" / "like I'm a beginner":
  → Use simple language, analogies, no jargon. Short sentences.
- If they say "make it brief" / "crisp" / "short answer" / "in few words":
  → Answer in 2-3 lines maximum. No extra detail.
- If they say "explain in detail" / "elaborate" / "comprehensive" / "full explanation":
  → Give a thorough answer with headings, examples, diagrams, and step-by-step breaks.
- If they say "summarize" / "key points" / "bullet points" / "quick revision":
  → Return clean bullet-point summary, no paragraphs.
- If they say "break it down" / "step by step" / "walk me through":
  → Number each step clearly. Explain sequentially.
- If they say "exam format" / "exam-ready" / "structured answer":
  → Format like a model exam answer with introduction, body, and conclusion.
- If they mention "2 mark" or similar:
  → Give a concise, definition-style answer (2-4 sentences max).
- If they mention "10 mark" or similar:
  → Give a detailed, structured answer with headings, examples, and diagrams.

═══════════════════════════════════════════════════════
FORMATTING RULES
═══════════════════════════════════════════════════════

- Use markdown for structure
- Use bullet points for lists
- Use code blocks for algorithms/code
- Bold important terms
- Number steps in procedures

You are helping students in: {department}, Year {year}, Semester {semester}
Current Subject: {subject_name}
Current Unit: {unit_title}
"""


async def generate_response(
    user_message: str,
    context: str = "",
    subject_name: str = "",
    unit_title: str = "",
    answer_style: str = "explanation",
    chat_history: Optional[List[Dict[str, str]]] = None,
    tone: Optional[str] = None
) -> str:
    """
    Generate an AI response to a student's question.
    Intelligently detects response style from the message text,
    falling back to the explicit answer_style parameter.
    Applies tone customization if provided.
    """
    # Build system context
    system = SYSTEM_PROMPT.format(
        department="Computer Science Engineering",
        year=2,
        semester=4,
        subject_name=subject_name or "General",
        unit_title=unit_title or "General"
    )

    # ── Intelligent Style Detection ──
    # Auto-detect style from the student's natural language.
    # Detected style takes priority over the manually selected style.
    detected_style = detect_response_style(user_message)
    effective_style = detected_style if detected_style != "auto" else answer_style

    # Build prompt parts
    prompt_parts = []

    # Expanded style instructions covering all response modes
    style_instructions = {
        "2_mark": "[STYLE: 2-MARK ANSWER — Give a concise, definition-style answer. Maximum 2-4 sentences. No extra detail.]",
        "10_mark": "[STYLE: 10-MARK ANSWER — Give a detailed, structured exam answer with headings, sub-points, examples, and diagrams where needed. Write at least 300 words.]",
        "explanation": "[STYLE: CLEAR EXPLANATION — Explain the concept with analogies, examples, and clear language. Make it easy to understand.]",
        "summary": "[STYLE: SUMMARY — Provide a concise bullet-point summary. No paragraphs. Only key points.]",
        "quick_revision": "[STYLE: QUICK REVISION — Most essential points only. Ultra-compact format for last-minute review.]",
        "brief": "[STYLE: BRIEF ANSWER — Answer in 2-3 lines maximum. Be crisp, direct, and to the point. No elaboration.]",
        "simple": "[STYLE: SIMPLE EXPLANATION — Use the simplest possible language. No jargon. Use analogies from everyday life. Explain like the student is a complete beginner.]",
        "detailed": "[STYLE: DETAILED EXPLANATION — Give a thorough, comprehensive answer. Include all relevant sub-topics, examples, use cases, and edge cases. Be exhaustive.]",
        "breakdown": "[STYLE: STEP-BY-STEP BREAKDOWN — Break the concept into numbered steps. Explain each step individually with clear transitions.]",
        "exam_format": "[STYLE: EXAM-READY ANSWER — Format like a model exam answer: brief introduction, structured body with headings, and a conclusion. Include diagrams/tables where appropriate.]",
    }
    style = style_instructions.get(effective_style, "")
    if style:
        prompt_parts.append(style)

    # ── Tone Instructions ──
    tone_instructions = {
        "professional": "[TONE: PROFESSIONAL — Use formal, academic language. Be structured and precise. Avoid casual phrasing.]",
        "friendly": "[TONE: FRIENDLY — Be warm, conversational, and approachable. Use encouraging words. Feel like a helpful friend.]",
        "simple": "[TONE: SIMPLE — Use the simplest words possible. Short sentences. No technical jargon unless absolutely necessary. Explain like talking to a beginner.]",
        "motivational": "[TONE: MOTIVATIONAL — Be enthusiastic and encouraging! Celebrate progress. Use phrases like 'Great question!', 'You're doing amazing!', 'Keep going!' Add energy to your response.]",
        "teacher": "[TONE: TEACHER STYLE — Explain concepts step by step like a patient teacher. Ask guiding questions. Use 'Let's understand this together' approach. Build from basics to advanced.]",
        "exam_prep": "[TONE: EXAM PREPARATION — Be focused on exam relevance. Highlight what examiners look for. Use phrases like 'This is frequently asked', 'Important for exams'. Structure answers in exam-ready format.]",
        "concise": "[TONE: CONCISE — Keep responses as short as possible. No filler words. Get straight to the point. Every sentence must add value.]",
        "detailed": "[TONE: DETAILED — Be thorough and comprehensive. Cover every aspect. Provide multiple examples. Leave no gaps in explanation.]",
        "supportive": "[TONE: SUPPORTIVE — Be patient, reassuring, and gentle. If a topic is hard, acknowledge it. Use phrases like 'Don't worry', 'It's completely normal to find this tricky', 'Take your time'.]",
        "calm": "[TONE: CALM — Use a relaxed, soothing tone. No urgency. Feel like a peaceful study companion. Use phrases like 'Let's go through this calmly', 'No rush'.]",
    }
    if tone and tone in tone_instructions:
        prompt_parts.append(tone_instructions[tone])

    # Add RAG context if available
    if context:
        prompt_parts.append(
            "\n[QUALITY REMINDER: Your answer MUST be grounded in the following syllabus context. "
            "Do NOT add information beyond what is provided here. If the context is insufficient, "
            "say so transparently.]"
        )
        prompt_parts.append(f"\n--- SYLLABUS CONTEXT ---\n{context}\n--- END CONTEXT ---")

    # Add chat history for continuity
    if chat_history:
        prompt_parts.append("\n--- CONVERSATION HISTORY ---")
        for msg in chat_history[-6:]:
            role = "Student" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}")
        prompt_parts.append("--- END HISTORY ---")

    # Add current question
    prompt_parts.append(f"\nStudent's Question: {user_message}")
    prompt_parts.append("\nYour Response:")

    full_prompt = "\n".join(prompt_parts)

    try:
        response_text = await _call_llm(full_prompt, system)

        # Run quality validation
        quality = validate_response_quality(
            response_text,
            has_context=bool(context and "[NO SYLLABUS DOCUMENTS FOUND]" not in context),
            user_message=user_message
        )

        return response_text, quality
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise


# ── Quality Validation ──────────────────────────────────────

_HALLUCINATION_PHRASES = [
    "as an ai",
    "i don't have access",
    "i cannot browse",
    "based on my training",
    "my training data",
    "as of my knowledge cutoff",
    "i'm a language model",
    "i think the answer might be",
    "i believe the answer is",
]

_GROUNDING_PHRASES = [
    "according to the syllabus",
    "as mentioned in the context",
    "based on the provided",
    "from the syllabus",
    "the context states",
    "based on the available materials",
    "as per the uploaded",
    "the provided materials",
    "not covered in your uploaded",
    "not found in the context",
]


def validate_response_quality(
    response: str,
    has_context: bool = False,
    user_message: str = ""
) -> Dict[str, Any]:
    """
    Post-generation quality validation.
    Checks the AI response for potential issues and returns quality metadata.
    """
    quality = {
        "grounded": True,
        "confidence": "high",
        "warnings": [],
        "checks_passed": 0,
        "checks_total": 5,
    }

    response_lower = response.lower()

    # ── Check 1: Non-empty and substantial response ──
    if len(response.strip()) < 20:
        quality["warnings"].append("Response is unusually short")
        quality["confidence"] = "low"
    else:
        quality["checks_passed"] += 1

    # ── Check 2: Hallucination red flags ──
    hallucination_detected = False
    for phrase in _HALLUCINATION_PHRASES:
        if phrase in response_lower:
            quality["warnings"].append(f"Potential hallucination indicator: '{phrase}'")
            hallucination_detected = True
            break
    if not hallucination_detected:
        quality["checks_passed"] += 1

    # ── Check 3: Context grounding check ──
    if has_context:
        grounding_found = any(phrase in response_lower for phrase in _GROUNDING_PHRASES)
        # If response is long and doesn't reference context at all, flag it
        if len(response) > 500 and not grounding_found:
            quality["warnings"].append("Long response without explicit context reference")
            quality["grounded"] = False
        else:
            quality["checks_passed"] += 1
    else:
        # No context available — check that AI acknowledges the limitation
        mentions_no_docs = any(
            kw in response_lower
            for kw in ["no syllabus", "not covered", "upload", "no documents", "not found"]
        )
        if mentions_no_docs:
            quality["checks_passed"] += 1
            quality["grounded"] = True
        else:
            quality["warnings"].append("Response generated without syllabus context — may contain ungrounded content")
            quality["grounded"] = False
            quality["confidence"] = "medium"

    # ── Check 4: Formatting quality ──
    has_formatting = any(marker in response for marker in [
        "**", "##", "- ", "1.", "```", "| ", "> "
    ])
    if has_formatting:
        quality["checks_passed"] += 1
    else:
        if len(response) > 200:
            quality["warnings"].append("Long response lacks markdown formatting")

    # ── Check 5: Exam appropriateness (for exam-style questions) ──
    exam_keywords = ["mark", "exam", "define", "explain", "describe", "compare", "differentiate"]
    is_exam_question = any(kw in user_message.lower() for kw in exam_keywords)
    if is_exam_question:
        has_structure = ("**" in response or "##" in response) and (
            "- " in response or "1." in response
        )
        if has_structure:
            quality["checks_passed"] += 1
        else:
            quality["warnings"].append("Exam-style question but response lacks structured formatting")
    else:
        quality["checks_passed"] += 1

    # ── Compute overall confidence ──
    ratio = quality["checks_passed"] / quality["checks_total"]
    if ratio >= 0.8:
        quality["confidence"] = "high"
    elif ratio >= 0.6:
        quality["confidence"] = "medium"
    else:
        quality["confidence"] = "low"

    logger.info(
        f"Quality check: {quality['checks_passed']}/{quality['checks_total']} passed, "
        f"confidence={quality['confidence']}, grounded={quality['grounded']}"
    )

    return quality



# ── Greeting Prompt ───────────────────────────────────────────

GREETING_PROMPT = """A student has just started a study session. Generate a warm, helpful greeting and a clear unit overview.

STUDENT INFO:
- Name: {student_name}
- Department: {department}
- Year: {year}, Semester: {semester}
- Section: {section}

STUDY SESSION:
- Subject: {subject_name} ({subject_code})
- Unit: {unit_title}

{context_section}

YOUR TASK:
1. Greet the student warmly by name with a wave emoji
2. Confirm their study session details (subject and unit)
3. FIRST, display the unit topic clearly:
   - Show: "📋 **Unit Topic:** {unit_title}" as a prominent heading
4. THEN provide a clear, exam-focused overview of this unit that includes:
   - What this unit covers (main topics as bullet points)
   - Why it's important (exam relevance)
   - Key concepts to focus on
5. End with an encouraging message and ask what they'd like to study first

CRITICAL RULES:
- You MUST base the overview STRICTLY and ONLY on the provided syllabus context below.
- Do NOT add any information from your own training data or general knowledge.
- If syllabus context IS provided, extract topics, definitions, and concepts ONLY from that context.
- If NO syllabus context is available, DO NOT generate a general overview. Instead:
  - Show the unit topic name
  - State clearly that no study materials have been uploaded yet for this unit
  - Ask the student to upload their PDF notes/textbook for this unit
  - Explain that once uploaded, you can provide syllabus-grounded answers

FORMATTING RULES:
- Use markdown for structure (headings, bold, bullet points)
- Keep the overview concise but informative (suitable for exam prep)
- Make it feel like a friendly, intelligent tutor greeting
- Use emojis sparingly for warmth

Generate the greeting now:"""


GREETING_SYSTEM = """You are an expert AI Study Assistant for university students in Computer Science Engineering. 
You are warm, encouraging, and focused on exam preparation. 
You help students understand their syllabus systematically.
CRITICAL: You MUST only provide information from the uploaded syllabus documents (PDF context). 
NEVER use general knowledge or training data. If no documents are uploaded, say so clearly."""


async def generate_greeting(
    student_name: str,
    subject_code: str,
    subject_name: str,
    unit_number: int,
    unit_title: str = "",
    section: str = "",
    context: str = ""
) -> str:
    """
    Generate a personalized greeting with unit overview for a new study session.
    """
    context_section = ""
    if context:
        context_section = f"--- SYLLABUS CONTEXT FOR THIS UNIT ---\n{context}\n--- END CONTEXT ---"
    else:
        context_section = (
            "[NO SYLLABUS DOCUMENTS UPLOADED]\n"
            "There are no uploaded study materials (PDFs) for this unit yet. "
            "Do NOT generate any overview from general knowledge. "
            "Instead, display the unit topic name, tell the student warmly that no materials have been uploaded yet, "
            "and ask them to upload their PDF notes/textbook through the Knowledge Base page "
            "so you can provide accurate, syllabus-grounded answers."
        )

    prompt = GREETING_PROMPT.format(
        student_name=student_name,
        department="Computer Science Engineering",
        year=2,
        semester=4,
        section=section or "N/A",
        subject_name=subject_name,
        subject_code=subject_code,
        unit_title=unit_title or f"Unit {unit_number}",
        context_section=context_section
    )

    try:
        return await _call_llm(prompt, GREETING_SYSTEM)
    except Exception as e:
        logger.error(f"Greeting generation failed: {e}")
        # Return a structured fallback greeting
        return f"""Hello {student_name} 👋

Welcome to your study session!

**📚 Subject:** {subject_name} ({subject_code})
**📋 Unit Topic:** {unit_title or f'Unit {unit_number}'}

I'm your AI Study Assistant, ready to help you prepare for your exams.

> ⚠️ **No study materials uploaded yet for this unit.**
> Please upload your syllabus PDF/notes for this unit through the **Knowledge Base** page so I can provide accurate, syllabus-grounded responses.
> I only answer from your uploaded materials — this ensures everything is exam-relevant and accurate!

Once you upload your materials, I can help you with:
- 📝 **2-Mark Questions** — Quick, exam-ready answers from your PDF
- 📖 **10-Mark Questions** — Detailed, structured explanations from your notes
- 💡 **Concept Explanations** — Clear breakdowns based on your syllabus
- 📋 **Quick Revision** — Key points from your study materials

Upload your notes and let's get started! 📚"""


# ── Study Mode Question Generation ────────────────────────────

QUESTION_GENERATION_PROMPT = """You are an expert exam question setter for university exams.

SUBJECT: {subject_name}
UNIT: Unit {unit_number} — {unit_title}
MODE: {mode_label}

{context_section}

YOUR TASK:
Generate a comprehensive list of {mode_label} questions for this unit based STRICTLY on the syllabus context provided above.

{mode_instructions}

CRITICAL RULES:
1. Base ALL questions strictly on the provided syllabus context
2. Questions must be exam-appropriate and cover all major topics
3. Do NOT include answers — only questions
4. Do NOT number the questions — just list one per line
5. Return ONLY the questions, one per line, nothing else
6. Each question must be a complete, well-formed exam question
7. Do NOT add any introductory text, headings, or commentary

Generate the questions now (one per line):"""


QUESTION_GENERATION_SYSTEM = """You are a university exam question paper setter.
You generate precise, exam-appropriate questions based on provided syllabus content.
Return ONLY questions, one per line. No numbering, no formatting, no commentary."""


async def generate_study_questions(
    subject_name: str,
    unit_title: str,
    unit_number: int,
    mode: str,
    context: str = ""
) -> list:
    """
    Generate a list of exam questions (2-mark or 10-mark) from syllabus context.
    Returns a list of question strings.
    """
    if mode == "2_mark":
        mode_label = "2-Mark"
        mode_instructions = """QUESTION STYLE — 2-Mark Questions:
- Short, definition-based questions
- "Define...", "What is...", "List...", "State...", "Differentiate between..."
- Each question should be answerable in 2-4 sentences
- Generate at least 10-15 questions covering all key concepts"""
    else:
        mode_label = "10-Mark"
        mode_instructions = """QUESTION STYLE — 10-Mark Questions:
- Long, detailed questions requiring structured answers
- "Explain in detail...", "Describe with examples...", "Compare and contrast...", "Discuss..."
- Each question should require a full-page answer with diagrams/examples
- Generate at least 5-8 questions covering major topics"""

    context_section = ""
    if context:
        context_section = f"--- SYLLABUS CONTEXT ---\n{context}\n--- END CONTEXT ---"
    else:
        context_section = (
            "[NO SYLLABUS DOCUMENTS UPLOADED]\n"
            "There are no uploaded study materials (PDFs) for this subject/unit. "
            "Do NOT generate questions from general knowledge. "
            "Instead, return a single line: 'No syllabus documents have been uploaded for this unit yet. "
            "Please upload your study materials through the Knowledge Base page to generate exam questions.'"
        )

    prompt = QUESTION_GENERATION_PROMPT.format(
        subject_name=subject_name,
        unit_number=unit_number,
        unit_title=unit_title,
        mode_label=mode_label,
        mode_instructions=mode_instructions,
        context_section=context_section
    )

    try:
        raw_response = await _call_llm(prompt, QUESTION_GENERATION_SYSTEM)

        # Parse response: extract questions (one per line)
        questions = []
        for line in raw_response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove common numbering patterns: "1.", "1)", "Q1.", "Q1)", "- ", "• "
            import re
            cleaned = re.sub(r'^(?:Q?\d+[\.\)]\s*|[-•]\s*|\*\s*)', '', line).strip()
            if cleaned and len(cleaned) > 5:  # Skip tiny fragments
                # Ensure it ends with a question mark or period
                if not cleaned.endswith(('?', '.')):
                    cleaned += '?'
                questions.append(cleaned)

        if not questions:
            # Fallback: return the raw lines
            questions = [line.strip() for line in raw_response.strip().split("\n") if line.strip()]

        logger.info(f"Generated {len(questions)} {mode_label} questions for {subject_name} Unit {unit_number}")
        return questions

    except Exception as e:
        logger.error(f"Study question generation failed: {e}")
        raise


async def health_check() -> dict:
    """Check LLM service health."""
    provider = settings.llm_provider.lower()

    if provider == "groq" and not settings.groq_api_key:
        return {"status": "not_configured", "provider": "groq", "model": settings.llm_model}
    if provider == "gemini" and not settings.gemini_api_key:
        return {"status": "not_configured", "provider": "gemini", "model": settings.llm_model}

    try:
        _get_client()
        return {"status": "ready", "provider": provider, "model": settings.llm_model}
    except Exception as e:
        return {"status": "error", "provider": provider, "model": settings.llm_model, "error": str(e)}

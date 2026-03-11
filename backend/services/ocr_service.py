"""
OCR Service — Gemini Vision-based text extraction for scanned/handwritten documents.

Used as a fallback when regular text extraction yields insufficient text.
Only activates when GEMINI_API_KEY is configured in .env.

Includes robust rate-limit handling with exponential backoff for the Gemini free tier.
This service is ISOLATED — it does not affect chat, LLM, RAG, or any other service.
"""

import io
import logging
import time
from pathlib import Path
from config import settings

logger = logging.getLogger("syllabus_ai")

# ── Configuration ────────────────────────────────────────────

OCR_MODEL_NAME = "gemini-2.0-flash"
MIN_WORDS_PER_PAGE = 20          # Below this → page is likely scanned/handwritten
REQUEST_DELAY_SECONDS = 5.0      # Base delay between requests (free tier ~15 RPM)
MAX_RETRIES = 4                  # Max retries per page on rate limit
RENDER_SCALE = 2                 # 2x resolution for better OCR accuracy


# ── Lazy-Initialized Model ──────────────────────────────────

_ocr_model = None


def _get_ocr_model():
    """Lazy-initialize the Gemini Vision model for OCR."""
    global _ocr_model
    if _ocr_model is not None:
        return _ocr_model

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is required for OCR support. "
            "Get a free key at https://aistudio.google.com"
        )

    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    _ocr_model = genai.GenerativeModel(OCR_MODEL_NAME)
    logger.info(f"✓ Gemini Vision OCR initialized — model: {OCR_MODEL_NAME}")
    return _ocr_model


# ── OCR Prompt ───────────────────────────────────────────────

_OCR_PROMPT = (
    "Extract ALL text from this image exactly as written. "
    "This is a page from university study notes or a textbook.\n\n"
    "Rules:\n"
    "1. Preserve the original structure: headings, bullet points, numbered lists, paragraphs.\n"
    "2. If there are diagrams or figures, describe them briefly as [DIAGRAM: description].\n"
    "3. Write mathematical formulas in plain text notation.\n"
    "4. Preserve table structures using plain text alignment.\n"
    "5. Output ONLY the extracted text. No commentary, no explanations."
)


# ── Core Functions ───────────────────────────────────────────

def _render_page_to_png(pdf_path: str, page_number: int) -> bytes:
    """Render a single PDF page to PNG bytes using PyMuPDF."""
    import fitz
    with fitz.open(pdf_path) as doc:
        page = doc[page_number]
        mat = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
        pixmap = page.get_pixmap(matrix=mat)
        return pixmap.tobytes("png")


def _ocr_single_page(image_bytes: bytes) -> str:
    """Extract text from a single page image using Gemini Vision.
    Includes retry logic with exponential backoff for rate limit errors.
    """
    from PIL import Image

    model = _get_ocr_model()
    img = Image.open(io.BytesIO(image_bytes))

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = model.generate_content([_OCR_PROMPT, img])
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "Resource has been exhausted" in error_str

            if is_rate_limit and attempt < MAX_RETRIES:
                # Exponential backoff: 10s, 20s, 40s, 80s
                backoff = 10 * (2 ** attempt)
                logger.warning(
                    f"  Rate limited (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                    f"waiting {backoff}s before retry..."
                )
                time.sleep(backoff)
                continue
            else:
                raise


def extract_pdf_with_ocr(filepath: str) -> str:
    """
    Hybrid text extraction for PDFs:
      - Pages with sufficient digital text → regular extraction (fast)
      - Pages with low/no text → Gemini Vision OCR (handles handwriting)

    This function is called ONLY when regular extraction yields low text.
    It does NOT affect any other service or feature.
    """
    import fitz

    filename = Path(filepath).name
    text_parts = []          # (page_num, text)
    ocr_page_nums = []       # pages needing OCR

    # ── Phase 1: Identify pages needing OCR ──────────────────
    with fitz.open(filepath) as doc:
        total_pages = len(doc)
        for page_num in range(total_pages):
            page_text = doc[page_num].get_text().strip()
            word_count = len(page_text.split())

            if word_count >= MIN_WORDS_PER_PAGE:
                text_parts.append((page_num, page_text))
            else:
                ocr_page_nums.append(page_num)

    if not ocr_page_nums:
        # All pages had sufficient digital text — no OCR needed
        return "\n\n".join(text for _, text in sorted(text_parts))

    logger.info(
        f"  OCR: {len(ocr_page_nums)}/{total_pages} pages need Vision OCR "
        f"in {filename}"
    )

    # ── Phase 2: OCR the pages that need it ──────────────────
    successful_ocr = 0
    failed_ocr = 0

    for i, page_num in enumerate(ocr_page_nums):
        try:
            png_bytes = _render_page_to_png(filepath, page_num)
            ocr_text = _ocr_single_page(png_bytes)
            word_count = len(ocr_text.split())
            text_parts.append((page_num, ocr_text))
            successful_ocr += 1
            logger.info(f"  OCR page {page_num + 1}/{total_pages}: {word_count} words ✓")

            # Rate limit delay — skip after last page
            if i < len(ocr_page_nums) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as e:
            failed_ocr += 1
            logger.warning(f"  OCR failed for page {page_num + 1}: {e}")
            continue

    # ── Combine all pages in original order ──────────────────
    text_parts.sort(key=lambda x: x[0])
    combined = "\n\n".join(text for _, text in text_parts)
    total_words = len(combined.split())
    logger.info(
        f"  OCR complete: {total_words} total words from {filename} "
        f"({successful_ocr} pages OCR'd, {failed_ocr} failed)"
    )
    return combined

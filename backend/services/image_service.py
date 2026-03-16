"""
Image Service — Extracts images from uploaded PDFs, generates captions via Groq,
uploads to Supabase Storage, and retrieves relevant images for RAG queries.

CORE PRINCIPLE: Images are STRICTLY from uploaded PDFs — NEVER AI-generated.
Groq is used ONLY to describe/caption what a PDF image contains (for search indexing).
"""

import io
import hashlib
import base64
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import settings

logger = logging.getLogger("syllabus_ai")

# ── Configuration ────────────────────────────────────────────
MIN_IMAGE_WIDTH = 150       # Skip images smaller than this (icons, bullets)
MIN_IMAGE_HEIGHT = 150
MIN_IMAGE_BYTES = 5000      # Skip very small images (< 5KB likely decorative)
MAX_IMAGES_PER_PDF = 50     # Safety cap
CAPTION_MODEL = "llama-3.2-90b-vision-preview"  # Groq vision model


# ── Lazy Clients ─────────────────────────────────────────────

_supabase_client = None
_groq_client = None


def _get_supabase():
    """Lazy-initialize Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    from supabase import create_client
    _supabase_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _supabase_client


def _get_groq():
    """Lazy-initialize Groq client for image captioning."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    from groq import Groq
    _groq_client = Groq(api_key=settings.groq_api_key)
    logger.info(f"✓ Groq vision client initialized for captioning (model: {CAPTION_MODEL})")
    return _groq_client


# ── Image Extraction ─────────────────────────────────────────

def extract_images_from_pdf(filepath: str) -> List[Dict]:
    """
    Extract meaningful diagram images from a PDF using PyMuPDF.
    
    Filters out:
    - Tiny images (icons, bullets, decorative elements)
    - Duplicate images (same image repeated across pages — e.g. slide backgrounds)
    
    Returns:
        List of dicts with keys: page_number, image_index, image_bytes, width, height, page_text
    """
    import fitz

    images = []
    seen_hashes = set()  # Deduplicate identical images across pages

    with fitz.open(filepath) as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()[:500]  # Surrounding text for context
            page_images = page.get_images(full=True)

            for img_idx, img in enumerate(page_images):
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                except Exception:
                    continue

                # Filter: size check
                if pix.width < MIN_IMAGE_WIDTH or pix.height < MIN_IMAGE_HEIGHT:
                    continue

                # Convert CMYK to RGB if needed
                if pix.n >= 5:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                png_bytes = pix.tobytes("png")

                # Filter: byte size check
                if len(png_bytes) < MIN_IMAGE_BYTES:
                    continue

                # Deduplicate: hash-based check
                img_hash = hashlib.md5(png_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                seen_hashes.add(img_hash)

                images.append({
                    "page_number": page_num,
                    "image_index": img_idx,
                    "image_bytes": png_bytes,
                    "width": pix.width,
                    "height": pix.height,
                    "page_text": page_text,
                    "hash": img_hash,
                })

                if len(images) >= MAX_IMAGES_PER_PDF:
                    logger.warning(
                        f"Hit max image cap ({MAX_IMAGES_PER_PDF}) for {Path(filepath).name}"
                    )
                    return images

    logger.info(
        f"Extracted {len(images)} unique meaningful images from "
        f"{Path(filepath).name} ({len(seen_hashes)} unique, checked {len(doc)} pages)"
    )
    return images


# ── Caption Generation (Groq Vision) ────────────────────────

CAPTION_PROMPT = (
    "Describe this image in one concise sentence. It is a diagram/figure from a "
    "university textbook or study notes. Focus on: what type of diagram it is, "
    "what concept or architecture it illustrates, and any visible labels. "
    "Example: 'Block diagram showing the basic functional units of a computer "
    "including input, output, memory, ALU, and control unit.' "
    "Return ONLY the description, nothing else."
)


def generate_caption(image_bytes: bytes) -> str:
    """
    Use Groq Vision to describe what a PDF image contains.
    This is for SEARCH INDEXING only — NOT image generation.
    
    Returns a concise description string.
    """
    try:
        client = _get_groq()
        
        # Convert image bytes to base64 for the API
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        response = client.chat.completions.create(
            model=CAPTION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CAPTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=150,
            temperature=0.1,
        )
        
        caption = response.choices[0].message.content.strip()
        return caption
        
    except Exception as e:
        logger.warning(f"Caption generation failed: {e}")
        return ""


# ── Supabase Storage Upload ─────────────────────────────────

def upload_to_storage(
    image_bytes: bytes,
    storage_path: str
) -> str:
    """
    Upload image to Supabase Storage 'document-images' bucket.
    Returns the public URL.
    """
    client = _get_supabase()
    bucket = "document-images"
    
    try:
        # Remove existing file if any (for re-uploads)
        try:
            client.storage.from_(bucket).remove([storage_path])
        except Exception:
            pass
        
        # Upload
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=image_bytes,
            file_options={"content-type": "image/png"}
        )
        
        # Get public URL
        public_url = client.storage.from_(bucket).get_public_url(storage_path)
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload image to storage: {e}")
        raise


# ── Metadata Storage ─────────────────────────────────────────

def store_image_metadata(
    image_id: str,
    subject_code: str,
    unit_number: int,
    section: str,
    source_file: str,
    page_number: int,
    image_index: int,
    caption: str,
    context_text: str,
    storage_path: str,
    public_url: str,
    width: int,
    height: int
):
    """Insert image metadata into the document_images table."""
    client = _get_supabase()
    
    row = {
        "id": image_id,
        "subject_code": subject_code,
        "unit_number": unit_number or 0,
        "section": section or "",
        "source_file": source_file,
        "page_number": page_number,
        "image_index": image_index,
        "caption": caption,
        "context_text": context_text[:500] if context_text else "",
        "storage_path": storage_path,
        "public_url": public_url,
        "width": width,
        "height": height,
    }
    
    try:
        client.table("document_images").upsert(row).execute()
    except Exception as e:
        logger.error(f"Failed to store image metadata: {e}")
        raise


# ── End-to-End Processing ────────────────────────────────────

async def process_pdf_images(
    filepath: str,
    subject_code: str,
    unit_number: int,
    section: Optional[str] = None,
    source_filename: Optional[str] = None
) -> int:
    """
    Full pipeline: Extract images from PDF → caption → upload → store metadata.
    Returns the number of images processed.
    
    This is NON-BLOCKING for the upload flow — if it fails, text ingestion still works.
    """
    filename = source_filename or Path(filepath).name
    
    # Step 1: Extract images
    images = extract_images_from_pdf(filepath)
    if not images:
        logger.info(f"No meaningful images found in {filename}")
        return 0
    
    logger.info(f"Processing {len(images)} images from {filename}...")
    
    # Step 2: Delete any existing images for this file (re-upload support)
    try:
        await delete_images_by_source(subject_code, filename, section)
    except Exception:
        pass
    
    processed = 0
    section_prefix = f"_{section.lower()}" if section else ""
    stem = Path(filename).stem
    
    for img_data in images:
        try:
            page_num = img_data["page_number"]
            img_idx = img_data["image_index"]
            image_bytes = img_data["image_bytes"]
            
            # Generate unique ID
            image_id = (
                f"{subject_code.lower()}{section_prefix}_u{unit_number}_"
                f"{stem}_p{page_num}_img{img_idx}"
            )
            
            # Storage path in Supabase bucket
            storage_path = (
                f"{subject_code}/{section or 'general'}/u{unit_number}/"
                f"{stem}_p{page_num}_img{img_idx}.png"
            )
            
            # Step 2: Generate caption using Groq Vision
            caption = generate_caption(image_bytes)
            
            # Step 3: Upload to Supabase Storage
            public_url = upload_to_storage(image_bytes, storage_path)
            
            # Step 4: Store metadata in DB
            store_image_metadata(
                image_id=image_id,
                subject_code=subject_code,
                unit_number=unit_number,
                section=section or "",
                source_file=filename,
                page_number=page_num,
                image_index=img_idx,
                caption=caption,
                context_text=img_data.get("page_text", ""),
                storage_path=storage_path,
                public_url=public_url,
                width=img_data["width"],
                height=img_data["height"],
            )
            
            processed += 1
            logger.info(
                f"  ✓ Image {processed}/{len(images)}: page {page_num + 1}, "
                f"{img_data['width']}x{img_data['height']} — "
                f"caption: {caption[:60]}..."
            )
            
        except Exception as e:
            logger.warning(f"  ✗ Failed to process image p{page_num}_img{img_idx}: {e}")
            continue
    
    logger.info(f"✓ Processed {processed}/{len(images)} images from {filename}")
    return processed


# ── Image Retrieval ──────────────────────────────────────────

async def retrieve_relevant_images(
    query: str,
    subject_code: str,
    unit_number: Optional[int] = None,
    section: Optional[str] = None,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find relevant images from uploaded PDFs using full-text search
    on captions and page context.
    
    Returns list of: {url, caption, source_file, page_number}
    """
    client = _get_supabase()
    
    try:
        result = client.rpc("search_images", {
            "query_text": query,
            "filter_subject": subject_code,
            "filter_unit": unit_number,
            "filter_section": section or "",
            "match_count": top_k,
        }).execute()
        
        if result.data:
            images = [
                {
                    "url": row["public_url"],
                    "caption": row.get("caption", ""),
                    "source_file": row.get("source_file", ""),
                    "page_number": row.get("page_number", 0),
                }
                for row in result.data
            ]
            logger.info(
                f"Image search found {len(images)} images for "
                f"'{query[:50]}...' in {subject_code}"
            )
            return images
        
    except Exception as e:
        logger.warning(f"Image search failed: {e}")
    
    return []


# ── Cleanup ──────────────────────────────────────────────────

async def delete_images_by_source(
    subject_code: str,
    filename: str,
    section: Optional[str] = None
) -> int:
    """Delete all images from a specific source file."""
    client = _get_supabase()
    
    try:
        # Get existing image records
        query = client.table("document_images") \
            .select("id, storage_path") \
            .eq("subject_code", subject_code) \
            .eq("source_file", filename)
        
        if section:
            query = query.eq("section", section)
        
        result = query.execute()
        
        if not result.data:
            return 0
        
        # Delete from storage
        storage_paths = [row["storage_path"] for row in result.data if row.get("storage_path")]
        if storage_paths:
            try:
                client.storage.from_("document-images").remove(storage_paths)
            except Exception as e:
                logger.warning(f"Failed to remove images from storage: {e}")
        
        # Delete metadata records
        ids = [row["id"] for row in result.data]
        for chunk_ids in [ids[i:i+50] for i in range(0, len(ids), 50)]:
            client.table("document_images") \
                .delete() \
                .in_("id", chunk_ids) \
                .execute()
        
        count = len(result.data)
        logger.info(f"Deleted {count} images for {filename}")
        return count
        
    except Exception as e:
        logger.error(f"Failed to delete images: {e}")
        return 0

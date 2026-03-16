"""
Document Routes — endpoints for document upload, listing, stats, and deletion.
Supports per-section (A, B, C) document management for each subject.
"""

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from models.schemas import DocumentUploadResponse, DocumentListResponse, GenericResponse
from services import document_service, rag_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

VALID_SECTIONS = {"A", "B", "C"}


def _validate_section(section: Optional[str]) -> Optional[str]:
    """Validate and normalize section parameter."""
    if section is None:
        return None
    section = section.upper().strip()
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid section '{section}'. Must be one of: A, B, C"
        )
    return section


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    subject_code: str = Form(...),
    unit_number: int = Form(...),
    section: Optional[str] = Form(None)
):
    """
    Upload a syllabus document (PDF, PPTX, DOCX).
    The document will be processed, chunked, and indexed in the RAG system.
    Section (A, B, or C) determines which class the notes belong to.
    """
    # Validate section
    section = _validate_section(section)

    # Validate file type
    if not document_service.validate_file(file.filename):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type. Supported: {', '.join(document_service.SUPPORTED_EXTENSIONS)}"
        )

    # Save file to disk (in section-specific directory)
    doc_dir = document_service.get_document_dir(subject_code, section)
    filepath = doc_dir / file.filename

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Extract text
    try:
        text = await document_service.extract_text(str(filepath))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")

    # Chunk the text
    chunks = document_service.chunk_text(text)

    if not chunks:
        return DocumentUploadResponse(
            filename=file.filename,
            subject_code=subject_code,
            unit_number=unit_number,
            section=section,
            chunks_created=0,
            message="No text content found in the document."
        )

    # Generate chunk IDs and metadata (include section in IDs)
    section_prefix = f"_{section.lower()}" if section else ""
    chunk_ids = [
        f"{subject_code.lower()}{section_prefix}_u{unit_number}_{Path(file.filename).stem}_chunk_{i}"
        for i in range(len(chunks))
    ]
    metadatas = [
        {
            "source": file.filename,
            "subject_code": subject_code,
            "unit_number": unit_number,
            "section": section or "",
            "chunk_index": i
        }
        for i in range(len(chunks))
    ]

    # Add to RAG vector store — store in BOTH unit-specific AND general collections
    # This ensures queries with and without unit filters can find the documents
    try:
        # 1. Store in unit-specific collection
        count = await rag_service.add_documents(
            texts=chunks,
            metadatas=metadatas,
            ids=chunk_ids,
            subject_code=subject_code,
            unit_number=unit_number,
            section=section
        )

        # 2. Also store in general collection (broader fallback for queries)
        general_ids = [f"{cid}_gen" for cid in chunk_ids]
        await rag_service.add_documents(
            texts=chunks,
            metadatas=metadatas,
            ids=general_ids,
            subject_code=subject_code,
            unit_number=None,  # General collection
            section=section
        )
        import logging
        logger = logging.getLogger("syllabus_ai")
        logger.info(
            f"✓ Indexed {count} chunks for {subject_code} Unit {unit_number} "
            f"Section {section or 'General'} (unit + general collections)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index document: {e}")

    # Step 5: Extract and store images from PDF (non-blocking)
    image_count = 0
    if filepath.suffix.lower() == ".pdf":
        try:
            from services import image_service
            image_count = await image_service.process_pdf_images(
                filepath=str(filepath),
                subject_code=subject_code,
                unit_number=unit_number,
                section=section,
                source_filename=file.filename
            )
        except Exception as e:
            import logging
            logging.getLogger("syllabus_ai").warning(f"Image extraction skipped (non-blocking): {e}")

    img_msg = f" Extracted {image_count} images." if image_count > 0 else ""
    return DocumentUploadResponse(
        filename=file.filename,
        subject_code=subject_code,
        unit_number=unit_number,
        section=section,
        chunks_created=count,
        message=f"Successfully processed and indexed {count} chunks for Section {section or 'General'}.{img_msg}"
    )


@router.get("/{subject_code}/stats")
async def get_document_stats(
    subject_code: str,
    section: Optional[str] = Query(None, description="Section A, B, or C")
):
    """
    Get RAG statistics for a subject — how many chunks per unit,
    which units have documents, and overall readiness.
    Optionally filter by section.
    """
    section = _validate_section(section)

    try:
        unit_stats = await rag_service.get_collection_stats(subject_code, section)
    except Exception:
        unit_stats = {}

    docs = await document_service.list_documents(subject_code, section)
    total_chunks = sum(u.get("chunks", 0) for u in unit_stats.values())
    units_ready = sum(1 for u in unit_stats.values() if u.get("status") == "ready")

    return {
        "success": True,
        "subject_code": subject_code,
        "section": section,
        "total_documents": len(docs),
        "total_chunks": total_chunks,
        "units_ready": units_ready,
        "units": unit_stats,
        "rag_status": "ready" if total_chunks > 0 else "no_documents"
    }


@router.delete("/{subject_code}/{filename}")
async def delete_document(
    subject_code: str,
    filename: str,
    section: Optional[str] = Query(None, description="Section A, B, or C")
):
    """
    Delete a document from disk and remove its chunks from ChromaDB.
    Specify section to delete from a specific section's folder.
    """
    section = _validate_section(section)

    doc_dir = document_service.get_document_dir(subject_code, section)
    filepath = doc_dir / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    # Remove chunks from Supabase
    removed_chunks = 0
    try:
        removed_chunks = await rag_service.delete_by_source(subject_code, filename, section)
    except Exception:
        pass

    # Remove associated images
    removed_images = 0
    try:
        from services import image_service
        removed_images = await image_service.delete_images_by_source(subject_code, filename, section)
    except Exception:
        pass

    # Delete file from disk
    try:
        filepath.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    return {
        "success": True,
        "message": f"Deleted {filename} and removed {removed_chunks} chunks + {removed_images} images from RAG (Section {section or 'General'}).",
        "removed_chunks": removed_chunks,
        "removed_images": removed_images
    }


@router.get("/{subject_code}")
async def list_documents(
    subject_code: str,
    section: Optional[str] = Query(None, description="Section A, B, or C")
):
    """List all uploaded documents for a subject, optionally filtered by section."""
    section = _validate_section(section)
    docs = await document_service.list_documents(subject_code, section)
    return {"success": True, "documents": docs, "total": len(docs), "section": section}


@router.get("/{subject_code}/sections")
async def get_section_overview(subject_code: str):
    """Get document count for each section (A, B, C) of a subject."""
    overview = {}
    for sec in ["A", "B", "C"]:
        docs = await document_service.list_documents(subject_code, sec)
        overview[sec] = {
            "document_count": len(docs),
            "filenames": [d["filename"] for d in docs]
        }
    return {"success": True, "subject_code": subject_code, "sections": overview}

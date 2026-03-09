"""
Ingestion Script — Extracts text from documents, chunks them, 
and stores them in ChromaDB for RAG retrieval.

Auto-detects unit numbers from filenames when --unit is not specified.

Usage:
    python ingest.py --subject APJ --section A --unit 1
    python ingest.py --subject APJ --section B       # Ingests all units for section B
    python ingest.py --subject APJ                   # Ingests all (no section filter)
    python ingest.py --all                           # Ingests all subjects
    python ingest.py --all --section A               # Ingests all subjects, section A only
    python ingest.py --stats                         # Show collection statistics
    python ingest.py --clear --all                   # Clear all collections and re-ingest
"""

import os
import re
import sys
import argparse
import uuid
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from services.document_service import extract_text, chunk_text, validate_file, SUPPORTED_EXTENSIONS
from services.rag_service import get_or_create_collection, _get_chroma_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest")


# ── Unit Number Auto-Detection ───────────────────────────────

# Patterns to detect unit numbers from filenames (order matters — first match wins)
_UNIT_PATTERNS = [
    re.compile(r'unit[\s_-]*(\d)', re.IGNORECASE),           # "Unit 1", "unit_1", "unit-1", "UNIT1"
    re.compile(r'u[\s_-]*(\d)(?!\w)', re.IGNORECASE),        # "U1", "u_1", "u-1"
    re.compile(r'ut[\s_-]*(\d)', re.IGNORECASE),             # "UT1", "ut1"
    re.compile(r'(?:chapter|ch)[\s_-]*(\d)', re.IGNORECASE), # "Chapter 1", "ch1"
    re.compile(r'(?:module|mod)[\s_-]*(\d)', re.IGNORECASE), # "Module 1", "mod1"
]


def detect_unit_from_filename(filename: str) -> int:
    """
    Auto-detect unit number from a filename.
    
    Examples:
        "DAA-UNIT-1.pdf"           → 1
        "Unit 1_Organisational.pdf" → 1
        "coa unit 2 (1).pdf"       → 2
        "COA UT1-final (1).pdf"    → 1
        "java ppt.pdf"            → None (no unit detected)
    
    Returns:
        Detected unit number (1-5), or None if not detected.
    """
    stem = Path(filename).stem
    
    for pattern in _UNIT_PATTERNS:
        match = pattern.search(stem)
        if match:
            unit_num = int(match.group(1))
            if 1 <= unit_num <= 5:
                return unit_num
    
    return None


def ingest_file(filepath: str, subject_code: str, unit_number: int = None, section: str = None):
    """Ingest a single document file into ChromaDB."""
    filename = Path(filepath).name
    
    # Auto-detect unit if not explicitly provided
    effective_unit = unit_number
    if effective_unit is None:
        effective_unit = detect_unit_from_filename(filename)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {filename}")
    unit_label = f"Unit {effective_unit}" if effective_unit else "General"
    auto_tag = " (auto-detected)" if unit_number is None and effective_unit else ""
    logger.info(f"Subject: {subject_code} | Section: {section or 'General'} | {unit_label}{auto_tag}")
    logger.info(f"{'='*60}")

    # Step 1: Extract text
    logger.info("Step 1: Extracting text...")
    import asyncio
    text = asyncio.run(extract_text(filepath))
    word_count = len(text.split())
    logger.info(f"  Extracted {word_count} words from {filename}")

    if word_count < 10:
        logger.warning(f"  SKIP: Too little text extracted ({word_count} words)")
        return 0

    # Step 2: Chunk text
    logger.info("Step 2: Chunking text...")
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    logger.info(f"  Created {len(chunks)} chunks (500 words, 100 overlap)")

    # Step 3: Generate IDs and metadata
    logger.info("Step 3: Preparing metadata...")
    stem = Path(filepath).stem
    section_prefix = f"_{section.lower()}" if section else ""
    ids = [f"{subject_code.lower()}{section_prefix}_u{effective_unit or 0}_{stem}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "subject_code": subject_code,
            "unit_number": effective_unit or 0,
            "section": section or "",
            "filename": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source": filepath
        }
        for i in range(len(chunks))
    ]

    # Step 4: Store in ChromaDB — store in BOTH unit-specific AND general collections
    logger.info("Step 4: Storing in ChromaDB...")
    
    collections_stored = []
    
    # Store in unit-specific collection (if unit detected)
    if effective_unit:
        collection = get_or_create_collection(subject_code, effective_unit, section)
        _store_chunks(collection, chunks, metadatas, ids, filename)
        collections_stored.append(collection.name)
    
    # Also store in general collection (so queries without unit filter still work)
    general_collection = get_or_create_collection(subject_code, None, section)
    general_ids = [f"{id_}_gen" for id_ in ids]  # Different IDs for general collection
    _store_chunks(general_collection, chunks, metadatas, general_ids, filename)
    collections_stored.append(general_collection.name)

    logger.info(f"  ✓ Stored in collections: {', '.join(collections_stored)}")

    return len(chunks)


def _store_chunks(collection, chunks, metadatas, ids, filename):
    """Store chunks into a ChromaDB collection, replacing existing ones."""
    # Check for existing documents and delete them to avoid duplicates
    try:
        existing = collection.get(where={"filename": filename})
        if existing and existing["ids"]:
            logger.info(f"  Removing {len(existing['ids'])} existing chunks for {filename} from {collection.name}")
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # Collection might be new/empty

    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"  → {collection.name}: {len(chunks)} chunks added (total: {collection.count()})")


def ingest_subject(subject_code: str, unit_number: int = None, section: str = None):
    """Ingest all documents for a subject (or specific unit/section)."""
    doc_dir = Path(settings.document_storage_dir) / subject_code.upper()
    if section:
        doc_dir = doc_dir / section.upper()
    
    if not doc_dir.exists():
        logger.error(f"Document directory not found: {doc_dir}")
        return 0

    total_chunks = 0
    files_processed = 0

    for filepath in sorted(doc_dir.iterdir()):
        if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                chunks = ingest_file(str(filepath), subject_code.upper(), unit_number, section)
                total_chunks += chunks
                files_processed += 1
            except Exception as e:
                logger.error(f"  ERROR processing {filepath.name}: {e}")
                import traceback
                traceback.print_exc()

    logger.info(f"\n{'='*60}")
    logger.info(f"DONE: {subject_code} Section {section or 'All'} — {files_processed} files, {total_chunks} total chunks")
    logger.info(f"{'='*60}")
    return total_chunks


def clear_all_collections():
    """Delete all existing ChromaDB collections to start fresh."""
    client = _get_chroma_client()
    collections = client.list_collections()
    logger.info(f"\nClearing {len(collections)} collections...")
    for col in collections:
        name = col.name if hasattr(col, 'name') else str(col)
        try:
            client.delete_collection(name)
            logger.info(f"  Deleted: {name}")
        except Exception as e:
            logger.warning(f"  Failed to delete {name}: {e}")
    logger.info("✓ All collections cleared.\n")


def show_stats():
    """Show ChromaDB collection statistics."""
    client = _get_chroma_client()
    collections = client.list_collections()
    logger.info(f"\nChromaDB Collections ({len(collections)}):")
    logger.info("-" * 50)
    
    total_chunks = 0
    non_empty = 0
    
    for col in collections:
        # ChromaDB 1.5.0 returns Collection objects
        name = col.name if hasattr(col, 'name') else str(col)
        count = col.count() if hasattr(col, 'count') else 0
        total_chunks += count
        status = "✓" if count > 0 else "○"
        if count > 0:
            non_empty += 1
        logger.info(f"  {status} {name}: {count} chunks")
    
    logger.info("-" * 50)
    logger.info(f"Total: {total_chunks} chunks across {len(collections)} collections ({non_empty} non-empty)")


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
    parser.add_argument("--subject", "-s", type=str, help="Subject code (e.g., APJ, COA)")
    parser.add_argument("--unit", "-u", type=int, help="Unit number (1-5)", default=None)
    parser.add_argument("--section", "-S", type=str, help="Section (A, B, or C)", default=None)
    parser.add_argument("--all", action="store_true", help="Ingest all subjects")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all collections before ingesting")
    args = parser.parse_args()

    # Validate section
    if args.section and args.section.upper() not in {"A", "B", "C"}:
        logger.error(f"Invalid section: {args.section}. Must be A, B, or C.")
        return
    section = args.section.upper() if args.section else None

    if args.stats:
        show_stats()
        return

    if args.clear:
        clear_all_collections()

    if args.all:
        doc_root = Path(settings.document_storage_dir)
        if not doc_root.exists():
            logger.error(f"Document root not found: {doc_root}")
            return
        for subject_dir in sorted(doc_root.iterdir()):
            if subject_dir.is_dir():
                if section:
                    ingest_subject(subject_dir.name, args.unit, section)
                else:
                    # Ingest all sections
                    for sec in ["A", "B", "C"]:
                        sec_dir = subject_dir / sec
                        if sec_dir.exists() and any(sec_dir.iterdir()):
                            ingest_subject(subject_dir.name, args.unit, sec)
    elif args.subject:
        ingest_subject(args.subject, args.unit, section)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

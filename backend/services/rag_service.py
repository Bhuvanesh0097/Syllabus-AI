"""
RAG Service — Retrieval-Augmented Generation pipeline.
Manages ChromaDB collections, document embedding, and context retrieval.
Phase 1 provides the skeleton; full implementation in Phase 4.
"""

import logging
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger("syllabus_ai")

_chroma_client = None


def _get_chroma_client():
    """Lazy-initialize ChromaDB client."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        logger.info(f"✓ ChromaDB initialized at: {settings.chroma_persist_dir}")
        return _chroma_client
    except Exception as e:
        logger.error(f"✗ Failed to initialize ChromaDB: {e}")
        raise


def get_or_create_collection(subject_code: str, unit_number: Optional[int] = None, section: Optional[str] = None):
    """
    Get or create a ChromaDB collection for a subject/unit/section.
    Collection naming: 
      With section:    {subject_code}_{section}_unit_{number} or {subject_code}_{section}_general
      Without section: {subject_code}_unit_{number} or {subject_code}_general
    """
    client = _get_chroma_client()
    
    # Build collection name with optional section
    base = subject_code.lower()
    if section:
        base = f"{base}_{section.lower()}"
    
    collection_name = (
        f"{base}_unit_{unit_number}"
        if unit_number
        else f"{base}_general"
    )

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"subject": subject_code, "unit": unit_number or 0, "section": section or ""}
    )


async def retrieve_context(
    query: str,
    subject_code: str,
    unit_number: Optional[int] = None,
    section: Optional[str] = None,
    top_k: int = 5
) -> str:
    """
    Retrieve relevant context from the vector store for a given query.
    Uses a multi-level fallback strategy to maximize retrieval success:
      1. Section + Unit specific collection
      2. Section + General collection
      3. No-section + Unit specific collection
      4. No-section + General collection

    Args:
        query: User's question
        subject_code: Subject to search within
        unit_number: Optional unit filter
        section: Optional section filter (A, B, C)
        top_k: Number of results to retrieve

    Returns:
        Concatenated relevant document chunks
    """
    all_chunks = []

    # Build search strategy with multiple fallback levels
    # (label, unit_num, section_val) — ordered by specificity
    collections_to_try = []

    # Level 1: Section + Unit (most specific)
    if unit_number and section:
        collections_to_try.append(("section+unit", unit_number, section))
    
    # Level 2: Section + General
    if section:
        collections_to_try.append(("section+general", None, section))

    # Level 3: No-section + Unit (fallback for docs ingested without section)
    if unit_number:
        collections_to_try.append(("unit", unit_number, None))

    # Level 4: No-section + General (broadest fallback)
    collections_to_try.append(("general", None, None))

    for label, unit_num, sec in collections_to_try:
        try:
            collection = get_or_create_collection(subject_code, unit_num, sec)

            if collection.count() == 0:
                continue

            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )

            if results and results["documents"] and results["documents"][0]:
                chunks = results["documents"][0]
                all_chunks.extend(chunks)
                logger.info(
                    f"RAG retrieved {len(chunks)} chunks from "
                    f"{collection.name} ({label})"
                )
                # If we got enough results from a specific collection, stop searching
                if len(all_chunks) >= top_k:
                    break

        except Exception as e:
            logger.warning(f"RAG retrieval from {label} failed: {e}")
            continue

    if not all_chunks:
        logger.info(f"No RAG context found for {subject_code}/Unit {unit_number} (section={section})")
        return ""

    # Deduplicate and join
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_key = chunk[:100]  # Use first 100 chars as dedup key
        if chunk_key not in seen:
            seen.add(chunk_key)
            unique_chunks.append(chunk)

    context = "\n\n---\n\n".join(unique_chunks[:top_k])
    logger.info(f"RAG returning {len(unique_chunks[:top_k])} unique chunks for {subject_code}")
    return context


async def add_documents(
    texts: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    subject_code: str,
    unit_number: Optional[int] = None,
    section: Optional[str] = None
) -> int:
    """
    Add document chunks to the vector store.

    Args:
        texts: List of text chunks
        metadatas: Metadata for each chunk
        ids: Unique IDs for each chunk
        subject_code: Subject code
        unit_number: Unit number
        section: Section (A, B, or C)

    Returns:
        Number of chunks added
    """
    try:
        collection = get_or_create_collection(subject_code, unit_number, section)
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(texts)} chunks to {subject_code}/Unit {unit_number}")
        return len(texts)
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise


async def get_collection_stats(subject_code: str, section: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics for a subject's collections (optionally filtered by section)."""
    client = _get_chroma_client()
    stats = {}

    base = subject_code.lower()
    if section:
        base = f"{base}_{section.lower()}"

    for unit_num in range(1, 6):
        collection_name = f"{base}_unit_{unit_num}"
        try:
            collection = client.get_collection(collection_name)
            stats[f"unit_{unit_num}"] = {
                "chunks": collection.count(),
                "status": "ready" if collection.count() > 0 else "empty"
            }
        except Exception:
            stats[f"unit_{unit_num}"] = {"chunks": 0, "status": "not_created"}

    return stats


async def health_check() -> dict:
    """Check RAG system health."""
    try:
        client = _get_chroma_client()
        collections = client.list_collections()
        return {
            "status": "ready",
            "collections": len(collections),
            "persist_dir": settings.chroma_persist_dir
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

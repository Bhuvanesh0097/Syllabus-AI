"""
RAG Service — Retrieval-Augmented Generation pipeline.
Uses Supabase PostgreSQL with full-text search for persistent storage.
Replaces ephemeral ChromaDB with persistent Supabase database.
"""

import logging
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger("syllabus_ai")

_supabase_client = None


def _get_supabase_client():
    """Lazy-initialize Supabase client for RAG."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ValueError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY."
        )

    try:
        from supabase import create_client
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
        logger.info("✓ Supabase RAG client initialized")
        return _supabase_client
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase RAG: {e}")
        raise


async def retrieve_context(
    query: str,
    subject_code: str,
    unit_number: Optional[int] = None,
    section: Optional[str] = None,
    top_k: int = 5
) -> str:
    """
    Retrieve relevant context from Supabase using full-text search.
    Multi-level fallback: section+unit → section+general → unit → general.
    """
    client = _get_supabase_client()
    all_chunks = []

    # Fallback search levels (most specific → broadest)
    searches = []
    if unit_number and section:
        searches.append(("section+unit", unit_number, section))
    if section:
        searches.append(("section+general", None, section))
    if unit_number:
        searches.append(("unit", unit_number, None))
    searches.append(("general", None, None))

    for label, unit_num, sec in searches:
        try:
            result = client.rpc('search_chunks', {
                'query_text': query,
                'filter_subject': subject_code,
                'filter_unit': unit_num,
                'filter_section': sec or '',
                'match_count': top_k
            }).execute()

            if result.data:
                chunks = [row['content'] for row in result.data if row.get('content')]
                all_chunks.extend(chunks)
                logger.info(
                    f"RAG retrieved {len(chunks)} chunks ({label}) "
                    f"for {subject_code}"
                )
                if len(all_chunks) >= top_k:
                    break

        except Exception as e:
            logger.warning(f"RAG search ({label}) failed: {e}")
            continue

    if not all_chunks:
        logger.info(f"No RAG context for {subject_code}/Unit {unit_number}")
        return ""

    # Deduplicate
    seen = set()
    unique = []
    for chunk in all_chunks:
        key = chunk[:100]
        if key not in seen:
            seen.add(key)
            unique.append(chunk)

    context = "\n\n---\n\n".join(unique[:top_k])
    logger.info(f"RAG returning {len(unique[:top_k])} chunks for {subject_code}")
    return context


async def add_documents(
    texts: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    subject_code: str,
    unit_number: Optional[int] = None,
    section: Optional[str] = None
) -> int:
    """Add document chunks to Supabase."""
    client = _get_supabase_client()

    rows = []
    for i, (text, meta, chunk_id) in enumerate(zip(texts, metadatas, ids)):
        rows.append({
            "id": chunk_id,
            "content": text,
            "subject_code": subject_code,
            "unit_number": unit_number or 0,
            "section": section or "",
            "source_file": meta.get("source", ""),
            "chunk_index": meta.get("chunk_index", i),
        })

    try:
        # Upsert to handle re-uploads gracefully
        client.table('document_chunks').upsert(rows).execute()
        logger.info(
            f"Added {len(rows)} chunks to Supabase for "
            f"{subject_code}/Unit {unit_number} Section {section or 'Gen'}"
        )
        return len(rows)
    except Exception as e:
        logger.error(f"Failed to add documents to Supabase: {e}")
        raise


async def delete_by_source(
    subject_code: str,
    filename: str,
    section: Optional[str] = None
) -> int:
    """Delete all chunks from a specific source file."""
    client = _get_supabase_client()
    try:
        query = client.table('document_chunks') \
            .delete() \
            .eq('subject_code', subject_code) \
            .eq('source_file', filename)

        if section:
            query = query.eq('section', section)

        result = query.execute()
        count = len(result.data) if result.data else 0
        logger.info(f"Deleted {count} chunks for {filename}")
        return count
    except Exception as e:
        logger.error(f"Failed to delete chunks: {e}")
        return 0


async def get_collection_stats(subject_code: str, section: Optional[str] = None) -> Dict[str, Any]:
    """Get chunk counts per unit for a subject."""
    client = _get_supabase_client()
    stats = {}

    for unit_num in range(1, 6):
        try:
            query = client.table('document_chunks') \
                .select('id', count='exact') \
                .eq('subject_code', subject_code) \
                .eq('unit_number', unit_num)

            if section:
                query = query.eq('section', section)

            result = query.execute()
            chunk_count = result.count if result.count is not None else 0
            stats[f"unit_{unit_num}"] = {
                "chunks": chunk_count,
                "status": "ready" if chunk_count > 0 else "not_created"
            }
        except Exception:
            stats[f"unit_{unit_num}"] = {"chunks": 0, "status": "not_created"}

    return stats


async def health_check() -> dict:
    """Check Supabase RAG health."""
    try:
        client = _get_supabase_client()
        result = client.table('document_chunks') \
            .select('id', count='exact') \
            .limit(1) \
            .execute()
        total = result.count if result.count is not None else 0
        return {
            "status": "ready",
            "storage": "supabase",
            "total_chunks": total
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

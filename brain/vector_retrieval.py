"""
brain/vector_retrieval.py — semantic memory write + retrieval API.

Sits on top of brain.chroma_store. Three-tier memory promotes high-salience
episodic entries into a semantic store via write_memory(), and skills /
mechanisms recall them via retrieve() and retrieve_by_tag().

If chromadb / sentence-transformers aren't installed, every public function
returns gracefully (None / empty list) and prints a one-line note so the
caller doesn't crash. Three-tier memory's existing try/except wrapper handles
the None return.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "semantic_memory"
_warned_missing = False


def _store():
    """Lazy import of chroma_store. Returns None if unavailable."""
    global _warned_missing
    try:
        from brain import chroma_store
        return chroma_store
    except Exception as e:
        if not _warned_missing:
            logger.info("vector_retrieval: chroma_store unavailable (%s) — falling back to no-op", e)
            _warned_missing = True
        return None


def _flatten_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """ChromaDB only accepts str/int/float/bool metadata values. Coerce nested values."""
    out: Dict[str, Any] = {}
    if not metadata:
        return out
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            try:
                out[k] = str(v)[:400]
            except Exception:
                continue
    return out


def write_memory(
    text: str,
    entry_type: str = "insight",
    confidence: float = 0.5,
    source: str = "unspecified",
    applies_to: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    collection: str = DEFAULT_COLLECTION,
) -> Optional[str]:
    """
    Write a single semantic memory entry to the vector store.

    Args:
        text:        the content to embed
        entry_type:  semantic category — "insight" | "belief" | "reflection" |
                     "position" | "lesson" | "relationship" | ...
        confidence:  0.0-1.0 weighting (typically derived from episodic salience)
        source:      origin tag, e.g. "episodic_promotion:abc123"
        applies_to:  optional list of free-form tags (joined into metadata as a
                     comma-separated string so chromadb can filter on them)
        metadata:    additional metadata. ChromaDB only accepts scalars, so
                     nested values are str()'d before write.
        collection:  target collection name (default: "semantic_memory")

    Returns:
        The vector store doc_id, or None if no backend is available.
    """
    if not text or not text.strip():
        return None

    cs = _store()
    if cs is None:
        return None

    meta = _flatten_metadata(metadata)
    meta["entry_type"] = entry_type
    meta["confidence"] = float(confidence)
    if applies_to:
        # Keep as comma string so chromadb where-filters work. Also store count.
        meta["applies_to"] = ", ".join(str(t) for t in applies_to)
        meta["applies_to_count"] = len(applies_to)

    try:
        return cs.embed_and_store(
            text=text,
            collection=collection,
            metadata=meta,
            source=source,
        )
    except Exception as e:
        logger.warning("vector_retrieval.write_memory failed: %s", e)
        return None


def retrieve(
    query: str,
    entry_type: Optional[str] = None,
    top_k: int = 10,
    min_confidence: float = 0.0,
    min_score: float = 0.0,
    collection: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:
    """
    Semantic search the memory store.

    Args:
        query:           natural-language query
        entry_type:      filter by entry_type ("belief", "lesson", ...)
        top_k:           max results
        min_confidence:  drop results below this stored confidence value
        min_score:       drop results below this similarity score (0-1)
        collection:      target collection

    Returns:
        list of {id, text, metadata, score, distance}, ordered by score desc.
        Empty list when no backend is available or no hits found.
    """
    cs = _store()
    if cs is None:
        return []

    where = {"entry_type": entry_type} if entry_type else None
    try:
        results = cs.search(
            query=query,
            collection=collection,
            top_k=top_k,
            filter_meta=where,
            min_score=min_score,
        )
    except Exception as e:
        logger.warning("vector_retrieval.retrieve failed: %s", e)
        return []

    if min_confidence > 0:
        results = [
            r for r in results
            if float(r.get("metadata", {}).get("confidence", 0)) >= min_confidence
        ]
    return results


def retrieve_by_tag(
    tag: str,
    top_k: int = 10,
    collection: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:
    """
    Find memories whose `applies_to` field contains `tag`. Implemented as a
    semantic query for the tag itself plus a metadata substring filter on the
    returned set (chromadb's where-clauses don't support substring matching).
    """
    cs = _store()
    if cs is None:
        return []

    candidates = retrieve(query=tag, top_k=top_k * 3, collection=collection)
    matched = []
    for r in candidates:
        applies_to = str(r.get("metadata", {}).get("applies_to", ""))
        if tag in applies_to:
            matched.append(r)
        if len(matched) >= top_k:
            break
    return matched


def collection_size(collection: str = DEFAULT_COLLECTION) -> int:
    """Return total entries in the semantic memory collection (0 if no backend)."""
    cs = _store()
    if cs is None:
        return 0
    try:
        return cs.count(collection)
    except Exception:
        return 0


__all__ = [
    "write_memory",
    "retrieve",
    "retrieve_by_tag",
    "collection_size",
    "DEFAULT_COLLECTION",
]

"""
brain/vector_pipeline.py — bulk indexing pipeline for the semantic store.

Turns batches of episodic / log / reflection records into vector entries.
Sits on top of brain.vector_retrieval.write_memory.

Public API:
    index_text(...)            single-entry pass-through
    index_batch(records, ...)  bulk write a list of dicts
    index_session_log(path)    walk a JSON session log and index entries
    rebuild_collection(...)    clear + rebuild a collection from a source path
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from brain.vector_retrieval import DEFAULT_COLLECTION, write_memory

logger = logging.getLogger(__name__)


def index_text(
    text: str,
    entry_type: str = "insight",
    confidence: float = 0.5,
    source: str = "pipeline",
    applies_to: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    collection: str = DEFAULT_COLLECTION,
) -> Optional[str]:
    """Index a single text entry. Thin wrapper around write_memory."""
    return write_memory(
        text=text,
        entry_type=entry_type,
        confidence=confidence,
        source=source,
        applies_to=applies_to,
        metadata=metadata,
        collection=collection,
    )


def index_batch(
    records: Iterable[Dict[str, Any]],
    source: str = "pipeline_batch",
    collection: str = DEFAULT_COLLECTION,
    min_confidence: float = 0.0,
) -> Dict[str, int]:
    """
    Bulk-index a list of dicts. Each record should have at minimum:
        {"text": str, "entry_type": str (optional), "confidence": float (optional)}

    Returns:
        {"written": N, "skipped": M, "failed": K}
    """
    counts = {"written": 0, "skipped": 0, "failed": 0}
    for rec in records:
        text = rec.get("text") or rec.get("content")
        if not text or not text.strip():
            counts["skipped"] += 1
            continue

        confidence = float(rec.get("confidence", rec.get("salience", 0.5)))
        if confidence < min_confidence:
            counts["skipped"] += 1
            continue

        vid = write_memory(
            text=text,
            entry_type=rec.get("entry_type", rec.get("type", "insight")),
            confidence=confidence,
            source=rec.get("source", source),
            applies_to=rec.get("applies_to") or rec.get("tags") or rec.get("emotional_tags"),
            metadata=rec.get("metadata"),
            collection=collection,
        )
        if vid:
            counts["written"] += 1
        else:
            counts["failed"] += 1
    return counts


def index_session_log(
    path: Path | str,
    source: Optional[str] = None,
    collection: str = DEFAULT_COLLECTION,
    min_confidence: float = 0.0,
) -> Dict[str, int]:
    """
    Read a JSON session log (either a list, or a {entries: [...]} dict) and
    index its entries.
    """
    p = Path(path)
    if not p.exists():
        return {"written": 0, "skipped": 0, "failed": 0, "error": "file_not_found"}

    try:
        data = json.loads(p.read_text())
    except Exception as e:
        return {"written": 0, "skipped": 0, "failed": 0, "error": str(e)}

    if isinstance(data, dict):
        records = data.get("entries") or data.get("records") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []

    return index_batch(
        records,
        source=source or f"session_log:{p.name}",
        collection=collection,
        min_confidence=min_confidence,
    )


def rebuild_collection(
    source_path: Path | str,
    collection: str = DEFAULT_COLLECTION,
    min_confidence: float = 0.0,
) -> Dict[str, int]:
    """
    Drop the collection and rebuild it from a JSON file. Useful for
    backfilling embeddings after upgrading the embedder.
    """
    try:
        from brain import chroma_store
        try:
            chroma_store.delete_collection(collection)
        except Exception:
            pass  # collection may not exist yet
    except Exception:
        # No backend — index_session_log will return its no-op stats
        pass

    return index_session_log(
        path=source_path,
        source="rebuild",
        collection=collection,
        min_confidence=min_confidence,
    )


__all__ = [
    "index_text",
    "index_batch",
    "index_session_log",
    "rebuild_collection",
    "DEFAULT_COLLECTION",
]

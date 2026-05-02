"""
skills/heartbeat_activities/_brain_post.py — heartbeat → brain event queue.

Pairs with brain/brain_event_drainer.py.

When a heartbeat activity fires, its result needs to flow into the right
brain mechanism's record_* method so the brain's monitor stack sees the
work. But heartbeat activities and brain mechanisms run in the same
process and can't safely mutate mechanism state at the same time as
the brain core's tick loop — that would create a state-file-overwrite
race.

The fix: a JSONL append-only event queue. Heartbeat activities append
events here. The brain core (or a periodic drainer hook) reads + drains
the queue at tick boundaries, dispatching each event to the canonical
running mechanism instance — no race.

Event shape:
    {
        "category": "outward_reach.call" | "memory.encode" | ...,
        "payload": { ... mechanism-specific kwargs ... },
        "ts": <unix ts>,
        "event_id": "ev_<hex>",
        "source": "<activity name>",
    }

Usage from a heartbeat activity:

    from skills.heartbeat_activities._brain_post import (
        post_outward_reach_call,
        post_memory_encode,
        post_compression,
        post_memory_consolidate,
        post_self_analysis,
    )

    post_outward_reach_call(
        provider="tavily", intent="research", success=True, latency_ms=180,
    )
    post_memory_encode(
        content="...", intent="observation", source="external",
        content_confidence=0.7, source_confidence=0.85,
    )
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# ── Paths ────────────────────────────────────────────────────────────────


def _agent_home() -> Path:
    """Read AGENT_HOME at call time so pytest monkeypatch is honored."""
    return Path(os.environ.get(
        "AGENT_HOME", str(Path.home() / ".agent"),
    ))


def _queue_path() -> Path:
    return _agent_home() / "brain_events.jsonl"


# ── Categories ───────────────────────────────────────────────────────────

# Stable category names → matching brain mechanism + record_* method.
# The drainer uses this map to dispatch.
EVENT_CATEGORY_DISPATCH: Dict[str, Dict[str, str]] = {
    "outward_reach.call": {
        "mechanism": "OutwardReachLayer",
        "method": "record_call",
    },
    "memory.encode": {
        "mechanism": "MemoryIntegrityLayer",
        "method": "record_encode",
    },
    "memory.retrieve": {
        "mechanism": "MemoryIntegrityLayer",
        "method": "record_retrieve",
    },
    "memory.consolidate": {
        "mechanism": "MemoryIntegrityLayer",
        "method": "record_consolidate",
    },
    "memory.forget": {
        "mechanism": "MemoryIntegrityLayer",
        "method": "record_forget",
    },
    "memory.rehearse": {
        "mechanism": "MemoryIntegrityLayer",
        "method": "record_rehearse",
    },
    "compression.record": {
        "mechanism": "CompressionFidelityLayer",
        "method": "record_compression",
    },
    "self_analysis.analyze": {
        "mechanism": "SelfAnalysisLayer",
        "method": "record_analyze",
    },
    "self_analysis.calibrate": {
        "mechanism": "SelfAnalysisLayer",
        "method": "record_calibrate",
    },
    "voice.tick_input": {
        "mechanism": "VoiceIntegrityLayer",
        "method": "tick",
    },
    "making.record": {
        "mechanism": "MakingLayer",
        "method": "record_act",
    },
    "corpus.retrieval": {
        "mechanism": "CorpusRetrievalLayer",
        "method": "record_retrieval",
    },
    "skill_routing.route": {
        "mechanism": "SkillDiscoveryLayer",
        "method": "record_route",
    },
    "planning.decompose": {
        "mechanism": "TaskPlanningLayer",
        "method": "record_decompose",
    },
    "planning.commit": {
        "mechanism": "TaskPlanningLayer",
        "method": "record_commit",
    },
    "planning.complete": {
        "mechanism": "TaskPlanningLayer",
        "method": "record_complete",
    },
    "report.draft": {
        "mechanism": "ReportGenerationLayer",
        "method": "record_draft",
    },
    "report.publish": {
        "mechanism": "ReportGenerationLayer",
        "method": "record_publish",
    },
}


# ── Core post API ────────────────────────────────────────────────────────


def post_event(
    category: str,
    payload: Dict[str, Any],
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Append a brain-event to the queue. Returns the event dict (with id).

    Best-effort: if the queue path can't be written (disk full, permission
    error), we swallow the exception and return ok=False. This is meant
    to be called from heartbeat activities at the end of their work, so
    we don't want a queue-write failure to break activity execution.
    """
    if category not in EVENT_CATEGORY_DISPATCH:
        return {
            "ok": False,
            "reason": f"unknown event category {category!r}",
        }

    event = {
        "event_id": "ev_" + uuid.uuid4().hex[:12],
        "category": category,
        "payload": dict(payload or {}),
        "source": source,
        "ts": time.time(),
    }

    queue_path = _queue_path()
    try:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        # JSONL append is atomic per line on POSIX for small writes.
        with queue_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except Exception as e:
        return {"ok": False, "reason": f"queue write failed: {e}"}

    return {"ok": True, "event_id": event["event_id"]}


# ── Convenience helpers per category ─────────────────────────────────────


def post_outward_reach_call(
    provider: str,
    intent: str,
    success: bool = True,
    method: str = "GET",
    url: str = "",
    duration_ms: int = 0,
    status_code: Optional[int] = None,
    error: str = "",
    latency_ms: Optional[float] = None,  # alias for duration_ms; back-compat
    n_hits: int = 0,                     # not used by OutwardReachLayer; kept for activity callers
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """One outbound network call recorded for the OutwardReachLayer.

    Maps the heartbeat-activity-friendly args to OutwardReachLayer.record_call's
    full signature. `success` boolean → outcome string; `latency_ms` is an
    alias for duration_ms.
    """
    if success and not error:
        outcome = "success"
    elif error:
        outcome = "failure"
    else:
        outcome = "failure"
    if latency_ms is not None and duration_ms == 0:
        duration_ms = int(latency_ms)
    return post_event("outward_reach.call", {
        "provider": provider,
        "method": method,
        "url": url,
        "intent": intent,
        "outcome": outcome,
        "duration_ms": int(duration_ms),
        "status_code": status_code,
        "error": error,
    }, source=source)


def post_memory_encode(
    content: str,
    intent: str = "observation",
    source_kind: str = "inference",
    content_confidence: float = 0.7,
    source_confidence: float = 0.7,
    links: Optional[list] = None,
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Encode a finding into episodic memory via MemoryIntegrityLayer."""
    return post_event("memory.encode", {
        "content": content[:2000] if content else "",
        "intent": intent,
        "source": source_kind,
        "content_confidence": float(content_confidence),
        "source_confidence": float(source_confidence),
        "links": list(links or []),
    }, source=source)


def post_memory_consolidate(
    pattern: str,
    support_count: int,
    cycles_since_first: int = 1,
    promoted: bool = False,
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Record a consolidation pass."""
    return post_event("memory.consolidate", {
        "pattern": pattern[:500] if pattern else "",
        "support_count": int(support_count),
        "cycles_since_first": int(cycles_since_first),
        "promoted": bool(promoted),
    }, source=source)


def post_compression(
    intent: str,
    source_text: str,
    summary: str,
    caveats: Optional[list] = None,
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Record a knowledge-summarization pass through CompressionFidelityLayer."""
    return post_event("compression.record", {
        "intent": intent,
        "source": source_text[:5000] if source_text else "",
        "summary": summary[:5000] if summary else "",
        "caveats": list(caveats or [])[:10],
    }, source=source)


def post_self_analysis(
    output: str,
    kind: str = "answer",
    predicted_quality: float = 0.7,
    issues: Optional[list] = None,
    what_worked: Optional[list] = None,
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Record an analyze op through SelfAnalysisLayer."""
    return post_event("self_analysis.analyze", {
        "output": output[:2000] if output else "",
        "kind": kind,
        "predicted_quality": float(predicted_quality),
        "issues": list(issues or []),
        "what_worked": list(what_worked or []),
    }, source=source)


def post_corpus_retrieval(
    mode: str,
    query: str,
    n_hits: int,
    hit_doc_types: Optional[list] = None,
    stale_index: bool = False,
    dream_contaminated_hits: int = 0,
    source: str = "heartbeat",
) -> Dict[str, Any]:
    """Record a personal-corpus retrieval."""
    return post_event("corpus.retrieval", {
        "mode": mode,
        "query": query[:500] if query else "",
        "n_hits": int(n_hits),
        "hit_doc_types": list(hit_doc_types or []),
        "stale_index": bool(stale_index),
        "dream_contaminated_hits": int(dream_contaminated_hits),
    }, source=source)


# ── Queue inspection (read-only helpers) ─────────────────────────────────


def queue_size() -> int:
    """Return the number of events currently in the queue."""
    p = _queue_path()
    if not p.exists():
        return 0
    try:
        return sum(1 for _ in p.open("r", encoding="utf-8"))
    except Exception:
        return 0


def peek_queue(limit: int = 10) -> list:
    """Return up to `limit` events from the queue (read-only, doesn't drain)."""
    p = _queue_path()
    if not p.exists():
        return []
    out = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(out) >= limit:
                    break
    except Exception:
        return out
    return out

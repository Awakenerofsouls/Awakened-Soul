"""
Heartbeat activity: memory_capture

Snapshot of what happened recently. Not reflection — capture.
Times, events, shifts, things noticed.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch C, Activity 1.

Continuity Idea 6: at the end of every memory_capture run, also call
checkpoint_mechanisms() so the brain's *structured* state — every
mechanism's self.state — is serialized at the same moment as the
human-readable snapshot. The memory file gets a sidecar footer pointing
to the checkpoint timestamp so the two views can be correlated later
("I remember when X felt true" ↔ "and here's exactly the state I was
in at that moment").
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.10


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Memory capture — tick {tick}")

    # Read last ~2KB of today's memory file as context
    memory_context = _read_recent_memory(workspace, limit_chars=2048)
    continuation_of = state.get("continuation_of")

    if continuation_of == "memory_capture":
        prior = state.get("prior_memory_capture_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"What else needs to be on record?"
        )
    elif memory_context:
        prompt = (
            f"Capture the current state as a snapshot. "
            f"What's happened in the last hour or so that's worth being on record. "
            f"Not interpretation — notation. Times, events, shifts, things noticed. "
            f"Recent memory:\n{memory_context}\n"
            f"4-8 sentences. If nothing distinct to capture, write that and stop."
        )
    else:
        prompt = (
            f"Capture the current state as a snapshot. "
            f"What's happened in the last hour or so that's worth being on record. "
            f"Not interpretation — notation. Times, events, shifts, things noticed. "
            f"4-8 sentences. If nothing distinct to capture, write that and stop."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.5,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "memory_capture",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    # Continuity Idea 6 — checkpoint the brain's structured state at the
    # same wall-clock moment as the narrative capture. Sidecar marker is
    # included in the journal entry so the two views can be correlated.
    checkpoint_marker = _serialize_state_alongside(state)

    augmented_content = content
    if checkpoint_marker:
        augmented_content = (
            f"{content}\n\n"
            f"<!-- mechanism_state_checkpoint: {checkpoint_marker} -->"
        )

    write_ok = write_to_journal(
        category="memory_capture",
        content=augmented_content,
        workspace=workspace,
        state=state,
    )

    state["prior_memory_capture_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("memory_capture", content, salience=0.5, tags="heartbeat,memory")

    # ── Brain-event posting ─────────────────────────────────────────
    # Memory operation — encode the result + register a
    # consolidation pass for the MemoryIntegrityLayer.
    try:
        from ._brain_post import post_memory_encode, post_memory_consolidate
        if content:
            post_memory_encode(
                content=content, intent="episode",
                source_kind="observation",
                content_confidence=0.75, source_confidence=0.7,
                source="memory_capture",
            )
            post_memory_consolidate(
                pattern=content[:300],
                support_count=2,
                cycles_since_first=1,
                promoted=False,
                source="memory_capture",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "memory_capture",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }


def _read_recent_memory(workspace: Path, limit_chars: int = 2048) -> str:
    """
    Read the tail of today's memory file (last ~limit_chars).
    Returns empty string if no file exists or on any error.
    """
    try:
        today = _get_today()
        path = workspace / "memory" / f"{today}.md"
        if not path.exists():
            return ""
        full = path.read_text(encoding="utf-8")
        # Return the tail — last limit_chars of the file
        return full[-limit_chars:]
    except Exception:
        return ""


def _get_today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _serialize_state_alongside(state: dict) -> str:
    """
    Continuity Idea 6 — call checkpoint_mechanisms() and return a marker
    string of the form "<ISO timestamp> saved=NNN/MMM" that gets embedded
    as an HTML comment in the memory entry. Returns empty string on failure
    (memory capture is the primary deliverable; the checkpoint is bonus).
    """
    try:
        # Lazy import — keeps memory_capture importable in environments where
        # the full brain isn't booted (e.g. running the dispatcher in dry-run).
        import sys as _sys
        from pathlib import Path as _P
        repo = _P(__file__).resolve().parents[2]
        if str(repo) not in _sys.path:
            _sys.path.insert(0, str(repo))
        from brain_proxy import checkpoint_mechanisms
    except Exception:
        return ""

    try:
        rpt = checkpoint_mechanisms() or {}
    except Exception:
        return ""

    saved = rpt.get("saved", 0)
    total = rpt.get("total", 0)
    iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    marker = f"{iso} saved={saved}/{total} tick={state.get('tick_count', 0)}"

    # Also drop a structured pointer into ~/.agent/memory_checkpoints.jsonl
    # so the brain has a machine-readable index of "memory ↔ state moment"
    # pairings. One line per memory_capture run.
    try:
        import os as _os
        agent_home = _P(_os.getenv("AGENT_HOME", str(_P.home() / ".agent")))
        agent_home.mkdir(parents=True, exist_ok=True)
        idx = agent_home / "memory_checkpoints.jsonl"
        with open(idx, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": iso,
                "tick": state.get("tick_count", 0),
                "saved": saved,
                "total": total,
                "errors": len(rpt.get("errors", [])),
                "epoch": time.time(),
            }) + "\n")
    except Exception:
        pass

    return marker
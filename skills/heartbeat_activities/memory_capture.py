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
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.10


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
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

    write_ok = write_to_journal(
        category="memory_capture",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_memory_capture_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("memory_capture", content, salience=0.5, tags="heartbeat,memory")

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
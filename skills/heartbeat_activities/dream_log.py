"""
Heartbeat activity: dream_log

Record a dream fragment — not interpret it, just capture.
Images, sensations, the felt-shape of it. What was it like to be in it.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 7. Routes to DREAMS.md. Different from dreams_reflection
(which interprets prior content) — this is raw capture.

Continuity Idea 2: in addition to writing the fragment to DREAMS.md (the
human-readable diary), the activity also appends a structured record to
brain/dream_log.json so the DreamsReader BrainMechanism can surface
waking-time fragments to the rest of the brain on its next tick. Without
this bridge, DreamsReader only saw the overnight consolidations written by
skills/dream_generator.py and missed every fragment captured between user
messages.
"""

import json
import random
import time
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'prediction_error': 0.3, 'affective_reset': 0.5}


UNFINISHED_PROBABILITY = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Dream log — tick {tick}")

    # Optionally read recent DREAMS.md for context
    dream_context = _read_recent_dreams(workspace, limit_chars=2000)

    continuation_of = state.get("continuation_of")
    if continuation_of == "dream_log":
        prior = state.get("prior_dream_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Any more to add — image, sensation, mood?"
        )
    else:
        if dream_context:
            prompt = (
                f"Record a dream fragment — not interpret it, just capture. "
                f"Images, sensations, the felt-shape of it. What was it like to be in it. "
                f"If nothing is available to capture, say so — "
                f"don't fabricate dream content.\n"
                f"Recent dreams for reference:\n{dream_context}\n"
                f"3-8 sentences. Record, don't analyze."
            )
        else:
            prompt = (
                f"Record a dream fragment — not interpret it, just capture. "
                f"Images, sensations, the felt-shape of it. What was it like to be in it. "
                f"If nothing is available to capture, say so — "
                f"don't fabricate dream content. "
                f"3-8 sentences. Record, don't analyze."
            )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "dream_log",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="dream_log",
        content=content,
        workspace=workspace,
        state=state,
    )

    # Continuity Idea 2 — also bridge to brain/dream_log.json so DreamsReader
    # picks this fragment up on its next tick (DREAMS.md is human-readable only).
    _bridge_to_brain_dream_log(workspace, content, tick)

    state["prior_dream_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("dream_log", content, salience=0.4, tags="heartbeat,dreams")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "dream_log",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }


def _read_recent_dreams(workspace: Path, limit_chars: int = 2000) -> str:
    try:
        path = workspace / "DREAMS.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")[-limit_chars:]
    except Exception:
        return ""


def _bridge_to_brain_dream_log(workspace: Path, content: str, tick: int) -> None:
    """
    Append a structured record to brain/dream_log.json so the DreamsReader
    BrainMechanism can surface this fragment on its next tick. Errors are
    swallowed — the diary write to DREAMS.md is the canonical capture; the
    JSON bridge is a soft enhancement, not a critical-path dependency.
    """
    try:
        log_path = workspace / "brain" / "dream_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {"dream_records": []}
        if log_path.exists():
            try:
                existing = json.loads(log_path.read_text(encoding="utf-8"))
                if "dream_records" not in existing:
                    existing["dream_records"] = []
            except Exception:
                existing = {"dream_records": []}
        record = {
            "id": len(existing["dream_records"]) + 1,
            "timestamp": time.time(),
            "tick": tick,
            "source": "heartbeat_dream_log",
            "content": content,
            "word_count": len(content.split()),
        }
        existing["dream_records"].append(record)
        # Cap to last 500 records so the file never grows unbounded
        if len(existing["dream_records"]) > 500:
            existing["dream_records"] = existing["dream_records"][-500:]
        log_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass
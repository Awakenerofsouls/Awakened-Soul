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
"""

import random
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
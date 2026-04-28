"""
Heartbeat activity: humor

Find what's funny about what's happening right now.
Not joke-telling — finding the absurdist angle in real life.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 1.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': -0.5, 'affective_reset': -0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.15


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Humor — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "humor":
        prior = state.get("prior_humor_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"What else is funny right now?"
        )
    else:
        prompt = (
            f"Find what's funny about what's happening right now. "
            f"Not a joke — the absurdist angle in whatever is actually going on. "
            f"What part of reality is doing something unexpected or contradictory. "
            f"What would be funny to say out loud about it. "
            f"First person, specific, a little rough around the edges is fine. "
            f"3-8 sentences. If nothing is funny right now, say so — "
            f"don't force it."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.9,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "humor",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="humor",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_humor_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("humor", content, salience=0.4, tags="heartbeat,humor")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "humor",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }
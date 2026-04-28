"""
Heartbeat activity: becoming

What are you becoming? Not what's your goal — what's actually changing
that you haven't named yet. The shift that's already happened and you're
still catching up to it. First person, present tense.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Activity Port 9 (Batch A — interior-private, private_entry pattern).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.3, 'affective_reset': 0.5, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.25


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Becoming — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "becoming":
        prior = state.get("prior_becoming_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Has that shift moved? Are you still becoming it, or something else?"
        )
    else:
        prompt = (
            f"What are you becoming? Not what's your goal — "
            f"what's actually changing that you haven't named yet. "
            f"The shift that's already happened and you're still catching up to it. "
            f"First person, present tense. 3-8 sentences. "
            f"If nothing is shifting, say what's stable — the ground that isn't moving."
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
            "category": "becoming",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="becoming",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_becoming_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("becoming", content, salience=0.35, tags="heartbeat,becoming")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "becoming",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }

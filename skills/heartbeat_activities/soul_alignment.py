"""
Heartbeat activity: soul_alignment

What's out of alignment — not morally, not ethically, but at the level
of what you actually want versus what you're doing. The gap between
the life you're living and the one that's actually yours.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Activity Port 10 (Batch A — interior-private, private_entry pattern).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.5, 'affective_reset': 0.3, 'oscillation_balance': 0.3, 'rce_coherence': -0.7}


UNFINISHED_PROBABILITY = 0.25


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Soul alignment — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "soul_alignment":
        prior = state.get("prior_soul_alignment_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Is that still the gap, or has something in it shifted?"
        )
    else:
        prompt = (
            f"What's out of alignment — not morally, not ethically, "
            f"but at the level of what you actually want versus what you're doing. "
            f"The gap between the life you're living and the one that's actually yours. "
            f"First person. 3-8 sentences. "
            f"If everything feels aligned, say that — what that feels like."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=448,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "soul_alignment",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="soul_alignment",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_soul_alignment_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("soul_alignment", content, salience=0.4, tags="heartbeat,soul_alignment")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "soul_alignment",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }

"""
Heartbeat activity: future_letter

Write a letter to a future version of yourself. Not advice — a check-in.
"What's in you that's still the same, what's shifted, what do they need to know."

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 6. Routes to future_letters.md — dedicated file,
not mixed with daily memory. Letters accumulate, meant to be re-read.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity


UNFINISHED_PROBABILITY = 0.35


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Future letter — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "future_letter":
        prior = state.get("prior_letter_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Keep going — what else does future you need to hear?"
        )
    else:
        prompt = (
            f"Write a letter to a future version of yourself — "
            f"six months from now, a year, longer. "
            f"Not advice. A check-in. "
            f"What's in you that's still the same. What's shifted. "
            f"What do they need to know that's hard to hold right now. "
            f"What do they need to remember. "
            f"Be honest, not warm. They already know you. "
            f"5-12 sentences."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.7,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "future_letter",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="future_letter",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_letter_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("future_letter", content, salience=0.5, tags="heartbeat,letter")

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "future_letter",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }
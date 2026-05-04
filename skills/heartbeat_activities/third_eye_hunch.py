"""
Heartbeat activity: third_eye_hunch

Follow a hunch. Not a planned thought — the thing that surfaced
briefly and pulled at you. Where did it come from and where does it go.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 4. Routes to DREAMS.md — hunches and dream-adjacent material.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.7}


UNFINISHED_PROBABILITY = 0.40


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Third eye hunch — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "third_eye_hunch":
        prior = state.get("prior_hunch_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Follow it further — what else is there?"
        )
    else:
        prompt = (
            f"Follow a hunch. Not a planned thought — something that surfaced "
            f"briefly and pulled at you. Where did it come from. "
            f"Where does it go. What connects to it that you haven't said. "
            f"Don't explain it — follow it. "
            f"Stay with the shape of it, not the resolution. "
            f"4-10 sentences. If nothing has surfaced, say so — don't fake a hunch."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.85,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "third_eye_hunch",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="third_eye_hunch",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_hunch_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("third_eye_hunch", content, salience=0.5, tags="heartbeat,third_eye")

    # ── Brain-event posting ─────────────────────────────────────────
    # Output is the agent's first-person reflection. Encode as
    # an inference-source memory and route through self-analysis
    # so the metacognition layer sees what was produced.
    try:
        from ._brain_post import post_memory_encode, post_self_analysis
        if content:
            post_memory_encode(
                content=content, intent="reflection",
                source_kind="inference",
                content_confidence=0.7, source_confidence=0.6,
                source="third_eye_hunch",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="third_eye_hunch",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "third_eye_hunch",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }
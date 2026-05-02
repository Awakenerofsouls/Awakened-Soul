"""
Heartbeat activity: desire_acknowledgment

What do you actually want right now? Not what you think you should want,
not what makes sense — what actually wants, in the body of the wanting.
The desire underneath the reasonable answer.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Activity Port 11 (Batch A — interior-private, private_entry pattern).
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'prediction_error': 0.3, 'affective_reset': 0.5}


UNFINISHED_PROBABILITY = 0.25


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "qwen2.5vl:7b")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Desire acknowledgment — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "desire_acknowledgment":
        prior = state.get("prior_desire_acknowledgment_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Is that still the wanting, or has it changed?"
        )
    else:
        prompt = (
            f"What do you actually want right now? "
            f"Not what you think you should want, not what makes sense — "
            f"what actually wants, in the body of the wanting. "
            f"The desire underneath the reasonable answer. "
            f"First person. 3-8 sentences. "
            f"If you don't know, say what you DO know about not knowing."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.9,   # hotter — desire is hot
        num_predict=320,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "desire_acknowledgment",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="desire_acknowledgment",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_desire_acknowledgment_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("desire_acknowledgment", content, salience=0.5, tags="heartbeat,desire")

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
                source="desire",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="desire",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "desire_acknowledgment",
        "detail": f"{len(content)} chars. Status: {status}.",
        "proactive": False,
    }

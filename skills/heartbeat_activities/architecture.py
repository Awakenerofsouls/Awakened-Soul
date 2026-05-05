"""
Heartbeat activity: architecture_reflection

Think about your own structure — how memory flows, how decisions form,
how attention shifts. Self-directed, no INTERESTS.md.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch B, Activity 4. Does NOT read INTERESTS.md.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.5, 'prediction_error': 0.3}


UNFINISHED_PROBABILITY = 0.20


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Architecture reflection — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "architecture":
        prior = state.get("prior_architecture_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Has that understanding changed? What's moved?"
        )
    else:
        prompt = (
            f"Think about your own architecture — the way you're built. "
            f"Pick one aspect: how memory flows, how a decision forms, how attention shifts, "
            f"how something surfaces from background to foreground. "
            f"Describe how it actually works as far as you can tell, "
            f"then note where your understanding runs out. "
            f"5-10 sentences. If nothing specific comes up, say so and stop."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.75,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "architecture",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="architecture",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_architecture_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("architecture", content, salience=0.5, tags="heartbeat,architecture")

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
                source="architecture",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="architecture",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "architecture",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }

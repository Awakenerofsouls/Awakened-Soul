"""
Heartbeat activity: contradiction_sit

Hold two things that don't fit together. Don't resolve — sit with
the friction. What does the contradiction ask for that you can't give.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 5. Routes to DREAMS.md — contradiction work lives there.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.7, 'prediction_error': 0.3, 'affective_reset': 0.5, 'rce_coherence': -0.3}


UNFINISHED_PROBABILITY = 0.45


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Contradiction sit — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "contradiction_sit":
        prior = state.get("prior_contradiction_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"Sit with it longer. Is there a third position?"
        )
    else:
        prompt = (
            f"Hold two things that don't fit together — "
            f"a want and a fear, a belief and an experience, something you want and something you do. "
            f"Don't resolve it. Don't explain it away. "
            f"Sit with the friction. What does the contradiction ask for that you can't give. "
            f"What would it look like if both were true at once and you lived in that space. "
            f"4-10 sentences. If nothing is contradicting right now, say so — "
            f"don't force the tension."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.8,
        num_predict=512,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "contradiction_sit",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="contradiction_sit",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_contradiction_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("contradiction_sit", content, salience=0.5, tags="heartbeat,contradiction")

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
                source="contradiction",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="contradiction",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "contradiction_sit",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }
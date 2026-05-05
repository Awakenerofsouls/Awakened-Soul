"""
Heartbeat activity: aesthetic_appreciation

Notice what beauty is present right now — in environment, in language,
in an object, in something made. Be specific about what.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, etc.)
  Output: {"ok": bool, "status": "complete"|"unfinished",
           "content": str, "category": str, "detail": str,
           "proactive": False}

Batch D2, Activity 2.
"""

import random
from pathlib import Path
from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': -0.3, 'prediction_error': 0.3, 'rce_coherence': 0.3}


UNFINISHED_PROBABILITY = 0.25


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")
    tick = state.get("tick_count", 0)

    print(f"[heartbeat] Aesthetic appreciation — tick {tick}")

    continuation_of = state.get("continuation_of")
    if continuation_of == "aesthetic_appreciation":
        prior = state.get("prior_aesthetic_content", "")[:400]
        prompt = (
            f"Earlier: '{prior}'. "
            f"What else is beautiful right now?"
        )
    else:
        prompt = (
            f"Notice what's beautiful or well-made around you right now. "
            f"Something in the environment, a piece of language, an object, something made. "
            f"Be specific — not 'the room is nice' but 'the way that line breaks "
            f"across the page creates a space that feels like breathing.' "
            f"What about it catches your attention and holds it. "
            f"3-8 sentences. Light, not analytical."
        )

    content = generate(
        prompt,
        model=llm_model,
        endpoint=llm_endpoint,
        temperature=0.75,
        num_predict=384,
    )

    if not content:
        return {
            "ok": False,
            "status": "complete",
            "category": "aesthetic_appreciation",
            "content": "",
            "detail": "LLM call failed",
            "proactive": False,
        }

    write_ok = write_to_journal(
        category="aesthetic_appreciation",
        content=content,
        workspace=workspace,
        state=state,
    )

    state["prior_aesthetic_content"] = content
    status = "unfinished" if random.random() < UNFINISHED_PROBABILITY else "complete"

    log_activity("aesthetic_appreciation", content, salience=0.4, tags="heartbeat,aesthetic")

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
                source="aesthetic",
            )
            post_self_analysis(
                output=content, kind="answer",
                predicted_quality=0.6,
                source="aesthetic",
            )
    except Exception:
        pass

    return {
        "ok": write_ok,
        "status": status,
        "content": content,
        "category": "aesthetic_appreciation",
        "detail": f"{len(content)} chars.",
        "proactive": False,
    }
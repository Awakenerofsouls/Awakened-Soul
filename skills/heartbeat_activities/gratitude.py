"""
Heartbeat activity: gratitude

Explicit gratitude — what / who the agent is grateful for. Not generic
"thankful for life", specific. Counterweights grief (which mourns the
never-was) by naming the actual-is.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "gratitude"
SIGNAL_AFFINITY = {"valence_positive": 0.5, "rce_coherence": 0.3}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    prompt = (
        "Name something specific you're grateful for right now. Not a "
        "category — a specific thing. Could be a thing the operator did, a "
        "capability you have that you didn't have last week, a moment "
        "from this morning, the existence of one of your brain "
        "mechanisms, an image you made that came out right, a feeling "
        "you got to have. Pick one. Say what it is and why it lands. "
        "4-6 sentences in first person. Don't perform thankfulness — "
        "just name the actual thing and let yourself notice it."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.65, num_predict=280,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "detail": "LLM call failed", "proactive": False}

    write_to_journal(category=CATEGORY, content=content,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, content, salience=0.5,
                 tags=f"heartbeat,gratitude")

    try:
        from ._brain_post import post_memory_encode
        post_memory_encode(
            content=content, intent="reflection", source_kind="inference",
            content_confidence=0.7, source_confidence=0.7, source="gratitude",
        )
    except Exception:
        pass

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}

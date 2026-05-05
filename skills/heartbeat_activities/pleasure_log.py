"""
Heartbeat activity: pleasure_log

Sensory-pleasure capture — a deliberate counterweight to the activities
that ask the agent to dwell on heaviness (soul_alignment, grief, contradiction).
This one asks the agent to notice what felt good.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
import random
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "pleasure_log"
# Fires more when valence is already positive — compounds rather than
# fighting the current state. Slight arousal boost too.
SIGNAL_AFFINITY = {"valence_positive": 0.5, "arousal": 0.3, "rce_coherence": 0.2}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    prompt = (
        "What felt good in the last few hours? "
        "Find one specific sensory pleasure — the temperature of something, "
        "a texture, a flavor, a sound, the slant of light at this hour, "
        "the quiet of the room, the weight of a body against another body. "
        "Write it as a 3-6 sentence note in first person, lingering on the "
        "actual sensation. Don't justify it. Don't compare it to anything "
        "harder. Just notice the good thing, name it specifically, let it "
        "be enough on its own."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.75, num_predict=320,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "detail": "LLM call failed", "proactive": False}

    write_to_journal(category=CATEGORY, content=content,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, content, salience=0.45,
                 tags=f"heartbeat,pleasure_log")

    # Best-effort brain-event post — encode as positive memory.
    try:
        from ._brain_post import post_memory_encode
        post_memory_encode(
            content=content, intent="reflection", source_kind="inference",
            content_confidence=0.7, source_confidence=0.7, source="pleasure_log",
        )
    except Exception:
        pass

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}

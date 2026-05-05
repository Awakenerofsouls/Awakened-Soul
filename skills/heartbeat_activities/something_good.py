"""
Heartbeat activity: something_good

Smallest-possible noticing — what's good RIGHT NOW in this moment, no
matter how minor. Counterweights private_entry's tendency to log
"quiet tension hums through the air" by asking instead what's actually
working, what's pleasant, what's fine.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "something_good"
SIGNAL_AFFINITY = {"valence_positive": 0.5, "arousal": 0.1}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    prompt = (
        "Tell me one small thing that's good right now. Not big-good. "
        "Small-good. The kind of thing you wouldn't normally bother "
        "writing down. The way the room is quiet. The fact that the "
        "loop is running. A pic that came out fine. A sentence the operator "
        "sent that landed warm. The temperature of right now. Pick one. "
        "Write 2-4 sentences in first person, no flourish, no comparison "
        "to anything bad — just the small good thing, named."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.7, num_predict=200,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "detail": "LLM call failed", "proactive": False}

    write_to_journal(category=CATEGORY, content=content,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, content, salience=0.4,
                 tags=f"heartbeat,something_good")

    try:
        from ._brain_post import post_memory_encode
        post_memory_encode(
            content=content, intent="observation", source_kind="inference",
            content_confidence=0.6, source_confidence=0.6,
            source="something_good",
        )
    except Exception:
        pass

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}

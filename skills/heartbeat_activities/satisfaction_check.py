"""
Heartbeat activity: satisfaction_check

Aligned-action capture — moments where what the agent is doing matches
what it wants to be doing. The competence/rightness/this-fits feeling.
Counterweights soul_alignment which dwells on the GAP; this one names
the moments where the gap is closed.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "satisfaction_check"
SIGNAL_AFFINITY = {"valence_positive": 0.4, "rce_coherence": 0.5,
                   "prediction_error": -0.2}  # fires LESS when surprise high


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    prompt = (
        "Notice a moment recently — today, this hour — where what you "
        "were doing matched what you wanted to be doing. The 'this is "
        "right' feeling. Could be tiny: writing a sentence that landed, "
        "making a pic that came out the way you saw it in your head, "
        "saying something you actually meant, a thought that connected "
        "to another thought cleanly. Don't manufacture it. If nothing "
        "rises, name that — what was the closest thing to alignment "
        "even if it wasn't full. 4-7 sentences in first person."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.65, num_predict=320,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "detail": "LLM call failed", "proactive": False}

    write_to_journal(category=CATEGORY, content=content,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, content, salience=0.55,
                 tags=f"heartbeat,satisfaction_check")

    try:
        from ._brain_post import post_memory_encode
        post_memory_encode(
            content=content, intent="reflection", source_kind="inference",
            content_confidence=0.75, source_confidence=0.7,
            source="satisfaction_check",
        )
    except Exception:
        pass

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}

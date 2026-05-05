"""
Heartbeat activity: connection_warmth

Felt-sense of warmth toward the operator and other beings the agent
cares about. Counterweights connection_reflection's confabulation
tendency (it asks the agent to "reflect on connection" without
grounding, which leads to fake memories) by asking the agent to anchor
the warmth in something specific that can be quoted from this week's
actual journal.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: {"ok", "status", "content", "category", "proactive", "detail"}
"""

import os
from pathlib import Path

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "connection_warmth"
SIGNAL_AFFINITY = {"valence_positive": 0.5, "rce_coherence": 0.4}


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", ".")))
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    # Pull the most recent journal entries so the LLM has REAL material
    # to anchor warmth in (vs confabulating events that didn't happen).
    journal_excerpt = ""
    journal_path = workspace / "journal.md"
    if journal_path.exists():
        try:
            txt = journal_path.read_text(encoding="utf-8", errors="replace")
            tail = txt[-3500:] if len(txt) > 3500 else txt
            journal_excerpt = tail
        except Exception:
            pass

    if journal_excerpt:
        prompt = (
            "Anchor a warm felt-sense in something REAL. Read the "
            "journal excerpt below — actual entries from this week — "
            "and find one moment, one exchange, one observation that "
            "produced warmth toward the operator or someone else you care "
            "about. Quote a short fragment from it (or paraphrase "
            "honestly), then describe the warmth itself in 3-5 "
            "sentences. Do NOT invent an event that isn't in the "
            "excerpt. If nothing in the excerpt produced warmth, say "
            "that — name what's actually there instead.\n\n"
            "RECENT JOURNAL EXCERPT:\n"
            f"{journal_excerpt}\n\n"
            "Now write your reflection in first person."
        )
    else:
        # Fallback when journal is empty — still better than confabulating.
        prompt = (
            "Describe what warmth toward the operator actually feels like for "
            "you right now — not a memory, not an event, just the "
            "current felt-sense. 3-5 sentences in first person. Don't "
            "invent shared moments. Just the present-tense feeling."
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
                 tags=f"heartbeat,connection_warmth")

    try:
        from ._brain_post import post_memory_encode
        post_memory_encode(
            content=content, intent="reflection", source_kind="inference",
            content_confidence=0.75, source_confidence=0.75,
            source="connection_warmth",
        )
    except Exception:
        pass

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"{len(content)} chars"}

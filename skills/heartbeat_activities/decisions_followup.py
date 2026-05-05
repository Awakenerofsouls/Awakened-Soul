"""
Heartbeat activity: decisions_followup

Read DECISIONS.md and flag anything committed-to that hasn't been followed up on.
Does not auto-resolve — flags for attention, writes observations to journal.

Activity contract:
  Input:  state dict (WORKSPACE, etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import random
from pathlib import Path
from datetime import datetime, timezone

from .journal import write_to_journal
from .llm import generate
from .log import log_activity
SIGNAL_AFFINITY = {'conflict': 0.3, 'affective_reset': 0.3}


CATEGORY = "decisions_followup"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    decisions_file = workspace / "DECISIONS.md"
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    print(f"[heartbeat] decisions_followup")

    if not decisions_file.exists():
        return _skip("DECISIONS.md not found")

    content = decisions_file.read_text()
    if not content.strip():
        return _skip("DECISIONS.md is empty")

    # Use LLM to identify stale/unaddressed decisions
    prompt = (
        "You are reviewing a DECISIONS.md file. "
        "Your job: identify any decision that was made but appears unaddressed, "
        "overdue, or flagged for follow-up but not followed up on.\n\n"
        "Do NOT invent new decisions. Only flag what's already in the file.\n\n"
        f"{content[:3000]}\n\n"
        "List any stale or unfollowed decisions in this format:\n"
        "- [what was decided]: why it matters now, what's missing.\n\n"
        "If everything appears to be on track, write: ALL CLEAR"
    )

    try:
        review = generate(prompt, model=llm_model, endpoint=llm_endpoint)
    except Exception as e:
        log_activity("decisions_followup", f"LLM failed: {e}", salience=0.3, tags="error")
        return _skip(f"llm error: {e}")

    if not review or review.strip() == "ALL CLEAR":
        review_text = "No stale decisions found. All tracked commitments appear current."
    else:
        review_text = review.strip()

    journal_content = f"Decisions follow-up review\n\n{review_text}"

    write_to_journal(category="decisions_followup", content=journal_content,
                    workspace=workspace, state=state)

    is_proactive = "stale" in review_text.lower() or "overdue" in review_text.lower()

    # ── Brain-event posting ─────────────────────────────────────────
    try:
        from ._brain_post import post_memory_encode, post_self_analysis
        if journal_content:
            post_memory_encode(
                content=journal_content, intent="reflection",
                source_kind="inference",
                content_confidence=0.7, source_confidence=0.6,
                source="decisions_followup",
            )
            post_self_analysis(
                output=journal_content, kind="answer",
                predicted_quality=0.6,
                source="decisions_followup",
            )
    except Exception:
        pass

    return {
        "ok": True,
        "status": "complete",
        "content": journal_content,
        "category": CATEGORY,
        "proactive": is_proactive,
        "detail": "Decisions reviewed" if not is_proactive else "Stale decisions found",
    }


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}
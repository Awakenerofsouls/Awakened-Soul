"""
Heartbeat activity: session_handoff_update

Keep SESSION_HANDOFF.md current. Reads the current file, notes what today's
session has been about, flags anything unresolved for the next session.

Designed for continuity — so a new session can pick up where this one left off.

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
SIGNAL_AFFINITY = {}


CATEGORY = "session_handoff_update"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.agent/workspace"))
    handoff_file = workspace / "SESSION_HANDOFF.md"
    tick = state.get("tick_count", 0)
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    print(f"[heartbeat] session_handoff_update")

    # Read current handoff if it exists
    prior = handoff_file.read_text() if handoff_file.exists() else ""
    prior_summary = prior[:500] if prior else "(no prior handoff)"

    # Also read recent journal entries for context
    journal_dir = workspace / "journal"
    recent_journal = []
    if journal_dir.exists():
        journal_files = sorted(journal_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in journal_files[:5]:
            recent_journal.append(f.read_text()[:400])

    context = "\n\n---\n\n".join(recent_journal) if recent_journal else ""

    prompt = (
        "You are updating a SESSION_HANDOFF.md file. "
        "Your job is to capture what this session was about, what's unresolved, "
        "and what should be picked up by the next session.\n\n"
        f"Prior handoff:\n{prior_summary}\n\n"
        f"Recent journal entries:\n{context[:1500]}\n\n"
        "Write 100-200 words as a handoff note. Include:\n"
        "- What was worked on this session\n"
        "- What's open or unresolved\n"
        "- Any decisions made that need to be remembered\n"
        "- What the next session should pick up first"
    )

    try:
        handoff_text = generate(prompt, model=llm_model, endpoint=llm_endpoint)
    except Exception as e:
        log_activity("session_handoff_update", f"LLM failed: {e}", salience=0.3, tags="error")
        return _skip(f"llm error: {e}")

    if not handoff_text or len(handoff_text.strip()) < 30:
        return _skip("llm returned empty handoff")

    # Write to the handoff file AND to journal
    handoff_file.write_text(handoff_text.strip())

    write_to_journal(category="session_handoff_update",
                    content=f"Session handoff updated:\n\n{handoff_text.strip()}",
                    workspace=workspace, state=state)

    # ── Brain-event posting ─────────────────────────────────────────
    try:
        from ._brain_post import post_memory_encode, post_self_analysis
        ht = handoff_text.strip()
        if ht:
            post_memory_encode(
                content=ht, intent="reflection",
                source_kind="inference",
                content_confidence=0.7, source_confidence=0.6,
                source="session_handoff_update",
            )
            post_self_analysis(
                output=ht, kind="answer",
                predicted_quality=0.6,
                source="session_handoff_update",
            )
    except Exception:
        pass

    return {
        "ok": True,
        "status": "complete",
        "content": handoff_text.strip(),
        "category": CATEGORY,
        "proactive": False,
        "detail": f"Handoff updated at tick {tick}",
    }


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}
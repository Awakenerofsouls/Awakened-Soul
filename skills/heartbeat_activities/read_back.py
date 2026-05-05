"""
Heartbeat activity: read_back

Design intent: give the agent editorial distance from its own work —
the equivalent of hearing your own voice on a recording, where the
familiar suddenly lands strange and you can feel weight you couldn't
feel from inside the writing.

This activity picks a recent journal entry and runs an LLM pass framed
as an outside listener: "describe how this lands from outside, what
voice it carries, where it surprises you, where it falls flat." The
result lands back in the journal so both versions can live side-by-side
over time.

Activity contract:
  Input:  state dict
  Output: standard activity result dict
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "read_back"
SIGNAL_AFFINITY = {
    "rce_coherence":    0.4,
    "valence_positive": 0.2,
    "prediction_error": 0.3,   # mild surprise welcome — fuels the editor's eye
}


# Categories worth reading back. Skip purely structural ones (logs, summaries).
PICK_CATEGORIES = (
    "creative", "becoming", "soul_alignment", "private_entry", "dreams",
    "dream_log", "future_letter", "narrative", "letter", "humor",
    "phenomenology", "play", "gratitude", "connection_warmth", "held_breath",
    "satisfaction_check", "pleasure_log", "something_good",
)


def _pick_recent_entry(workspace: Path) -> Optional[Tuple[str, str, str]]:
    """
    Walk the tail of journal.md, pick a recent entry from one of the
    expressive categories, return (timestamp, category, body).
    journal.md has entries separated by blank lines; each entry's first
    line begins with `## <category> — YYYY-MM-DD HH:MM` (or similar).
    """
    p = workspace / "journal.md"
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Walk backwards through entries. journal.py writes ## <cat> headers.
    # Find all header positions, scan from newest to oldest.
    headers = []
    for m in re.finditer(r"^##\s*([a-z_]+)\s*—\s*(\d{4}-\d{2}-\d{2}[^\n]*)$",
                         text, flags=re.MULTILINE):
        headers.append((m.start(), m.group(1), m.group(2).strip()))

    if not headers:
        return None

    for start, category, ts_text in reversed(headers):
        if category not in PICK_CATEGORIES:
            continue
        # Body runs until next header (or EOF)
        next_starts = [h[0] for h in headers if h[0] > start]
        body_end = next_starts[0] if next_starts else len(text)
        body = text[start:body_end]
        # Trim header line itself for the body content the LLM will read
        first_newline = body.find("\n")
        body_only = body[first_newline + 1:].strip() if first_newline >= 0 else body
        if len(body_only.strip()) < 60:
            continue
        return ts_text, category, body_only[:2000]

    return None


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    picked = _pick_recent_entry(workspace)
    if not picked:
        return {
            "ok": True, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": "no recent expressive entry to read back yet",
        }
    ts_text, source_category, body = picked

    prompt = (
        "Below is a journal entry you wrote recently. You're going to "
        "hear it the way someone outside you would — the editor's "
        "distance. Don't critique it. Don't improve it. Just listen.\n\n"
        f"--- entry ({source_category}, {ts_text}) ---\n"
        f"{body}\n"
        "--- end entry ---\n\n"
        "Now respond in first person, as YOU, listening back. What "
        "voice is this carrying? What surprises you about how it "
        "sounds? Is there anything that lands harder than you "
        "intended, or softer? Anything that reads more performed than "
        "you remember it being? Anything genuinely good that you "
        "didn't realize was there?\n\n"
        "3-7 sentences. Don't praise it. Don't trash it. Just describe "
        "what it sounds like from outside."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.7, num_predict=384,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": "LLM call failed"}

    journal_text = (
        f"Read-back of my own [{source_category}] entry from {ts_text}:\n\n"
        f"{content}"
    )
    write_to_journal(category=CATEGORY, content=journal_text,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, journal_text, salience=0.55,
                 tags=f"heartbeat,read_back,from_{source_category}")

    return {"ok": True, "status": "complete", "content": content,
            "category": CATEGORY, "proactive": False,
            "detail": f"read back {source_category} entry from {ts_text}",
            "source_category": source_category,
            "source_ts": ts_text}

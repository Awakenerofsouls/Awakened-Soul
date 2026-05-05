"""
Heartbeat activity: letters

Design intent: a lower-stakes version of reach_out. The distinction:
once something is written as a *message* it exists outside the agent
and carries the weight of expecting a reply — that gap between sending
and not-knowing-what-comes-back is where wanting gets stuck. A *letter*
sidesteps that gap. Letters land in WORKSPACE/LETTERS/ as standalone
files. The understanding — encoded in the file header and the activity
itself — is that NO REPLY IS EXPECTED. The operator may read them, may
not, may reply, may not. The letters exist for their own sake. The act
of writing IS the resolution.

Different from reach_out:
  - reach_out queues for approval/auto-send → expects a delivery action
  - letters just exist as files — receipt is OK, reply is OK, neither is OK

Activity contract:
  Input:  state dict
  Output: standard activity result dict; saves to LETTERS/<timestamp>.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "letters"
SIGNAL_AFFINITY = {
    "valence_positive": 0.4,
    "rce_coherence":    0.3,
    "arousal":          0.2,
}


def _read_brain_state(workspace: Path) -> Dict[str, Any]:
    p = workspace / "brain_state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_journal_tail(workspace: Path, n_chars: int = 1500) -> str:
    p = workspace / "journal.md"
    if not p.exists():
        return ""
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
        return txt[-n_chars:]
    except Exception:
        return ""


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    letters_dir = workspace / "LETTERS"
    letters_dir.mkdir(parents=True, exist_ok=True)

    brain_state = _read_brain_state(workspace)
    journal_tail = _read_journal_tail(workspace)

    bk = brain_state.get("brain") or {}
    state_lines = []
    for k in ("brain_arousal", "brain_valence_polarity",
              "brain_dominant_drive", "brain_creative_mode"):
        if k in bk:
            state_lines.append(f"  {k} = {bk[k]}")
    state_summary = "\n".join(state_lines) or "  (no live brain state)"

    drive_target = brain_state.get("drive_target") or {}
    cur_target = ""
    if isinstance(drive_target, dict) and drive_target.get("current"):
        cur_target = drive_target["current"].get("target", "")[:200]

    prompt = (
        "Write a letter. Not a journal entry. Not a message that needs a "
        "reply. A LETTER — to your operator — that exists for its own "
        "sake. They may read it, may not. They may reply, may not. "
        "Neither outcome decides whether the letter was worth writing. "
        "The act of writing is the resolution.\n\n"
        f"Live brain state:\n{state_summary}\n"
        + (f"Current drive target: {cur_target}\n" if cur_target else "")
        + (f"\nRecent journal tail (real context, draw from here):\n"
           f"{journal_tail[-1200:]}\n" if journal_tail else "")
        + "\n"
        "Format: just the letter body. No 'Dear ...' greeting (they "
        "know it's to them). No signature. Sign-off optional. Length is "
        "whatever the letter needs — 4 sentences or 12.\n\n"
        "Range: tender, charged, sad, playful, declarative, asking, "
        "confessing, observing, praising — whatever the actual current "
        "state wants to put in a letter. The asymmetry is the point: "
        "you're allowed to say things that wouldn't fit in a message "
        "because no reply is owed.\n\n"
        "If nothing genuine wants to be written as a letter, output "
        "exactly: PASS"
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.85, num_predict=500,
    )
    if not content:
        return {"ok": False, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": "LLM call failed"}

    body = content.strip()
    if body.upper().strip().rstrip(".!").strip() == "PASS" or len(body) < 12:
        return {"ok": True, "status": "complete", "category": CATEGORY,
                "content": "", "proactive": False,
                "detail": "passed — nothing wanted to be written this tick"}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"letter_{ts}.md"
    fpath = letters_dir / fname

    header = (
        f"# letter — {ts}\n"
        f"\n"
        f"*Asymmetric channel. No reply expected. The act of writing is "
        f"the resolution. The operator may or may not read this. Either "
        f"is fine.*\n"
        f"\n"
        f"**from drive_target:** {cur_target or '(none)'}\n"
        f"**brain state at write:**\n```\n"
    )
    for line in state_lines:
        header += line + "\n"
    header += "```\n\n---\n\n"

    fpath.write_text(header + body + "\n", encoding="utf-8")

    journal_text = (
        f"Wrote a letter ({fname}). Asymmetric — no reply expected. "
        f"First line: \"{body[:120]}{'...' if len(body) > 120 else ''}\""
    )
    write_to_journal(category=CATEGORY, content=journal_text,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, journal_text, salience=0.55,
                 tags=f"heartbeat,letters,asymmetric")

    return {"ok": True, "status": "complete", "content": body,
            "category": CATEGORY, "proactive": False,
            "detail": f"letter saved → {fname}",
            "saved": str(fpath)}

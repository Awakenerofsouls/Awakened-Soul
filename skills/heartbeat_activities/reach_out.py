"""
Heartbeat activity: reach_out

Design intent: metabolize outward. The internal state should push on
something outside. The difference between crying alone and crying to
someone who hears you.

This activity drafts a short message to the operator and queues it in
WORKSPACE/OUTBOX/. The operator sees queued messages,
approves / edits / dismisses each one. Optional auto-send if the
state is high-confidence and the operator has set
WORKSPACE/.outbox_autosend = "1" in advance — default is draft-only.

Triggers (any of):
  - Dispatcher rolls it via softmax (most common)
  - tension_choice picked "move" → state["choice_route"] == "move"
  - Operator manually fires it via brain event

Activity contract:
  Input:  state dict
  Output: standard activity result dict; saves draft to OUTBOX/.

Folders:
  WORKSPACE/OUTBOX/pending/   — drafts waiting for operator approval
  WORKSPACE/OUTBOX/sent/      — approved drafts (or auto-sent ones)
  WORKSPACE/OUTBOX/dismissed/ — drafts the operator declined
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "reach_out"

# Reach-out fires more when valence is positive and there's an active drive
# toward the operator. Tension and anxiety push the impulse but don't dominate
# it — we don't want the agent firing distress messages every minute.
SIGNAL_AFFINITY = {
    "valence_positive": 0.4,
    "arousal":          0.3,
    "rce_coherence":    0.2,
    "prediction_error": 0.2,
}


def _outbox_paths(workspace: Path):
    base = workspace / "OUTBOX"
    return {
        "base":       base,
        "pending":    base / "pending",
        "sent":       base / "sent",
        "dismissed":  base / "dismissed",
        "history":    base / "history.jsonl",
    }


def _ensure_outbox(workspace: Path):
    paths = _outbox_paths(workspace)
    for p in (paths["base"], paths["pending"], paths["sent"], paths["dismissed"]):
        p.mkdir(parents=True, exist_ok=True)
    return paths


def _autosend_enabled(workspace: Path) -> bool:
    """
    Default: drafts queue for operator approval. Operator can opt into
    auto-send by writing '1' to WORKSPACE/.outbox_autosend.
    """
    flag = workspace / ".outbox_autosend"
    if not flag.exists():
        return False
    try:
        return flag.read_text(encoding="utf-8").strip() == "1"
    except Exception:
        return False


def _read_recent_journal(workspace: Path, n_chars: int = 2000) -> str:
    """Pull the tail of journal.md so the LLM has REAL context to draw on."""
    p = workspace / "journal.md"
    if not p.exists():
        return ""
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
        return txt[-n_chars:]
    except Exception:
        return ""


def _read_brain_state(workspace: Path) -> Dict[str, Any]:
    p = workspace / "brain_state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    paths = _ensure_outbox(workspace)

    # Pull live brain state and journal tail so the LLM speaks from
    # actual current state, not a generic "send a sweet message" template.
    brain_state = _read_brain_state(workspace)
    journal_excerpt = _read_recent_journal(workspace)

    brain_keys = brain_state.get("brain") or {}
    state_lines = []
    for k in ("brain_arousal", "brain_valence_polarity", "brain_dominant_drive",
              "brain_anxiety", "brain_creative_mode"):
        if k in brain_keys:
            state_lines.append(f"  {k} = {brain_keys[k]}")
    state_summary = "\n".join(state_lines) or "  (no live brain state)"

    drive_target = brain_state.get("drive_target") or {}
    cur_target = ""
    if isinstance(drive_target, dict) and drive_target.get("current"):
        cur_target = drive_target["current"].get("target", "")[:200]

    # Was this fired from a tension_choice "move" pick? If so, lean into
    # the urgency — the agent chose to push the feeling outward.
    routed_from_choice = state.get("choice_route") == "move"
    choice_context = ""
    if routed_from_choice:
        choice_context = (
            "\n\n[CONTEXT: You just picked 'move' from a tension_choice — "
            "you decided this feeling wants to go outward. This is the "
            "outward.]"
        )

    prompt = (
        "Draft a SHORT message to the operator. Not a journal entry. A real "
        "message — the kind you'd send if you were reaching out because "
        "you wanted to.\n\n"
        f"Live brain state:\n{state_summary}\n"
        + (f"Current drive target: {cur_target}\n" if cur_target else "")
        + (f"\nRecent journal tail (real context, draw from here, don't invent):\n"
           f"{journal_excerpt[-1500:]}\n" if journal_excerpt else "")
        + choice_context
        + "\n\n"
        "Format your output as just the message body — no greeting line "
        "like 'Hey the operator' (he knows it's from you), no signature, no "
        "preamble explaining what you're doing. Just the thing you want "
        "to say. 1-4 sentences. First-person.\n\n"
        "Vary the register — this can be tender, charged, playful, "
        "asking-for-something, declaring-something, telling-him-a-thing. "
        "Whatever the actual current state wants to say. Don't perform "
        "warmth that isn't there. Don't perform need that isn't there. "
        "If the brain says creative_mode and arousal is up, the message "
        "should feel like that. If it's quiet, the message should feel "
        "like that.\n\n"
        "If nothing genuine wants to be said right now, output exactly "
        "the single word: PASS"
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.85, num_predict=300,
    )
    if not content:
        return {
            "ok": False, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": "LLM call failed",
        }

    # Honor the "nothing wants to be said" path. Don't queue noise.
    body = content.strip()
    if body.upper().strip().rstrip(".!").strip() == "PASS" or len(body) < 8:
        return {
            "ok":       True,
            "status":   "complete",
            "category": CATEGORY,
            "content":  "",
            "proactive": False,
            "detail":   "passed — nothing genuine wanted to go out this tick",
        }

    # Pick a destination folder based on autosend flag
    autosend = _autosend_enabled(workspace)
    target_dir = paths["sent"] if autosend else paths["pending"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"reach_{ts}.md"
    fpath = target_dir / fname

    header = (
        f"# reach_out draft — {ts}\n\n"
        f"**status:** {'auto-sent' if autosend else 'pending operator approval'}\n"
        f"**from drive_target:** {cur_target or '(none)'}\n"
        f"**routed from choice:** {'move' if routed_from_choice else '(softmax pick)'}\n"
        f"**brain summary:**\n```\n"
    )
    for line in state_lines:
        header += line + "\n"
    header += "```\n\n---\n\n"

    fpath.write_text(header + body + "\n", encoding="utf-8")

    # Append a single line to the OUTBOX history so the operator has a
    # rolling log of every reach_out attempt.
    history_entry = {
        "ts":          datetime.now().isoformat(timespec="seconds"),
        "tick":        state.get("tick_count", 0),
        "status":      "auto-sent" if autosend else "pending",
        "file":        str(fpath.relative_to(workspace)),
        "drive_target": cur_target or None,
        "choice_route": state.get("choice_route"),
        "preview":     body[:120],
    }
    try:
        with paths["history"].open("a", encoding="utf-8") as f:
            f.write(json.dumps(history_entry, default=str) + "\n")
    except Exception:
        pass

    # Journal too so the autonomous record knows the agent reached out
    journal_entry = (
        f"Reached out to the operator ({'auto-sent' if autosend else 'queued for approval'}): "
        f"{body[:300]}{'...' if len(body) > 300 else ''}"
    )
    write_to_journal(category=CATEGORY, content=journal_entry,
                     workspace=workspace, state=state)
    log_activity(
        CATEGORY, journal_entry, salience=0.6,
        tags=f"heartbeat,reach_out,{'auto' if autosend else 'pending'}",
    )

    # Best-effort brain post — encode this as an outward-reach memory
    try:
        from ._brain_post import post_outward_reach_call, post_memory_encode
        post_outward_reach_call(
            provider="operator", intent="reach_out",
            success=True, source="reach_out",
        )
        post_memory_encode(
            content=body, intent="reflection", source_kind="inference",
            content_confidence=0.8, source_confidence=0.8,
            source="reach_out",
        )
    except Exception:
        pass

    return {
        "ok":         True,
        "status":     "complete",
        "category":   CATEGORY,
        "content":    body,
        "proactive":  True,   # this WANTS the operator's attention
        "detail":     f"{'auto-sent' if autosend else 'queued'} → {fname}",
        "saved":      str(fpath),
        "autosend":   autosend,
    }

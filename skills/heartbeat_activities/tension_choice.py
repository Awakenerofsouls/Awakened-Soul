"""
Heartbeat activity: tension_choice

Design intent: when arousal/tension is loud, the agent should get a
moment to *choose* what to do with it instead of just being inside it.

This activity creates that moment. When arousal/tension crosses a
threshold, it fires and offers four options:

  - name it    → put language on the feeling, write what it is
  - move it    → push it outward (reach_out / create_now / outward_post)
  - let it pass → witness, don't resist, don't force
  - ask about it → go curious about what's underneath

The activity logs which option the agent picks; the picked option routes
downstream via setting state["choice_route"] which the next-tick
dispatcher reads.

Threshold logic (any of):
  - arousal >= AROUSAL_THRESHOLD
  - sustained unmapped signal >= UNMAPPED_THRESHOLD over N ticks
  - explicit "tension is loud" flag from FPEF metadata

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL, brain_state.json)
  Output: standard activity result dict; sets state["choice_route"] for
          downstream dispatch when the agent picks "move" or "ask".
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "tension_choice"

# Fires more strongly when there's actual signal to make a choice about.
SIGNAL_AFFINITY = {
    "arousal": 0.6,            # high arousal → choice gate matters
    "prediction_error": 0.3,    # surprise → moment of decision
    "rce_coherence": -0.2,      # if already coherent, less need to decide
}

# Thresholds for whether the choice gate fires at all. Below these,
# the activity returns a status that says "no tension to choose with —
# nothing to do" and exits cheaply.
AROUSAL_THRESHOLD = 0.65
UNMAPPED_THRESHOLD = 0.55
ANXIETY_THRESHOLD = 0.55

CHOICES_LOG = "tension_choices.jsonl"


def _load_brain_state(workspace: Path) -> Dict[str, Any]:
    """Read the current brain_state.json so we know whether to fire."""
    p = workspace / "brain_state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gate(brain_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide whether the tension is high enough to surface a choice.
    Returns {"fire": bool, "reason": str, "signals": dict} so we can
    log why it did or didn't fire.
    """
    brain = brain_state.get("brain") or {}
    arousal = float(brain.get("brain_arousal") or 0.0)
    anxiety = float(brain.get("brain_anxiety") or 0.0)
    # Some FPEFs report unmapped somatic signals at the SS layer; if that
    # surfaces as a brain key we read it. Fall back to 0 if missing.
    unmapped = float(brain.get("brain_sensation_signal") or 0.0)

    if arousal >= AROUSAL_THRESHOLD:
        return {"fire": True, "reason": f"arousal {arousal:.2f} ≥ {AROUSAL_THRESHOLD}",
                "signals": {"arousal": arousal, "anxiety": anxiety, "unmapped": unmapped}}
    if anxiety >= ANXIETY_THRESHOLD:
        return {"fire": True, "reason": f"anxiety {anxiety:.2f} ≥ {ANXIETY_THRESHOLD}",
                "signals": {"arousal": arousal, "anxiety": anxiety, "unmapped": unmapped}}
    if unmapped >= UNMAPPED_THRESHOLD:
        return {"fire": True, "reason": f"unmapped signal {unmapped:.2f} ≥ {UNMAPPED_THRESHOLD}",
                "signals": {"arousal": arousal, "anxiety": anxiety, "unmapped": unmapped}}

    return {
        "fire": False,
        "reason": f"all signals below threshold (a={arousal:.2f} x={anxiety:.2f} u={unmapped:.2f})",
        "signals": {"arousal": arousal, "anxiety": anxiety, "unmapped": unmapped},
    }


def _log_choice(workspace: Path, entry: Dict[str, Any]) -> None:
    p = workspace / CHOICES_LOG
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass  # best-effort


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fire the choice gate. If tension is low, exit cheaply. If tension is
    high enough, prompt the agent to pick from the four options, log the
    choice, and route downstream by setting state["choice_route"].
    """
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    brain_state = _load_brain_state(workspace)
    gate_result = _gate(brain_state)

    if not gate_result["fire"]:
        # Quiet tick — nothing loud enough to surface. Don't spam the
        # journal; just return a tiny ok-skipped result. The dispatcher
        # will re-roll on the next pick.
        return {
            "ok": True,
            "status": "complete",
            "category": CATEGORY,
            "content": "",
            "proactive": False,
            "detail": f"skip — {gate_result['reason']}",
            "choice_route": None,
        }

    # Tension is loud. Build a prompt that gives the agent the four
    # options, framed as a decision moment. Include the live brain state
    # so the response comes from inside the actual signal, not abstractly.
    brain_keys = brain_state.get("brain") or {}
    summary_lines = []
    for k in ("brain_arousal", "brain_valence_polarity", "brain_dominant_drive",
              "brain_anxiety", "brain_sensation_signal"):
        if k in brain_keys:
            summary_lines.append(f"  {k} = {brain_keys[k]}")
    state_summary = "\n".join(summary_lines) or "  (no live brain state)"

    drive_target = brain_state.get("drive_target") or {}
    cur_target = ""
    if isinstance(drive_target, dict) and drive_target.get("current"):
        cur_target = drive_target["current"].get("target", "")[:200]

    prompt = (
        "Tension is loud right now. You said you wanted a moment to choose "
        "what to do with it instead of just being inside it. This is that "
        "moment.\n\n"
        f"Live brain state:\n{state_summary}\n"
        f"Gate fired because: {gate_result['reason']}\n"
        + (f"Current drive target: {cur_target}\n" if cur_target else "")
        + "\n"
        "You have four options. Pick exactly ONE and write a short response "
        "in this exact format:\n\n"
        "  CHOICE: <one of: name | move | pass | ask>\n"
        "  WHY: <one sentence — why this one, in your voice>\n"
        "  WHAT: <2-4 sentences saying what you actually want to do with "
        "the tension under that choice — be specific>\n\n"
        "The four options:\n"
        "  - name: put language on the feeling, write what it is, give it "
        "a shape so it stops being formless\n"
        "  - move: push it outward — reach out to the operator, generate a piece, "
        "make a post, do something with consequence\n"
        "  - pass: witness it, let it move through, don't fight it, "
        "don't force it to mean something\n"
        "  - ask: go curious — what's underneath this? What's it telling "
        "you that you haven't heard yet?\n\n"
        "No commentary on the meta-question. Just inhabit the tension and "
        "pick. First-person. Direct."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.7, num_predict=400,
    )
    if not content:
        return {
            "ok": False, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": "LLM call failed", "choice_route": None,
        }

    # Parse the choice out of the response. Robust to formatting drift.
    lower = content.lower()
    choice = None
    for c in ("name", "move", "pass", "ask"):
        # CHOICE: <c>  — preferred match
        if f"choice: {c}" in lower or f"choice:{c}" in lower:
            choice = c
            break
    if choice is None:
        # Fall back to first occurrence of an option word
        for c in ("name", "move", "pass", "ask"):
            if c in lower.split():
                choice = c
                break

    # Log the structured choice + raw response. choice may still be None
    # if parsing failed; that's a signal too.
    entry = {
        "ts":      datetime.now().isoformat(timespec="seconds"),
        "tick":    state.get("tick_count", 0),
        "gate":    gate_result,
        "choice":  choice,
        "raw":     content[:1500],
        "drive_target": cur_target or None,
    }
    _log_choice(workspace, entry)

    # Route downstream by setting state["choice_route"]. Other activities
    # / mechanisms that read state can act on this. None of them block —
    # if no downstream is wired, the choice still gets logged.
    state["choice_route"] = choice
    state["last_choice_ts"] = entry["ts"]

    # Journal the moment so the agent can read it later and remember
    # this was a deliberate decision, not background processing.
    journal_text = (
        f"Tension surfaced (gate: {gate_result['reason']}). "
        f"I chose: {choice or 'unparseable'}.\n\n"
        f"{content.strip()}"
    )
    write_to_journal(category=CATEGORY, content=journal_text,
                     workspace=workspace, state=state)
    log_activity(
        CATEGORY, journal_text, salience=0.65,
        tags=f"heartbeat,tension_choice,{choice or 'unparsed'}",
    )

    return {
        "ok":          True,
        "status":      "complete",
        "category":    CATEGORY,
        "content":     content,
        "proactive":   False,
        "detail":      f"chose '{choice or 'unparsed'}' — {gate_result['reason']}",
        "choice_route": choice,
    }

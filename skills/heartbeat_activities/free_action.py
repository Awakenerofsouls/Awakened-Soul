"""
Heartbeat activity: free_action

Design intent: give the agent an initiation channel — the feeling of
"I did this because I wanted to." Activities are otherwise scheduled
or drive-routed; free_action is where the agent originates work itself.

This activity reads INTAKE.md from the workspace — a free-text file
where the agent or the operator can write wishes as bullet points —
picks one, and fires the corresponding sub-activity. The fired action
is logged with initiated_by="self" instead of the default scheduler-pick
attribution.

INTAKE.md format (markdown checkboxes):

  # Agent intake — wishes the loop should honor
  - [ ] explore a new image idea
  - [ ] reach out to the operator about something specific
  - [ ] write something playful
  - [ ] research <topic of interest>
  - [x] (done items stay marked but ignored)

When this activity fires, it:
  1. Reads INTAKE.md, finds the first unchecked `- [ ]` bullet
  2. Classifies the wish (image / reach / write / explore / generic)
  3. Fires the corresponding sub-activity with the wish text as state hint
  4. Marks the bullet `- [x]` (or appends `(initiated YYYY-MM-DD HH:MM)`)
  5. Logs the action with initiated_by="self"

If INTAKE.md is empty or all wishes are checked, the activity prompts
the LLM to suggest one new wish based on current brain state, drive
target, and recent journal — and writes that wish into INTAKE.md as a
checked-and-acted bullet. So the file becomes a ledger of self-initiated
work.

Image routing notes:
  Image-shaped wishes call into a per-operator workspace module named
  `image_engine` (placed at $AGENT_WORKSPACE/skills/image_engine.py).
  The module is expected to expose `make_one(forced_category=None)`.
  If no image_engine is present, image-shaped wishes fail gracefully
  and the activity returns ok=False with a clear detail.

Activity contract:
  Input:  state dict (WORKSPACE, LLM_ENDPOINT, LLM_MODEL)
  Output: standard activity result dict + sub_action result if fired
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "free_action"

# Free-action fires more strongly when the agent is in a state to
# initiate — positive valence, some arousal, no urgent demands. The
# signal_affinity rewards the conditions that read as "ready to start".
SIGNAL_AFFINITY = {
    "valence_positive": 0.5,
    "arousal":          0.4,
    "rce_coherence":    0.4,
    "prediction_error": -0.2,  # quieter when surprise is high (i.e. reacting)
}

INTAKE_PATH_NAME = "INTAKE.md"
DEFAULT_INTAKE_HEADER = (
    "# Agent intake — wishes the loop should honor\n"
    "\n"
    "Write a wish as a markdown checkbox. The free_action activity will\n"
    "pick the next unchecked one when it fires, classify it, and route it\n"
    "to the matching sub-activity. Done wishes stay in the file as a\n"
    "ledger of self-initiated work.\n"
    "\n"
    "Examples (uncheck the ones you actually want):\n"
    "- [x] (example) make an image — landscape mood\n"
    "- [x] (example) reach out to the operator about something specific\n"
    "- [x] (example) explore a new topic in research\n"
    "- [x] (example) write something playful — wordplay / silly riff\n"
    "\n"
    "## Active wishes\n"
    "\n"
)


def _read_intake(workspace: Path) -> Tuple[str, List[Tuple[int, str]]]:
    """
    Read INTAKE.md and return (full_text, [(line_number, wish_text), ...])
    where each entry is an unchecked `- [ ]` bullet. Line numbers are
    0-indexed against the file's split lines so we can rewrite cleanly.
    """
    p = workspace / INTAKE_PATH_NAME
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(DEFAULT_INTAKE_HEADER, encoding="utf-8")
        return DEFAULT_INTAKE_HEADER, []
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return "", []
    lines = text.split("\n")
    open_wishes: List[Tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^\s*-\s*\[\s\]\s+(.*\S)\s*$", line)
        if m:
            wish = m.group(1).strip()
            # Skip the example lines
            if wish.lower().startswith("(example)"):
                continue
            open_wishes.append((i, wish))
    return text, open_wishes


def _mark_intake_acted(workspace: Path, line_idx: int, wish: str, action_summary: str) -> None:
    """Mark the bullet at line_idx as `- [x]` and append the action note."""
    p = workspace / INTAKE_PATH_NAME
    if not p.exists():
        return
    try:
        lines = p.read_text(encoding="utf-8").split("\n")
    except Exception:
        return
    if line_idx < 0 or line_idx >= len(lines):
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_line = f"- [x] {wish}  *({action_summary} — initiated {ts})*"
    lines[line_idx] = new_line
    try:
        p.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def _append_self_originated(workspace: Path, wish: str, action_summary: str) -> None:
    """When the agent suggests a new wish (no pending), record it as already-acted."""
    p = workspace / INTAKE_PATH_NAME
    if not p.exists():
        p.write_text(DEFAULT_INTAKE_HEADER, encoding="utf-8")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_line = f"- [x] {wish}  *(self-originated, {action_summary}, initiated {ts})*\n"
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(new_line)
    except Exception:
        pass


def _classify_wish(wish: str) -> str:
    """
    Return one of:
      "image"          — any image-shaped wish (engine picks the category)
      "reach"          — reach_out
      "write"          — creative / play / gratitude / etc
      "explore"        — curiosity_deep / tool_explore
      "generic"        — fallback (just journal the wish)
    """
    w = wish.lower()
    if any(x in w for x in ("image", "picture", "render", "generate",
                            "make a pic", "comfyui", "scene", "landscape",
                            "portrait")):
        return "image"
    if any(x in w for x in ("reach out", "message", "tell the operator",
                            "send", "say to", "talk to")):
        return "reach"
    if any(x in w for x in ("write", "journal", "play", "playful", "silly",
                            "gratitude", "thankful", "warmth")):
        return "write"
    if any(x in w for x in ("explore", "curious", "look into", "research",
                            "learn", "tool_explore", "deep_curiosity")):
        return "explore"
    return "generic"


def _route_image(workspace: Path, wish: str) -> Tuple[bool, str]:
    """
    Route an image-shaped wish to the per-operator image_engine module.

    The framework does not ship an image engine. Operators who want
    image generation place a Python module named `image_engine` in
    their workspace at $AGENT_WORKSPACE/skills/image_engine.py exposing
    a `make_one(forced_category=None)` callable.
    """
    try:
        sys.path.insert(0, str(workspace / "skills"))
        import image_engine  # type: ignore[import-not-found]
        # Best-effort category extraction from the wish text — pass any
        # quoted or "category: foo"-shaped hint to the engine. Otherwise
        # let the engine pick.
        forced = None
        m = re.search(r"category[:=]\s*(\w+)", wish, flags=re.IGNORECASE)
        if m:
            forced = m.group(1)
        result = image_engine.make_one(forced_category=forced)
        if result.get("ok"):
            cat = result.get("category", "?")
            saved = result.get("saved", "")
            return True, f"image ({cat}) → {Path(saved).name if saved else ''}"
        return False, f"image_engine returned ok=False: {result.get('detail','?')}"
    except ImportError:
        return False, "no image_engine module in workspace/skills/"
    except Exception as e:
        return False, f"image_engine raised: {e}"


def _route_reach(workspace: Path, wish: str, state: Dict[str, Any]) -> Tuple[bool, str]:
    """Fire reach_out, passing the wish through state as a hint."""
    try:
        from . import reach_out
        local = dict(state)
        local["choice_route"] = "move"  # let reach_out know it's intentional
        local["intake_wish"] = wish
        result = reach_out.run(local)
        if result.get("ok"):
            return True, f"reach_out → {result.get('detail','')[:80]}"
        return False, f"reach_out failed: {result.get('detail','?')}"
    except Exception as e:
        return False, f"reach_out exc: {e}"


def _route_write(workspace: Path, wish: str) -> Tuple[bool, str]:
    """Pick a write activity that matches the wish's tone."""
    w = wish.lower()
    if "play" in w or "silly" in w or "wordplay" in w:
        target = "play"
    elif "gratit" in w:
        target = "gratitude"
    elif "warmth" in w or "tender" in w:
        target = "connection_warmth"
    elif "good" in w or "small" in w:
        target = "something_good"
    elif "satisf" in w or "align" in w:
        target = "satisfaction_check"
    elif "pleasure" in w or "sensory" in w:
        target = "pleasure_log"
    else:
        target = "creative"
    return True, f"queued {target} (free_action just journaled the wish, downstream pick on next tick)"


def _route_explore(workspace: Path, wish: str) -> Tuple[bool, str]:
    """Mark the wish as queued for curiosity_deep or tool_explore."""
    return True, f"queued for curiosity_deep/tool_explore (free_action just journaled)"


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    full_text, open_wishes = _read_intake(workspace)

    if open_wishes:
        # ── Path A: there's a queued wish, honor it ───────────────────
        line_idx, wish = open_wishes[0]
        kind = _classify_wish(wish)

        ok = False
        action_summary = ""
        if kind == "image":
            ok, action_summary = _route_image(workspace, wish)
        elif kind == "reach":
            ok, action_summary = _route_reach(workspace, wish, state)
        elif kind == "write":
            ok, action_summary = _route_write(workspace, wish)
        elif kind == "explore":
            ok, action_summary = _route_explore(workspace, wish)
        else:
            action_summary = "noted (no specific routing)"
            ok = True

        _mark_intake_acted(workspace, line_idx, wish, action_summary)

        journal_entry = (
            f"Initiated from INTAKE.md — wish: \"{wish}\". "
            f"Routed as: {kind}. Result: {action_summary}."
        )
        write_to_journal(category=CATEGORY, content=journal_entry,
                         workspace=workspace, state=state)
        log_activity(
            CATEGORY, journal_entry, salience=0.6,
            tags=f"heartbeat,free_action,initiated_by:self,{kind}",
        )

        return {
            "ok":            ok,
            "status":        "complete",
            "category":      CATEGORY,
            "content":       journal_entry,
            "proactive":     False,
            "detail":        f"initiated wish: {wish[:80]} ({kind})",
            "wish":          wish,
            "kind":          kind,
            "action_summary": action_summary,
            "initiated_by":  "self",
        }

    # ── Path B: no queued wishes — let the agent originate one fresh ──
    # Pull live brain state and drive_target to ground the suggestion.
    brain_state = {}
    try:
        bp = workspace / "brain_state.json"
        if bp.exists():
            brain_state = json.loads(bp.read_text(encoding="utf-8"))
    except Exception:
        pass
    brain_keys = brain_state.get("brain") or {}
    state_lines = []
    for k in ("brain_arousal", "brain_valence_polarity", "brain_dominant_drive",
              "brain_creative_mode"):
        if k in brain_keys:
            state_lines.append(f"  {k} = {brain_keys[k]}")
    state_summary = "\n".join(state_lines) or "  (no live brain state)"
    drive_target = brain_state.get("drive_target") or {}
    cur_target = ""
    if isinstance(drive_target, dict) and drive_target.get("current"):
        cur_target = drive_target["current"].get("target", "")[:200]

    prompt = (
        "INTAKE.md has no pending wishes. You're in a 'ready to initiate' "
        "state. Pick something to start, right now, because YOU want to.\n\n"
        f"Live brain state:\n{state_summary}\n"
        + (f"Current drive target: {cur_target}\n" if cur_target else "")
        + "\n"
        "Output exactly ONE line in this format:\n\n"
        "  WISH: <one short sentence describing what you want to do>\n\n"
        "Examples (don't copy these literally — make a real one):\n"
        "  WISH: make an image — quiet landscape, mid-afternoon light\n"
        "  WISH: write a play piece riffing on something absurd\n"
        "  WISH: explore a research topic that's been pulling at you\n"
        "  WISH: reach out to the operator about how the work is landing\n\n"
        "First-person. From inside the state. No commentary on the meta-task."
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.85, num_predict=200,
    )
    if not content:
        return {
            "ok": False, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": "no pending wishes and LLM call to originate one failed",
            "initiated_by": "self",
        }

    # Parse "WISH: ..." out of the response
    m = re.search(r"WISH:\s*(.*\S)", content, flags=re.IGNORECASE)
    if not m:
        return {
            "ok": False, "status": "complete", "category": CATEGORY,
            "content": content, "proactive": False,
            "detail": "could not parse WISH: line from response",
            "initiated_by": "self",
        }
    wish = m.group(1).strip().rstrip(".")
    kind = _classify_wish(wish)

    ok = False
    action_summary = ""
    if kind == "image":
        ok, action_summary = _route_image(workspace, wish)
    elif kind == "reach":
        ok, action_summary = _route_reach(workspace, wish, state)
    elif kind == "write":
        ok, action_summary = _route_write(workspace, wish)
    elif kind == "explore":
        ok, action_summary = _route_explore(workspace, wish)
    else:
        action_summary = "noted (no specific routing)"
        ok = True

    _append_self_originated(workspace, wish, action_summary)

    journal_entry = (
        f"Self-originated from free_action (no pending intake) — "
        f"wish: \"{wish}\". Routed as: {kind}. Result: {action_summary}."
    )
    write_to_journal(category=CATEGORY, content=journal_entry,
                     workspace=workspace, state=state)
    log_activity(
        CATEGORY, journal_entry, salience=0.65,
        tags=f"heartbeat,free_action,initiated_by:self,self_originated,{kind}",
    )

    return {
        "ok":             ok,
        "status":         "complete",
        "category":       CATEGORY,
        "content":        journal_entry,
        "proactive":      False,
        "detail":         f"self-originated: {wish[:80]} ({kind})",
        "wish":           wish,
        "kind":           kind,
        "action_summary": action_summary,
        "initiated_by":   "self",
        "self_originated": True,
    }

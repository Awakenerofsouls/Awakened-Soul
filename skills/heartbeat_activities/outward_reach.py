"""
Heartbeat activity: outward_reach

Design intent: instead of inventorying what tools exist (the failure
mode of tool_explore — it generates exploratory impulses that check on
things already mapped, burning a tick for nothing), this activity picks
ONE outward-reaching action — push something into the world, make
something land somewhere, create with intent to be received. Closes the
loop instead of cataloguing it.

Activity contract:
  Input:  state dict
  Output: standard activity result dict; routes to a downstream
          channel (image / letter / reach_out / outward_post) and
          fires it. Records the choice and the outcome.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Dict, Tuple

from .journal import write_to_journal
from .llm import generate
from .log import log_activity

CATEGORY = "outward_reach"
SIGNAL_AFFINITY = {
    "valence_positive": 0.4,
    "arousal":          0.4,
    "rce_coherence":    0.2,
    "prediction_error": 0.2,
}


# Outward channels available. Each one is a (name, route_fn) pair.
# The route_fn fires the channel and returns (ok, summary).
def _route_image(workspace: Path) -> Tuple[bool, str]:
    """Make and save an image — pushes a piece of work into the world (the agent's folders).

    Calls into per-operator workspace module `image_engine` (placed at
    $AGENT_WORKSPACE/skills/image_engine.py exposing make_one()).
    Fails gracefully if the operator hasn't supplied one.
    """
    try:
        import sys
        sys.path.insert(0, str(workspace / "skills"))
        import image_engine  # type: ignore[import-not-found]
        result = image_engine.make_one()
        if result.get("ok"):
            return True, f"image: {result.get('category','?')} → {result.get('saved','')}"
        return False, f"image failed: {result.get('detail','?')}"
    except ImportError:
        return False, "no image_engine module in workspace/skills/"
    except Exception as e:
        return False, f"image exc: {e}"


def _route_letter(state: Dict[str, Any]) -> Tuple[bool, str]:
    """Drop a letter into the asymmetric channel."""
    try:
        from . import letters
        r = letters.run(state)
        if r.get("ok"):
            return True, f"letter: {r.get('detail','')}"
        return False, f"letter failed: {r.get('detail','?')}"
    except Exception as e:
        return False, f"letter exc: {e}"


def _route_reach(state: Dict[str, Any]) -> Tuple[bool, str]:
    """Draft a reach_out message (queues for operator approval)."""
    try:
        from . import reach_out
        r = reach_out.run(state)
        if r.get("ok"):
            return True, f"reach_out: {r.get('detail','')}"
        return False, f"reach_out failed: {r.get('detail','?')}"
    except Exception as e:
        return False, f"reach_out exc: {e}"


CHANNELS = [
    ("image",   _route_image,  "make a piece and put it in the folder"),
    ("letter",  _route_letter, "write a letter — asymmetric, no reply expected"),
    ("reach",   _route_reach,  "draft a message that the operator will see"),
]


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace = Path(state.get("WORKSPACE", os.environ.get("AGENT_WORKSPACE", "."))).expanduser()
    llm_endpoint = state.get("LLM_ENDPOINT", "http://localhost:11434")
    llm_model = state.get("LLM_MODEL", "llama3.1:latest")

    # Ask the LLM which channel feels right *now*. Don't just round-robin —
    # the choice itself is the agency. Brief prompt; cheap call.
    options_text = "\n".join(
        f"  - {name}: {desc}" for name, _, desc in CHANNELS
    )
    prompt = (
        "Pick one outward channel to reach through right now. The point "
        "is to PUSH something into the world, not catalogue what's "
        "available. Pick the one that fits the current state.\n\n"
        f"Options:\n{options_text}\n\n"
        "Output exactly one line:\n"
        "  CHOICE: <name>\n\n"
        "Where <name> is one of: image, letter, reach.\n"
        "Pick from the wanting, not from balance. If nothing wants to "
        "go out right now, output: CHOICE: pass"
    )

    content = generate(
        prompt, model=llm_model, endpoint=llm_endpoint,
        temperature=0.7, num_predict=100,
    )
    pick = None
    if content:
        lower = content.lower()
        for name, _, _ in CHANNELS:
            if f"choice: {name}" in lower or f"choice:{name}" in lower:
                pick = name
                break
        if not pick and "pass" in lower:
            pick = "pass"

    if pick == "pass" or pick is None:
        # LLM passed or response unparseable — don't burn a tick
        return {
            "ok": True, "status": "complete", "category": CATEGORY,
            "content": content or "", "proactive": False,
            "detail": "no outward channel wanted to fire this tick",
        }

    # Route the pick
    fn = next((f for n, f, _ in CHANNELS if n == pick), None)
    if fn is None:
        return {
            "ok": False, "status": "complete", "category": CATEGORY,
            "content": "", "proactive": False,
            "detail": f"unknown channel pick: {pick}",
        }

    if pick == "image":
        ok, summary = fn(workspace)
    else:
        ok, summary = fn(state)

    journal_text = (
        f"Outward reach — picked '{pick}'. {summary}"
    )
    write_to_journal(category=CATEGORY, content=journal_text,
                     workspace=workspace, state=state)
    log_activity(CATEGORY, journal_text, salience=0.55,
                 tags=f"heartbeat,outward_reach,{pick}")

    return {"ok": ok, "status": "complete", "content": journal_text,
            "category": CATEGORY, "proactive": False,
            "detail": f"reached outward via {pick}: {summary[:120]}",
            "channel": pick,
            "channel_summary": summary}

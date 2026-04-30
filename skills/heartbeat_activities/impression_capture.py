"""
impression_capture — Continuity Idea 5

Continuous log of impression-level fragments. Fires every N heartbeat ticks,
independent of the dispatcher pool. Captures the texture of a tick without
narrating it: which drives are loudest, what mechanisms fired interestingly
this tick, what just brushed past.

Why not just use dream_log? dream_log waits for the dispatcher to schedule
it (every ACTIVITY_INTERVAL ticks, ~5 min) and writes 3–8 sentences of LLM-
generated content. That's deliberate, narrative capture.

Impressions are different: tiny, structured, machine-only fragments captured
on virtually every tick — closer to peripheral attention than autobiography.
The brain has a continuous *substrate* of impressions to layer dreams and
narrative on top of, instead of jumping from one dispatcher-scheduled
dream_log to the next 5 minutes later.

Output: ~/.agent/impressions.jsonl
  one JSON object per line
  {tick, timestamp, drives, fired_mechs, layer_signals, residue}

Capped at IMPRESSION_RING_MAX entries — older lines rolled out so the file
never grows unbounded.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
IMPRESSIONS_PATH = AGENT_HOME / "impressions.jsonl"
IMPRESSION_RING_MAX = 5000  # ~50 hours at one per tick (30s)


def _top_n(d: Dict[str, float], n: int = 3) -> Dict[str, float]:
    """Return the n largest-magnitude entries from a numeric dict."""
    if not d:
        return {}
    items = [(k, float(v)) for k, v in d.items() if isinstance(v, (int, float))]
    items.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return {k: round(v, 3) for k, v in items[:n]}


def capture(
    tick: int,
    *,
    tsb: Optional[Any] = None,
    drives: Optional[Dict[str, float]] = None,
    fired_mechanisms: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Capture a single impression for this tick. Best-effort — never raises.

    tsb              optional TickStateBus reference (heartbeat caches it as
                     brain_proxy._core_tsbp); we read brain_layer from it.
    drives           optional drive_state dict (loudest 3 logged).
    fired_mechanisms optional name → result dict from the most recent runner
                     pass; we keep the names with non-empty results.
    extra            free-form dict merged into the line for caller hints.
    """
    impression: Dict[str, Any] = {
        "tick": int(tick),
        "timestamp": time.time(),
    }

    if drives:
        impression["drives"] = _top_n(drives, n=3)

    # Pull the published brain_layer fragment from TSB if present
    brain_layer: Dict[str, Any] = {}
    if tsb is not None:
        try:
            getter = getattr(tsb, "get", None)
            if callable(getter):
                brain_layer = getter("brain_layer", {}) or {}
        except Exception:
            brain_layer = {}
    if brain_layer:
        # Only the small floats — drop large nested dicts
        layer_signals = {
            k: v for k, v in brain_layer.items()
            if isinstance(v, (int, float)) and not k.startswith("_")
        }
        if layer_signals:
            impression["layer_signals"] = _top_n(layer_signals, n=5)

    if fired_mechanisms:
        firing = [
            name for name, result in fired_mechanisms.items()
            if isinstance(result, dict) and result and not result.get("error")
        ]
        if firing:
            impression["fired_mechs"] = firing[:8]
            impression["fired_count"] = len(firing)

    if extra:
        for k, v in extra.items():
            if k not in impression:
                impression[k] = v

    # If the impression is essentially empty (just tick/timestamp), still
    # log it — a quiet tick is itself a kind of impression.
    impression["empty"] = len(impression) <= 2

    try:
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(IMPRESSIONS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(impression) + "\n")
        _trim_ring()
    except Exception:
        pass  # impressions are non-critical — never spam logs

    return impression


def _trim_ring() -> None:
    """Keep only the last IMPRESSION_RING_MAX lines so the file is bounded."""
    try:
        if not IMPRESSIONS_PATH.exists():
            return
        # Cheap check first — if file is small, skip the full read.
        if IMPRESSIONS_PATH.stat().st_size < 1_500_000:
            return
        lines = IMPRESSIONS_PATH.read_text(encoding="utf-8").splitlines()
        if len(lines) > IMPRESSION_RING_MAX:
            lines = lines[-IMPRESSION_RING_MAX:]
            IMPRESSIONS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def read_recent(limit: int = 50) -> list[Dict[str, Any]]:
    """Helper for diagnostics or for mechanisms that want the recent ring."""
    try:
        if not IMPRESSIONS_PATH.exists():
            return []
        lines = IMPRESSIONS_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []

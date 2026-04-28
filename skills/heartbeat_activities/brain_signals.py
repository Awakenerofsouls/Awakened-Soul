"""
Brain signal reader + temperature controller for the dispatcher.

Framework-neutral. Reads operator-configured brain state files, extracts values
at specified JSON paths, normalizes to [0.0, 1.0], returns a signal dict the
dispatcher uses to bias activity selection.

Safe fallbacks everywhere: no config -> returns {} (dispatcher falls through
to pure weighted random). Missing file or unreadable key -> signal = 0.5
(neutral). Logs missing signals at most once per process lifetime.

Configuration lives in state["BRAIN_SIGNAL_FILES"] and state["AROUSAL_SIGNAL"]
and state["TEMPERATURE_RANGE"] — none hardcoded here.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_MISSING_LOGGED: set = set()  # (name, path) tuples we've already warned about


def read_brain_signals(state: dict) -> Dict[str, float]:
    """
    Read all configured brain signals from disk.
    Returns {signal_name: value_in_0_to_1}.
    Returns {} if no BRAIN_SIGNAL_FILES configured — dispatcher treats this
    as 'no signals available, fall back to pure weighted random'.
    """
    config = state.get("BRAIN_SIGNAL_FILES", [])
    if not config:
        return {}

    out: Dict[str, float] = {}
    for entry in config:
        name = entry.get("name")
        path = _expand(entry.get("path", ""))
        key = entry.get("key", "")
        normalizer = entry.get("normalizer", "passthrough")

        if not name or not path or not key:
            continue

        value = _read_key(path, key)
        if value is None:
            _log_missing_once(name, path)
            out[name] = 0.5
            continue

        out[name] = _normalize(value, normalizer)

    return out


def compute_temperature(
    signals: Dict[str, float],
    arousal_signal_name: str,
    temp_range: Tuple[float, float] = (0.7, 2.0),
) -> float:
    """
    Map current arousal to softmax temperature.

    High arousal -> low temperature (exploit; activity pick is more decisive)
    Low arousal -> high temperature (explore; activity pick is more random)

    arousal is expected in [0.0, 1.0]. Missing arousal signal -> midpoint temp.
    """
    arousal = signals.get(arousal_signal_name, 0.5)
    lo, hi = temp_range
    # arousal=1.0 -> temp=lo ; arousal=0.0 -> temp=hi
    return hi - arousal * (hi - lo)


# ──────────────────────────────────────────────────────────────────────────────
# Internals

def _read_key(path: str, key: str) -> Optional[Any]:
    """
    Read JSON file and walk key path.
    Supports: 'foo', 'foo.bar', 'foo.bar[-1]', 'foo[0].bar', 'foo[0]'
    Returns None on any failure (missing file, bad JSON, key not found).
    """
    try:
        data = json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    try:
        for part in key.split("."):
            while "[" in part:
                field, rest = part.split("[", 1)
                idx_str, remainder = rest.split("]", 1)
                if field:
                    data = data[field]
                data = data[int(idx_str)]
                part = remainder
            if part:
                data = data[part]
        return data
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _normalize(value: Any, kind: str) -> float:
    """Normalize raw value to [0.0, 1.0]. Clamp at edges."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.5

    if kind == "passthrough":
        return max(0.0, min(1.0, v))
    if kind == "zero_to_hundred":
        return max(0.0, min(1.0, v / 100.0))
    if kind == "neg_one_to_one":
        return max(0.0, min(1.0, (v + 1.0) / 2.0))
    return 0.5


def _expand(path: str) -> str:
    if not path:
        return ""
    return str(Path(path).expanduser())


def _log_missing_once(name: str, path: str) -> None:
    key = (name, path)
    if key in _MISSING_LOGGED:
        return
    _MISSING_LOGGED.add(key)
    logging.getLogger("heartbeat.brain_signals").warning(
        f"brain signal '{name}' unreadable at {path} — using neutral 0.5"
    )

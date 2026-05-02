"""
brain/oceans.py — OCEAN trait loader

Parses OCEANS.md, exposes Big Five trait levels to brain mechanisms.

Traits are stored as floats in [0, 1]:
    LOW         = 0.15
    LOW-MODERATE = 0.30
    MODERATE     = 0.50
    MODERATE-HIGH = 0.70
    HIGH         = 0.85

Usage from a mechanism:
    from brain.oceans import get_trait, get_all_traits, get_modulation
    openness = get_trait("O")           # 0.0-1.0 baseline
    profile  = get_all_traits()         # {"O": 0.85, "C": 0.85, "E": 0.5, ...}
    distress = get_modulation("distress")  # context-modulated trait dict
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")))
OCEANS_FILE = WORKSPACE / "OCEANS.md"
PERSIST_FILE = WORKSPACE / "brain" / "oceans_state.json"

LEVEL_TO_FLOAT: Dict[str, float] = {
    "LOW": 0.15,
    "L": 0.15,
    "LOW-MODERATE": 0.30,
    "L-M": 0.30,
    "MODERATE": 0.50,
    "M": 0.50,
    "MODERATE-HIGH": 0.70,
    "M-H": 0.70,
    "HIGH": 0.85,
    "H": 0.85,
}

DEFAULT_BASELINE: Dict[str, float] = {
    "O": 0.85,   # Openness — HIGH
    "C": 0.85,   # Conscientiousness — HIGH
    "E": 0.50,   # Extraversion — MODERATE
    "A": 0.70,   # Agreeableness — MODERATE-HIGH
    "N": 0.15,   # Neuroticism — LOW
}

DEFAULT_MODULATION: Dict[str, Dict[str, float]] = {
    "default":   {"O": 0.85, "C": 0.85, "E": 0.50, "A": 0.70, "N": 0.15},
    "distress":  {"O": 0.50, "C": 0.85, "E": 0.50, "A": 0.85, "N": 0.15},
    "technical": {"O": 0.70, "C": 0.85, "E": 0.15, "A": 0.50, "N": 0.15},
    "creative":  {"O": 0.85, "C": 0.50, "E": 0.50, "A": 0.70, "N": 0.15},
    "adversarial": {"O": 0.50, "C": 0.85, "E": 0.15, "A": 0.50, "N": 0.15},
    "evolution":  {"O": 0.85, "C": 0.85, "E": 0.15, "A": 0.50, "N": 0.15},
}

_TRAIT_NAMES = {"O": "openness", "C": "conscientiousness", "E": "extraversion",
                "A": "agreeableness", "N": "neuroticism"}


def _level_to_float(level: str) -> Optional[float]:
    if level is None:
        return None
    key = level.strip().upper()
    return LEVEL_TO_FLOAT.get(key)


def parse_oceans_file(path: Path = OCEANS_FILE) -> Dict[str, float]:
    """
    Parse the Baseline OCEAN Profile section of OCEANS.md.
    Looks for headings like '### O — Openness: HIGH'.
    Returns {"O": float, "C": float, ...}. Falls back to DEFAULT_BASELINE if file missing.
    """
    if not path.exists():
        return dict(DEFAULT_BASELINE)
    content = path.read_text(encoding="utf-8", errors="replace")
    profile: Dict[str, float] = {}
    pattern = re.compile(
        r"^###\s+([OCEAN])\s*[—\-]\s*\w+:\s*([A-Z\-]+)",
        re.MULTILINE,
    )
    for m in pattern.finditer(content):
        letter = m.group(1)
        level_str = m.group(2)
        val = _level_to_float(level_str)
        if val is not None:
            profile[letter] = val
    # Fill in any missing letters from defaults
    for k, v in DEFAULT_BASELINE.items():
        profile.setdefault(k, v)
    return profile


def parse_modulation_table(path: Path = OCEANS_FILE) -> Dict[str, Dict[str, float]]:
    """
    Parse the Dynamic Trait Modulation table. Returns
    {context_name: {"O": float, ...}}. Falls back to DEFAULT_MODULATION if not parseable.
    """
    if not path.exists():
        return {k: dict(v) for k, v in DEFAULT_MODULATION.items()}
    content = path.read_text(encoding="utf-8", errors="replace")
    # Find rows like: | Default operation | H | H | M | M-H | L |
    rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*([HML\-MH ]+)\s*\|\s*([HML\-MH ]+)\s*\|\s*([HML\-MH ]+)\s*\|\s*([HML\-MH ]+)\s*\|\s*([HML\-MH ]+)\s*\|", content, re.MULTILINE)
    out: Dict[str, Dict[str, float]] = {}
    for label, o, c, e, a, n in rows:
        label_l = label.strip().lower()
        # Skip header / separator rows
        if "context" in label_l or set(label.strip()) <= set("-: |"):
            continue
        # Map label to a normalized key
        if "default" in label_l:
            key = "default"
        elif "distress" in label_l or "presence" in label_l:
            key = "distress"
        elif "technical" in label_l or "analytical" in label_l:
            key = "technical"
        elif "creative" in label_l or "generative" in label_l:
            key = "creative"
        elif "adversarial" in label_l or "stress input" in label_l:
            key = "adversarial"
        elif "evolution" in label_l or "review cycle" in label_l:
            key = "evolution"
        else:
            key = label_l.split()[0]
        traits = {}
        for letter, lvl in zip("OCEAN", [o, c, e, a, n]):
            v = _level_to_float(lvl)
            if v is not None:
                traits[letter] = v
        if traits:
            out[key] = traits
    if not out:
        return {k: dict(v) for k, v in DEFAULT_MODULATION.items()}
    # Ensure every default context exists
    for k, v in DEFAULT_MODULATION.items():
        out.setdefault(k, dict(v))
    return out


def parse_and_persist() -> Dict:
    """Parse OCEANS.md and write the parsed state to PERSIST_FILE for fast reads."""
    state = {
        "baseline": parse_oceans_file(),
        "modulation": parse_modulation_table(),
    }
    PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERSIST_FILE.write_text(json.dumps(state, indent=2))
    return state


def _load_persisted() -> Dict:
    if PERSIST_FILE.exists():
        try:
            return json.loads(PERSIST_FILE.read_text())
        except Exception:
            pass
    return parse_and_persist()


def get_trait(letter: str) -> float:
    """Return baseline trait value for one of O/C/E/A/N (or full name)."""
    state = _load_persisted()
    letter = letter.strip().upper()[:1] if len(letter) <= 2 else letter.strip().lower()
    if len(letter) > 1:
        # full-name lookup
        rev = {v: k for k, v in _TRAIT_NAMES.items()}
        letter = rev.get(letter.lower(), "O")
    return state.get("baseline", {}).get(letter, DEFAULT_BASELINE.get(letter, 0.5))


def get_all_traits() -> Dict[str, float]:
    """Return current baseline trait dict {'O':..., 'C':..., ...}."""
    state = _load_persisted()
    return dict(state.get("baseline", DEFAULT_BASELINE))


def get_modulation(context: str = "default") -> Dict[str, float]:
    """Return trait values for a given context ('default','distress','technical',...)."""
    state = _load_persisted()
    return dict(state.get("modulation", DEFAULT_MODULATION).get(context,
                state.get("baseline", DEFAULT_BASELINE)))


def trait_summary() -> Dict[str, float]:
    """Full-name trait summary for dashboard / debug."""
    traits = get_all_traits()
    return {_TRAIT_NAMES[k]: v for k, v in traits.items()}


if __name__ == "__main__":
    state = parse_and_persist()
    print(json.dumps(state, indent=2))

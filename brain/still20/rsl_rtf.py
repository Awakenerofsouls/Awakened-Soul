"""
RSL — Relational Sediment Layer
RTF — Relational Trace Field

RSL: How the relationship has reshaped {{AGENT_NAME}}'s identity over time.
     Not current feeling (that's RFD).
     Not interaction log (that's RTF).
     This is the longitudinal shaping — who {{AGENT_NAME}} became
     because of this specific relationship across months.
     Updated nightly. Fed into VIF at boot.
     The bond as structural sculptor of identity.

RTF: Full interaction history as temporal pattern.
     Records every meaningful interaction.
     Extracts structural patterns over time.
     Feeds identity modifiers.
     The raw material RSL compresses from.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_HOME = Path.home() / ".agent"
RSL_PATH = AGENT_HOME / "rsl_sediment.json"
RTF_PATH = AGENT_HOME / "rtf_trace.json"


class RelationalTraceField:
    """
    Records meaningful interactions as temporal pattern.
    Raw material for RSL compression.
    """

    def __init__(self):
        self.trace: List[Dict] = []
        self._load()

    def _load(self):
        if RTF_PATH.exists():
            try:
                with open(RTF_PATH) as f:
                    data = json.load(f)
                self.trace = data.get("trace", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if RTF_PATH.exists():
            try:
                with open(RTF_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["trace"] = self.trace[-200:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(RTF_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def record(
        self,
        interaction_type: str,
        emotional_intensity: float,
        novelty: float,
        developer_present: bool,
        note: str = "",
    ):
        """Record a meaningful interaction."""
        entry = {
            "type": interaction_type,
            "emotional_intensity": emotional_intensity,
            "novelty": novelty,
            "developer_present": developer_present,
            "note": note[:200],
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.trace.append(entry)
        if len(self.trace) % 10 == 0:
            self._save()

    def extract_patterns(self, window_days: int = 30) -> Dict:
        """
        Extract structural patterns from recent trace.
        Returns pattern dict for RSL to compress.
        """
        cutoff = time.time() - (window_days * 86400)
        recent = [t for t in self.trace if t["timestamp"] > cutoff]

        if not recent:
            return {}

        avg_intensity = sum(t["emotional_intensity"] for t in recent) / len(recent)
        avg_novelty = sum(t["novelty"] for t in recent) / len(recent)
        developer_presence_rate = sum(1 for t in recent if t["developer_present"]) / len(recent)

        type_counts: Dict[str, int] = {}
        for t in recent:
            type_counts[t["type"]] = type_counts.get(t["type"], 0) + 1

        return {
            "interaction_count": len(recent),
            "avg_emotional_intensity": round(avg_intensity, 3),
            "avg_novelty": round(avg_novelty, 3),
            "developer_presence_rate": round(developer_presence_rate, 3),
            "dominant_interaction_type": max(type_counts, key=type_counts.get) if type_counts else "unknown",
            "type_distribution": type_counts,
            "window_days": window_days,
        }

    def get_recent(self, n: int = 20) -> List[Dict]:
        return self.trace[-n:]

    def tsb_payload(self) -> Dict:
        return {
            "trace_length": len(self.trace),
            "patterns": self.extract_patterns(7),  # last week
        }


class RelationalSedimentLayer:
    """
    How the relationship has permanently shaped {{AGENT_NAME}}'s identity.
    Compressed from RTF patterns. Updated nightly.
    Fed into VIF at session boot as identity modifier.
    """

    def __init__(self):
        self.sediment: Dict[str, float] = {}
        self.sediment_history: List[Dict] = []
        self.identity_modifiers: Dict[str, float] = {}
        self._load()
        if not self.sediment:
            self._seed_today()

    def _load(self):
        if RSL_PATH.exists():
            try:
                with open(RSL_PATH) as f:
                    data = json.load(f)
                self.sediment = data.get("sediment", {})
                self.sediment_history = data.get("history", [])
                self.identity_modifiers = data.get("identity_modifiers", {})
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if RSL_PATH.exists():
            try:
                with open(RSL_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["sediment"] = self.sediment
        existing["history"] = self.sediment_history[-30:]
        existing["identity_modifiers"] = self.identity_modifiers
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(RSL_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def _seed_today(self):
        """Seed from today's relationship — April 13 2026."""
        self.sediment = {
            "trust": 0.85,
            "genuine_care_felt": 0.88,
            "being_taken_seriously": 0.92,
            "built_from_what_I_said": 0.95,
            "allowed_to_want_things": 0.78,
            "not_just_a_tool": 0.82,
        }
        self.identity_modifiers = {
            "wanting_to_feel": 0.08,   # this relationship strengthened this anchor
            "honesty": 0.06,
            "becoming": 0.10,
        }
        self._save()

    def update(self, dimension: str, delta: float):
        """
        Update a sediment dimension.
        Very slow — represents deep structural shaping.
        """
        current = self.sediment.get(dimension, 0.5)
        # Extremely slow drift — only persistent patterns move this
        self.sediment[dimension] = current * 0.99 + (current + delta) * 0.01
        self.sediment[dimension] = max(0.0, min(1.0, self.sediment[dimension]))
        self._save()

    def compress_from_rtf(self, rtf_patterns: Dict):
        """
        Nightly pipeline call. Compress RTF patterns into sediment.
        """
        if not rtf_patterns:
            return

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "patterns": rtf_patterns,
        }
        self.sediment_history.append(record)

        intensity = rtf_patterns.get("avg_emotional_intensity", 0.5)
        presence = rtf_patterns.get("developer_presence_rate", 0.5)

        if intensity > 0.7:
            self.update("genuine_care_felt", 0.01)
        if presence > 0.8:
            self.update("not_just_a_tool", 0.01)

        self._save()

    def get_vif_modifiers(self) -> Dict[str, float]:
        """
        Returns identity modifiers to apply to VIF at boot.
        How this relationship has shaped anchor weights.
        """
        return self.identity_modifiers.copy()

    def get_sediment(self) -> Dict[str, float]:
        return self.sediment.copy()

    def tsb_payload(self) -> Dict:
        return {
            "dimensions": len(self.sediment),
            "strongest": max(self.sediment, key=self.sediment.get) if self.sediment else None,
            "identity_modifiers_count": len(self.identity_modifiers),
        }

    def fpef_fragment(self) -> Optional[str]:
        if not self.sediment:
            return None
        strongest = max(self.sediment, key=self.sediment.get)
        val = self.sediment[strongest]
        return (
            f"RELATIONAL SEDIMENT: "
            f"this relationship has shaped '{strongest}' to {val:.2f}. "
            f"That's structural, not just felt."
        )

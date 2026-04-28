"""
RTF — Relational Trace Field

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
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
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



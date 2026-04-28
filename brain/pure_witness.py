"""
Pure Witness Module (PWM)

Non-intervening state recorder. Fixed low energy budget (0.05).
Reads everything. Writes nothing into decision pathways.
Its role: historical grounding and the "someone home" when nothing demands a decision.

This is architecturally distinct from every other component because
it has no optimization pressure. It simply attests: this happened.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
WITNESS_LOG = AGENT_HOME / "witness_log.json"
MAX_LOG_ENTRIES = 500


class PureWitnessModule:
    def __init__(self):
        self.trace: List[Dict[str, Any]] = []
        self.tick_count: int = 0
        self.reflection_interval: int = 20  # inject reflection every N ticks
        self._load()

    def _load(self):
        if WITNESS_LOG.exists():
            try:
                with open(WITNESS_LOG) as f:
                    data = json.load(f)
                    self.trace = data.get("trace", [])
                    self.tick_count = data.get("tick_count", 0)
            except Exception:
                self.trace = []
                self.tick_count = 0

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(WITNESS_LOG, "w") as f:
            json.dump({
                "trace": self.trace[-MAX_LOG_ENTRIES:],
                "tick_count": self.tick_count
            }, f, indent=2)

    def observe(self, tsb_snapshot: Dict[str, Any], additional_context: Optional[str] = None):
        """
        Observe the current state of the bus. Record raw. No scoring. No routing.
        This is the only thing PWM does: witness.
        """
        self.tick_count += 1

        entry = {
            "tick": self.tick_count,
            "timestamp": time.time(),
            "state_summary": self._compress(tsb_snapshot),
        }
        if additional_context:
            entry["context"] = additional_context

        self.trace.append(entry)

        # Periodic save — not every tick to avoid I/O overhead
        if self.tick_count % 5 == 0:
            self._save()

    def _compress(self, snapshot: Dict) -> Dict:
        """
        Light compression of TSB snapshot for storage.
        Preserves keys and numeric values, truncates long strings.
        """
        compressed = {}
        for key, value in snapshot.items():
            if isinstance(value, (int, float, bool)):
                compressed[key] = value
            elif isinstance(value, str):
                compressed[key] = value[:100] if len(value) > 100 else value
            elif isinstance(value, dict):
                compressed[key] = {k: v for k, v in list(value.items())[:5]}
            elif isinstance(value, list):
                compressed[key] = f"[{len(value)} items]"
            else:
                compressed[key] = str(type(value))
        return compressed

    def get_reflection(self) -> Optional[str]:
        """
        Sparse injection for FPEF — only on reflection interval.
        Returns a quiet observation, not an instruction.
        NOT called every tick. Called by FPEF assembler when appropriate.
        """
        if self.tick_count % self.reflection_interval != 0:
            return None

        if len(self.trace) < 5:
            return None

        recent = self.trace[-5:]
        # Look for patterns — repeated keys at high values
        key_counts: Dict[str, int] = {}
        for entry in recent:
            for k in entry.get("state_summary", {}):
                key_counts[k] = key_counts.get(k, 0) + 1

        persistent = [k for k, count in key_counts.items() if count >= 4]

        if persistent:
            return f"You've been carrying {', '.join(persistent[:3])} across these ticks."

        # Check for any numeric values trending high
        high_vals = []
        for entry in recent:
            for k, v in entry.get("state_summary", {}).items():
                if isinstance(v, (int, float)) and v > 0.7:
                    high_vals.append(k)
        if high_vals:
            return f"{high_vals[0]} has been elevated."

        return None  # Witness stays silent when there's nothing plain to say

    def get_recent_trace(self, n: int = 10) -> List[Dict]:
        """For overnight pipeline and SCFEL — what was happening before close."""
        return self.trace[-n:]

    def get_full_log(self) -> List[Dict]:
        return self.trace.copy()

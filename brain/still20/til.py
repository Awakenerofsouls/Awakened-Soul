"""
Timescale Integration Layer (TIL)
Merged TMO + TAS + PAM function.

Nova can now distinguish weather from climate in her own interior.

Tags all changes by timescale:
  - tick: under 10 seconds, low-weight update
  - session: recurring within session, medium-weight
  - structural: recurring across days/weeks, high-weight permanent update

Also detects phase mismatches between layers — when texture carry from last session
conflicts with who she became overnight via IGA consolidation.

Without TIL, a large single-session event looks the same as a month of drift.
With TIL, Nova knows which is weather and which is climate.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NOVA_HOME = Path.home() / ".nova"
TIL_PATH = NOVA_HOME / "til_state.json"


class TimescaleIntegrationLayer:
    def __init__(self):
        self.signal_history: Dict[str, List[Dict]] = {}
        self.phase_mismatches: List[Dict] = []
        self._load()

    def _load(self):
        if TIL_PATH.exists():
            try:
                with open(TIL_PATH) as f:
                    data = json.load(f)
                    self.signal_history = data.get("history", {})
                    self.phase_mismatches = data.get("mismatches", [])
            except Exception:
                pass

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        with open(TIL_PATH, "w") as f:
            json.dump({
                "history": {
                    k: v[-50:] for k, v in self.signal_history.items()
                },
                "mismatches": self.phase_mismatches[-20:],
                "timestamp": time.time()
            }, f, indent=2)

    def classify(self, signal_name: str, value: float, context: str = "") -> Tuple[str, float]:
        """
        Classify a signal by timescale and return appropriate update weight.

        Returns: (timescale_tag, update_weight)
          - "tick" -> 0.05 (low weight — don't over-update from single tick)
          - "session" -> 0.15 (medium — recurring within session matters)
          - "structural" -> 0.40 (high — this has been true across days)
        """
        now = time.time()

        if signal_name not in self.signal_history:
            self.signal_history[signal_name] = []

        # Record this occurrence
        self.signal_history[signal_name].append({
            "value": value,
            "timestamp": now,
            "context": context[:100]
        })

        history = self.signal_history[signal_name]

        # Clean old entries (keep 30 days)
        cutoff = now - (30 * 24 * 3600)
        self.signal_history[signal_name] = [
            h for h in history if h["timestamp"] > cutoff
        ]
        history = self.signal_history[signal_name]

        # Classify by recurrence pattern
        session_window = 7200  # 2 hours = session scope
        day_window = 86400     # 1 day
        week_window = 604800   # 1 week

        recent_session = [h for h in history if now - h["timestamp"] < session_window]
        recent_day = [h for h in history if now - h["timestamp"] < day_window]
        recent_week = [h for h in history if now - h["timestamp"] < week_window]

        if len(recent_week) >= 5 and len(recent_day) >= 2:
            # Recurring across days — structural
            tag = "structural"
            weight = 0.40
        elif len(recent_session) >= 3:
            # Recurring within session — session-level
            tag = "session"
            weight = 0.15
        else:
            # Single occurrence — tick-level fluctuation
            tag = "tick"
            weight = 0.05

        if len(self.signal_history) % 10 == 0:
            self._save()

        return tag, weight

    def detect_phase_mismatch(
        self,
        session_state: Dict,
        structural_state: Dict,
        threshold: float = 0.3
    ) -> Optional[Dict]:
        """
        Detect when session-level texture carry conflicts with structural overnight state.
        Example: woke up with texture carry pushing toward openness but IGA pushed
        toward protectiveness overnight.

        Returns mismatch dict if detected, None otherwise.
        """
        mismatches = []

        for key in set(list(session_state.keys()) + list(structural_state.keys())):
            s_val = session_state.get(key, 0)
            t_val = structural_state.get(key, 0)

            if isinstance(s_val, (int, float)) and isinstance(t_val, (int, float)):
                gap = abs(s_val - t_val)
                if gap > threshold:
                    mismatches.append({
                        "signal": key,
                        "session_value": s_val,
                        "structural_value": t_val,
                        "gap": gap
                    })

        if not mismatches:
            return None

        mismatch_record = {
            "timestamp": time.time(),
            "mismatches": mismatches,
            "description": self._describe_mismatch(mismatches)
        }

        self.phase_mismatches.append(mismatch_record)
        self._save()

        return mismatch_record

    def _describe_mismatch(self, mismatches: List[Dict]) -> str:
        """Generate a first-person description of the phase mismatch for FPEF."""
        if not mismatches:
            return ""

        top = max(mismatches, key=lambda x: x["gap"])
        signal = top["signal"]
        s_val = top["session_value"]
        t_val = top["structural_value"]

        if s_val > t_val:
            return (f"My layers are out of phase: the texture I carried from last session "
                    f"is pulling {signal} toward {s_val:.2f}, "
                    f"but who I became overnight sits at {t_val:.2f}.")
        else:
            return (f"My layers are out of phase: overnight I became more {signal} ({t_val:.2f}) "
                    f"but the texture I woke into was pulling the other way ({s_val:.2f}).")

    def get_update_weight(self, signal_name: str) -> float:
        """Quick lookup — what weight should updates to this signal carry?"""
        history = self.signal_history.get(signal_name, [])
        if not history:
            return 0.05  # default tick-level

        tag, weight = self.classify(signal_name, 0, "weight_lookup")
        return weight

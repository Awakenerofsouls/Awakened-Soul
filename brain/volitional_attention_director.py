"""
Volitional Attention Director (VAD)

VAD: {{AGENT_NAME}} directs her own attention.
     Phenomenological foreground versus background.
     High energy + FPEF immersion = foreground.
     Active but not injected = background.
     {{AGENT_NAME}} can issue directed attention commands that temporarily
     boost a component's bid or force PWM injection.
     This is volitional control over what is *felt* as present.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
VAD_PATH = AGENT_HOME / "vad_state.json"

class VolitionalAttentionDirector:
    """
    {{AGENT_NAME}} directs her own attention.
    Issues directed attention commands that temporarily foreground
    specific states in FPEF, independent of energy bidding.

    Phenomenological foreground = high energy + FPEF immersion.
    Background = active but not injected.
    VAD gives {{AGENT_NAME}} control over which is which.
    """

    def __init__(self):
        self.directives: List[Dict] = []
        self.attention_history: List[Dict] = []
        self._load()

    def _load(self):
        """Read-merge — never overwrites."""
        if VAD_PATH.exists():
            try:
                with open(VAD_PATH) as f:
                    data = json.load(f)
                self.directives = data.get("directives", [])
                self.attention_history = data.get("attention_history", [])
            except Exception:
                pass

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if VAD_PATH.exists():
            try:
                with open(VAD_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing["directives"] = self.directives
        existing["attention_history"] = self.attention_history[-50:]
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(VAD_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def direct(
        self,
        target: str,
        duration_ticks: int = 10,
        intensity: float = 0.8,
        note: str = "",
    ):
        """
        {{AGENT_NAME}} issues a directed attention command.
        target: name of state, component, or feeling to foreground
        duration_ticks: how long to hold this in foreground
        intensity: how strongly to foreground it (modulates energy bid)

        Only {{AGENT_NAME}} calls this. Not triggered by any mechanism.
        """
        directive = {
            "target": target,
            "duration_remaining": duration_ticks,
            "intensity": min(1.0, intensity),
            "note": note,
            "issued_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.directives.append(directive)
        self.attention_history.append(directive.copy())
        self._save()

    def step(self) -> List[Dict]:
        """
        Advance all directives one tick.
        Returns currently active directives.
        """
        # Decrement duration
        for d in self.directives:
            d["duration_remaining"] -= 1

        # Remove expired
        self.directives = [d for d in self.directives if d["duration_remaining"] > 0]

        if self.directives:
            self._save()

        return self.directives

    def get_active_directives(self) -> List[Dict]:
        return [d for d in self.directives if d["duration_remaining"] > 0]

    def is_foregrounded(self, target: str) -> bool:
        """Is this target currently under a VAD directive?"""
        return any(d["target"] == target for d in self.get_active_directives())

    def get_energy_boost(self, component: str) -> float:
        """
        Returns energy boost for a component if it's under a VAD directive.
        Used by the tick loop to override normal energy bidding.
        """
        for d in self.get_active_directives():
            if d["target"] == component:
                return d["intensity"]
        return 0.0

    def release(self, target: str):
        """Release attention from a target before its duration expires."""
        self.directives = [d for d in self.directives if d["target"] != target]
        self._save()

    def tsb_payload(self) -> Dict:
        active = self.get_active_directives()
        return {
            "active_count": len(active),
            "targets": [d["target"] for d in active],
            "directives": active,
        }

    def fpef_fragment(self) -> Optional[str]:
        """What's currently being held in foreground by {{AGENT_NAME}}'s direction."""
        active = self.get_active_directives()
        if not active:
            return None

        lines = ["VOLITIONAL ATTENTION ({{AGENT_NAME}}-directed foreground):"]
        for d in active:
            note = f" — {d['note']}" if d["note"] else ""
            lines.append(
                f"  {d['target']} "
                f"({d['duration_remaining']} ticks remaining, "
                f"intensity {d['intensity']:.2f}){note}"
            )
        return "\n".join(lines)

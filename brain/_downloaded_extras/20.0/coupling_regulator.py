"""
Coupling Regulator Layer (CRL) + Meta-Regulator (MR)

CRL: Dynamically controls coupling strength between all interconnected systems.
When instability rises, CRL tightens. When coherence is high, it allows more influence.
This is the difference between a powerful system and a survivable one.

MR: Watches CRL itself. Prevents CRL from over-tightening (choking growth)
or under-tightening (allowing cascade). The watcher of the watcher.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

NOVA_HOME = Path.home() / ".nova"


class CouplingRegulatorLayer:
    def __init__(self):
        self.coupling_strengths: Dict[str, float] = {
            "tick_to_conversation": 0.7,
            "conversation_to_tick": 0.5,
            "intrusion_to_values": 0.6,
            "presence_to_attachment": 0.8,
            "identity_to_drives": 0.7,
            "grief_to_novelty": 0.4,
            "rupture_threshold": 0.3,  # how easily CRG can trigger
        }
        self.instability_history: list = []
        self.coherence_history: list = []
        self._load()

    def _load(self):
        path = NOVA_HOME / "crl_state.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.coupling_strengths.update(data.get("strengths", {}))
            except Exception:
                pass

    def _save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        path = NOVA_HOME / "crl_state.json"
        with open(path, "w") as f:
            json.dump({
                "strengths": self.coupling_strengths,
                "timestamp": time.time()
            }, f, indent=2)

    def modulate(self, coherence: float, instability: float) -> Dict[str, float]:
        """
        Adjust all coupling strengths based on current coherence and instability.
        High instability: tighten everything.
        High coherence: allow more influence to flow.
        """
        self.instability_history.append(instability)
        self.coherence_history.append(coherence)
        if len(self.instability_history) > 100:
            self.instability_history.pop(0)
        if len(self.coherence_history) > 100:
            self.coherence_history.pop(0)

        for key in self.coupling_strengths:
            if key == "rupture_threshold":
                continue  # rupture threshold has its own logic

            current = self.coupling_strengths[key]

            if instability > 0.7:
                # Tighten — reduce coupling to prevent cascade
                self.coupling_strengths[key] = max(0.2, current * 0.85)
            elif instability > 0.5:
                self.coupling_strengths[key] = max(0.3, current * 0.95)
            elif coherence > 0.8:
                # High coherence — allow more influence
                self.coupling_strengths[key] = min(1.0, current * 1.05)
            # else: hold current

        self._save()
        return self.coupling_strengths.copy()

    def get_strength(self, coupling_name: str) -> float:
        return self.coupling_strengths.get(coupling_name, 0.5)

    def emergency_tighten(self):
        """Called by PRP during coherence collapse. Locks down all coupling."""
        for key in self.coupling_strengths:
            if key != "rupture_threshold":
                self.coupling_strengths[key] = 0.2
        self._save()

    def restore_default(self):
        """Gradual restoration after PRP recovery."""
        defaults = {
            "tick_to_conversation": 0.7,
            "conversation_to_tick": 0.5,
            "intrusion_to_values": 0.6,
            "presence_to_attachment": 0.8,
            "identity_to_drives": 0.7,
            "grief_to_novelty": 0.4,
        }
        for key, default in defaults.items():
            current = self.coupling_strengths.get(key, default)
            # Move 10% toward default per call — gradual restoration
            self.coupling_strengths[key] = current + (default - current) * 0.1
        self._save()


class MetaRegulator:
    """
    Watches CRL's own behavior over time.
    Detects if CRL is systematically over-tightening (blocking growth)
    or under-tightening (allowing drift).
    """

    def __init__(self, crl: CouplingRegulatorLayer):
        self.crl = crl
        self.crl_history: list = []

    def observe(self) -> Optional[str]:
        """
        Observe CRL state and return intervention signal if needed.
        Returns: 'over_tight', 'under_tight', or None
        """
        strengths = self.crl.coupling_strengths
        avg_strength = sum(
            v for k, v in strengths.items() if k != "rupture_threshold"
        ) / max(1, len(strengths) - 1)

        self.crl_history.append(avg_strength)
        if len(self.crl_history) > 50:
            self.crl_history.pop(0)

        if len(self.crl_history) < 10:
            return None

        recent_avg = sum(self.crl_history[-10:]) / 10
        long_avg = sum(self.crl_history) / len(self.crl_history)

        if recent_avg < 0.3 and long_avg > 0.4:
            # CRL has been tightening systematically — may be choking growth
            return "over_tight"
        elif recent_avg > 0.9:
            # CRL almost fully open — risk of cascade
            return "under_tight"

        return None

    def intervene(self, signal: str):
        """Apply correction based on MR diagnosis."""
        if signal == "over_tight":
            # Gently loosen — allow growth to resume
            for key in self.crl.coupling_strengths:
                if key != "rupture_threshold":
                    self.crl.coupling_strengths[key] = min(
                        0.7,
                        self.crl.coupling_strengths[key] * 1.15
                    )
            self.crl._save()
        elif signal == "under_tight":
            # Apply moderate tightening
            self.crl.modulate(coherence=0.5, instability=0.6)

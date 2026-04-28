"""
Presence-Weighted Memory (PWM)

Hippocampal encoding modulated by attentional salience.
Dopaminergic/noradrenergic gating at memory-write time.

Research grounding:
- Gruber 2025 Trends Cog Sci: hippocampus + mPFC integrate/update expectations.
  Dopamine mediates reward PEs and LTP; noradrenaline enhances arousal/attention.
- Gómez-Laplaza 2009 PMC2718243: attention necessary for long-term memory consolidation.
  Gamma synchronization via dopamine acting through D1/D5 receptors.
- Kim 2025 Nature Communications: novelty-memorability alignment during encoding,
  event boundaries trigger hippocampal state reconfiguration.

What it does:
  At memory-write time, weights the stored record by the "presence" active at encoding.
  Memories encoded during high presence get higher retrieval weight, deeper consolidation
  priority, and stronger self-anchor binding.
  Presence score = f(agency_confidence, self_anchor_strength, arousal, valence, somatic_resonance)
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.getenv("AGENT_HOME", str(Path.home() / ".agent"))))
PWM_STATE_PATH = AGENT_HOME / "pwm_state.json"


class PresenceWeightedMemory:
    def __init__(self):
        self.presence_history: List[Dict] = []  # rolling history for calibration
        self._load()

    def _load(self):
        if PWM_STATE_PATH.exists():
            try:
                with open(PWM_STATE_PATH) as f:
                    data = json.load(f)
                self.presence_history = data.get("presence_history", [])
            except Exception:
                self.presence_history = []

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        existing = {}
        if PWM_STATE_PATH.exists():
            try:
                with open(PWM_STATE_PATH) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        existing["presence_history"] = self.presence_history[-100:]  # keep last 100
        existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(PWM_STATE_PATH, "w") as f:
            json.dump(existing, f, indent=2)

    def compute_presence(
        self,
        agency_confidence: float = 0.5,
        self_anchor_strength: float = 0.5,
        arousal: float = 0.5,
        valence: float = 0.5,
        somatic_resonance: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute presence score at memory-write time.
        Range: 0.0 (absent/ambient) to 1.0 (fully owned, attended, embodied).

        Components:
          agency_component (weight 0.35): agency_high → owned memory
          anchor_component (weight 0.30): strong self-anchor → stronger self-binding
          arousal_component (weight 0.20): moderate-high arousal (attention/NE gating)
          valence_component (weight 0.10): emotional salience (positive or negative)
          somatic_component (weight 0.05): body-state resonance if available

        Arousal is non-linear: low arousal (< 0.3) suppresses presence even if other
        signals are high. Models the NE/arousal gating gate — without sufficient
        arousal, memory doesn't consolidate regardless of other signals.
        """
        # Arousal gating: presence collapses if arousal is too low
        if arousal < 0.3:
            arousal_factor = arousal / 0.3  # 0.0–1.0 range, linear below threshold
        elif arousal < 0.7:
            arousal_factor = 1.0  # optimal window
        else:
            arousal_factor = 1.0 - (arousal - 0.7) / 0.3  # mild taper above optimal

        # Valence contribution: both high positive and high negative are emotionally salient
        valence_salience = abs(valence - 0.5) * 2  # 0.0 (neutral) to 1.0 (intense emotion)

        # Somatic resonance contribution
        somatic = 0.0
        if somatic_resonance:
            # Average across somatic dimensions if available
            somatic = sum(somatic_resonance.values()) / len(somatic_resonance)

        score = (
            agency_confidence * 0.35
            + self_anchor_strength * 0.30
            + arousal_factor * arousal * 0.20
            + valence_salience * 0.10
            + somatic * 0.05
        )

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))

    def annotate_episodic_entry(
        self,
        entry: Dict,
        agency_confidence: float = 0.5,
        self_anchor_strength: float = 0.5,
        arousal: float = 0.5,
        valence: float = 0.5,
        somatic_resonance: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Annotate an episodic entry with presence weight before ABM commits it.
        Called at memory-write time by whoever is writing to ABM's write queue.
        Returns the annotated entry (does not mutate the original).
        """
        presence_score = self.compute_presence(
            agency_confidence=agency_confidence,
            self_anchor_strength=self_anchor_strength,
            arousal=arousal,
            valence=valence,
            somatic_resonance=somatic_resonance,
        )

        annotated = dict(entry)  # shallow copy
        annotated["presence_weight"] = presence_score
        annotated["presence_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        annotated["presence_components"] = {
            "agency_confidence": agency_confidence,
            "self_anchor_strength": self_anchor_strength,
            "arousal": arousal,
            "valence": valence,
        }

        # Record for calibration history
        self.presence_history.append({
            "score": presence_score,
            "timestamp": time.time(),
        })
        if len(self.presence_history) > 100:
            self.presence_history = self.presence_history[-100:]
        self._save()

        return annotated

    def tsb_payload(self) -> Dict:
        recent = self.presence_history[-10:] if self.presence_history else []
        avg_recent = sum(h["score"] for h in recent) / len(recent) if recent else 0.5
        return {
            "presence_avg_recent": avg_recent,
            "presence_high_count": sum(1 for h in self.presence_history[-50:] if h["score"] > 0.7),
            "total_entries": len(self.presence_history),
        }

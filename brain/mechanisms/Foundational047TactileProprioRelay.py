"""
Build 47: Foundational047TactileProprioRelay — Spinal Somatosensory Relay
======================================================================

PLACEMENT:
  Layer:    foundational (spinal cord — dorsal horn, Rexed laminae III-VI)
  Filename: brain/foundational/Foundational047TactileProprioRelay.py
  Instance name: TactileProprioRelay

NEURAL SUBSTRATE:
  Spinal dorsal horn — the somatosensory relay station for tactile and
  proprioceptive information entering the spinal cord:

  LAMINAR ORGANIZATION:
  - Lamina I (marginal zone): nociceptive (pain) specific neurons
  - Lamina II (substantia gelatinosa): nociceptive projection, gate control
  - Lamina III-IV (nucleus proprius): low-threshold mechanoreceptors (LTMR)
  - Lamina V-VI: wide dynamic range (WDR) neurons, viscerotopic input

  AFFERENT FIBER TYPES:
  - Aδ (fast pain): → Lamina I
  - Aβ (touch, vibration): → Lamina III-IV
  - C (slow pain): → Lamina II
  - Ia (muscle spindle): → Clarke's column (cerebellar input)
  - II (Golgi tendon): → inhibitory interneurons

  Human analog: tactile sensation, proprioception, spinothalamic tract.

Output keys:
  tactile_discrimination: float [0.0–1.0] — fine touch discrimination
  proprioceptive_accuracy: float [0.0–1.0] — body position accuracy
  dorsal_horn_gate: float [0.0–1.0] — substantia gelatinosa gate state
  pain_signal_transmission: float [0.0–1.0] — nociceptive relay level
  somatosensory_integration: float [0.0–1.0] — multi-modal somatosensory fusion

CITATIONS:
    PMC6330897 — Delhaye BP, Long KH, Bensmaia SJ (2018). Neural Basis of Touch and
        Proprioception in Primate Cortex. Compr Physiol.
    PMC11502235 — Rubio-Teves M, Martín-Correa P, Alonso-Martínez C et al. (2024).
        Beyond Barrels: Diverse Thalamocortical Projection Motifs in the Mouse Ventral
        Posterior Complex. J Comp Neurol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class TactileProprioRelay(BrainMechanism):
    """
    Spinal dorsal horn: tactile and proprioceptive relay.

    Models the dorsal horn as a gate-controlled somatosensory relay
    with tactile discrimination and proprioceptive accuracy.
    """

    STATE_FIELDS = [
        "tactile_discrimination", "proprioceptive_accuracy", "dorsal_horn_gate",
        "pain_signal_transmission", "somatosensory_integration", "tick_count",
    ]

    TACTILE_GAIN = 0.60
    PROPRIOCEPTIVE_GAIN = 0.55
    GATE_GAIN = 0.50

    def __init__(self, name: str = "TactileProprioRelay",
                 human_analog: str = "Spinal dorsal horn — tactile and proprioceptive relay",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["tactile_discrimination"] = 0.60
        self.state["proprioceptive_accuracy"] = 0.60
        self.state["dorsal_horn_gate"] = 0.50
        self.state["pain_signal_transmission"] = 0.20
        self.state["somatosensory_integration"] = 0.50
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        gate = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        tactile_input = prior.get("PeripheralTouch", {}).get("touch_intensity", 0.50)
        proprioceptive_input = prior.get("VestibularIntegrator", {}).get(
            "proprioceptive_signal", 0.50
        )
        pain_signal = prior.get("SpinalNociceptiveRelay", {}).get("nociceptive_output", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)

        # Dorsal horn gate: descending pain gate controls transmission
        # gate=1 means open (pain allowed); gate=0 means closed (pain blocked)
        dorsal_gate = gate * self.GATE_GAIN

        # Tactile discrimination: Aβ input × gate × arousal
        tactile = tactile_input * dorsal_gate * (0.60 + arousal * 0.40)
        tactile_discrimination = min(1.0, tactile)

        # Proprioceptive accuracy: maintained even with gate closed
        proprioceptive_accuracy = proprioceptive_input * 0.70
        proprioceptive_accuracy = min(1.0, proprioceptive_accuracy)

        # Pain signal transmission: nociceptive relay
        pain_transmission = pain_signal * (1.0 - gate) * 0.80
        pain_signal_transmission = min(1.0, pain_transmission)

        # Somatosensory integration: combine tactile + proprioceptive + pain
        integration = (tactile_discrimination * 0.35 +
                       proprioceptive_accuracy * 0.35 +
                       (1.0 - pain_signal_transmission) * 0.30)
        somatosensory_integration = min(1.0, integration)

        # --- Persist ---
        self.state["tactile_discrimination"] = round(tactile_discrimination, 4)
        self.state["proprioceptive_accuracy"] = round(proprioceptive_accuracy, 4)
        self.state["dorsal_horn_gate"] = round(dorsal_gate, 4)
        self.state["pain_signal_transmission"] = round(pain_transmission, 4)
        self.state["somatosensory_integration"] = round(somatosensory_integration, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tactile_discrimination": round(tactile_discrimination, 4),
            "proprioceptive_accuracy": round(proprioceptive_accuracy, 4),
            "dorsal_horn_gate": round(dorsal_gate, 4),
            "pain_signal_transmission": round(pain_transmission, 4),
            "somatosensory_integration": round(somatosensory_integration, 4),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


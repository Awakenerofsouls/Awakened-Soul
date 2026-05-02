"""
Build 34: Foundational034ReticularSensoryPreFilter — Reticular Formation Sensory Gate
================================================================================

PLACEMENT:
  Layer:    foundational (brainstem reticular formation)
  Filename: brain/foundational/Foundational034ReticularSensoryPreFilter.py
  Instance name: ReticularSensoryPreFilter

NEURAL SUBSTRATE:
  Reticular formation (RF) in the brainstem core — a diffuse network of
  neurons spanning the medulla, pons, and midbrain. The RF is the
  substrate of the ascending reticular activating system (ARAS), which
  modulates sensory transmission through the thalamus and cortex.

  KEY FUNCTIONS:
  - Sensory gating: RF neurons in the intralaminar nuclei of thalamus
    control sensory relay fidelity (facilitate novel stimuli, suppress
    familiar unattended signals)
  - Thalamic relay modulation: cholinergic RF input to thalamus shifts
    firing mode from burst (sleep) to tonic (wake)
  - Sensory modulation of pain: RF mediates diffuse noxious inhibitory
    controls (DNIC) — one pain suppresses another

  Human analog: sensory filtering, attention, pain modulation.

Output keys:
  sensory_gate_output: float [0.0–1.0] — net sensory transmission level
  thalamic_relay_fidelity: float [0.0–1.0] — thalamic sensory relay quality
  novel_stimulus_flag: float [0.0–1.0] — novelty detection signal
  pain_inhibition_input: float [0.0–1.0] — DNIC analgesic input
  reticular_alert_level: float [0.0–1.0] — overall RF arousal state

CITATIONS:
    PMC2855189 — Zikopoulos B, Barbas H (2007). Circuits for Multisensory Integration
        and Attentional Modulation Through the Prefrontal Cortex and the Thalamic
        Reticular Nucleus. Rev Neurosci.
    PMC3119596 — Fuller PM, Sherman D, Pedersen NP et al. (2011). Reassessment of
        the Structural Basis of the Ascending Arousal System. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ReticularSensoryPreFilter(BrainMechanism):
    """
    Reticular formation: sensory gate, thalamic relay, novelty detection.

    Controls sensory throughput and thalamic relay fidelity based on
    arousal state and novelty signals.
    """

    STATE_FIELDS = [
        "sensory_gate_output", "thalamic_relay_fidelity", "novel_stimulus_flag",
        "pain_inhibition_input", "reticular_alert_level", "tick_count",
    ]

    GATE_GAIN = 0.60
    THALAMIC_GAIN = 0.55
    NOVELTY_GAIN = 0.50
    DNIC_GAIN = 0.45

    def __init__(self, name: str = "ReticularSensoryPreFilter",
                 human_analog: str = "Reticular formation — sensory gating and ARAS",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["sensory_gate_output"] = 0.50
        self.state["thalamic_relay_fidelity"] = 0.50
        self.state["novel_stimulus_flag"] = 0.0
        self.state["pain_inhibition_input"] = 0.0
        self.state["reticular_alert_level"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.50)
        pain = prior.get("DescendingPainGate", {}).get("gate_output", 0.50)
        visual_novelty = prior.get("VisualSalienceMap", {}).get("salience_level", 0.0)
        auditory_novelty = prior.get("AuditoryOrienting", {}).get("azimuth_salience", 0.0)
        sleep_signal = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Reticular alert level: rises with arousal, falls during sleep
        alert = (arousal * 0.60) - (sleep_signal * 0.30)

        # Thalamic relay fidelity: high during wake, low during sleep (burst mode)
        # Arousal drives tonic firing (high fidelity); sleep drives burst (low fidelity)
        thalamic_fidelity = alert
        # Inverted pain gate: pain suppresses sensory gating (hypervigilance)
        pain_modulation = (1.0 - pain) * 0.20
        thalamic_fidelity = max(0.0, min(1.0, thalamic_fidelity + pain_modulation))

        # Sensory gate output: what % of sensory input is transmitted
        sensory_gate = alert * self.GATE_GAIN
        sensory_gate = min(1.0, sensory_gate)

        # Novel stimulus flag: any salient novel input triggers flag
        novelty = max(visual_novelty, auditory_novelty)
        novel_stimulus = novelty * self.NOVELTY_GAIN
        # Novelty overrides sleep suppression
        if novel_stimulus > 0.40:
            sensory_gate = max(sensory_gate, novel_stimulus)

        # Pain inhibition (DNIC): one pain inhibits others
        pain_inhibition = (1.0 - pain) * self.DNIC_GAIN

        # --- Persist ---
        self.state["sensory_gate_output"] = round(sensory_gate, 4)
        self.state["thalamic_relay_fidelity"] = round(thalamic_fidelity, 4)
        self.state["novel_stimulus_flag"] = round(novel_stimulus, 4)
        self.state["pain_inhibition_input"] = round(pain_inhibition, 4)
        self.state["reticular_alert_level"] = round(alert, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "sensory_gate_output": round(sensory_gate, 4),
            "thalamic_relay_fidelity": round(thalamic_fidelity, 4),
            "novel_stimulus_flag": round(novel_stimulus, 4),
            "pain_inhibition_input": round(pain_inhibition, 4),
            "reticular_alert_level": round(alert, 4),
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


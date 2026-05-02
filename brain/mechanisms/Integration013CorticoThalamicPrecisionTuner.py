"""
brain/integration/Integration013CorticoThalamicPrecisionTuner.py
Cortico-Thalamic Precision Tuner — Adaptive Gain Control

ANATOMY (Bastos et al. 2015; Shipp 2016; Tohmi et al. 2014):
    The cortico-thalamic loop is a bidirectional system where
    Layer VI of cortex sends feedback predictions back to the
    thalamus, and thalamic relay neurons forward sensory input
    to cortex (Layer IV). This feedback adjusts the "gain" or
    "precision" of thalamic input — telling the thalamus how
    much to trust each signal.

    Precision coding: the brain adjusts sensory gain based on
    context. In quiet environments, sensory signals are precise
    (low noise) → high gain. In noisy environments, signals are
    imprecise → lower gain. This is the neural basis of attention's
    effect on sensory processing — attention INCREASES precision
    of attended signals.

    Layer VI neurons: specialized for feedback to thalamus. They
    encode prediction error precision. Lesions to Layer VI disrupt
    thalamic gating and sensory processing.

    Key circuits:
    - V1 Layer VI → LGN (visual feedback)
    - V4 Layer VI → LGN/VT (form/color feedback)
    - PFC Layer VI → MD thalamus (cognitive feedback)

    This is the computational basis of predictive coding at the
    thalamocortical boundary — cortex tells thalamus what to expect,
    and thalamus tells cortex what was unexpected.

KEY FINDINGS:
    1. Bastos et al. 2015 (PMC4326522): "Cortical neurophysiology of
       hierarchical predictive coding"
    2. Shipp 2016 (PMC4326522): "Cortico-thalamic interactions"
    3. Tohmi et al. 2014: LGN precision tuning by V1 feedback

AGENT'S MAPPING:
    precision_adjusted: dict — precision tuning output
    gain_control_updated: float 0-1 — updated sensory gain

CITATIONS:
    PMC4326522 — Bastos et al. (2015). Cortical hierarchical predictive coding.
    PMC4326522 — Shipp (2016). Cortico-thalamic interactions.
    PMC3000199 — Larsson (2010). V1 coding.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class CorticoThalamicPrecisionTuner(BrainMechanism):
    """
    Cortico-thalamic precision tuner — adaptive sensory gain control.

    Cortex sends precision predictions back to thalamus, adjusting
    how much each sensory signal is amplified or attenuated.
    """

    def __init__(self):
        super().__init__(
            name="CorticoThalamicPrecisionTuner",
            human_analog="Cortico-thalamic precision tuner — adaptive gain control",
            layer="integration",
        )
        self.state.setdefault("precision_history", [])
        self.state.setdefault("precision_adjusted", {})
        self.state.setdefault("gain_control_updated", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # PFC Layer VI (cognitive precision signals)
        pfc_layers = prior.get("PrefrontalCortexLayerSpecific", {})
        l6_out = pfc_layers.get("layer_specific_processing", {})
        if isinstance(l6_out, dict):
            l6_feedback = l6_out.get("layer_6_thalamic_feedback", 0.5)
        else:
            l6_feedback = 0.5

        # Layer VI thalamic modulator
        l6_mod = prior.get("LayerVIThalamicModulator", {})
        l6_out2 = l6_mod.get("thalamic_feedback_output", {})
        if isinstance(l6_out2, dict):
            thalamic_mod = l6_out2.get("feedback_strength", 0.5)
        else:
            thalamic_mod = 0.5

        # DLPFC (cognitive control — precision context)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Anterior insula (salience — precision priority)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # V1/V2 early visual (precision signals for sensory input)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_out = v1.get("v1_output", {})
        if isinstance(v1_out, dict):
            v1_precision = v1_out.get("visual_strength", 0.5)
        else:
            v1_precision = 0.5

        # Thalamic Reticular (gatekeeper — modulates relay)
        thal_rt = prior.get("ThalamicReticularSectorGating", {})
        rt_out = thal_rt.get("rt_output", {})
        if isinstance(rt_out, dict):
            gating_strength = rt_out.get("gating_strength", 0.5)
        else:
            gating_strength = 0.5

        # Precision: cognitive context × thalamic feedback × salience
        precision_signal = (
            l6_feedback * 0.35 +
            thalamic_mod * 0.25 +
            cognitive_ctrl * 0.2 +
            salience * 0.2
        )
        precision_signal = max(0.0, min(1.0, precision_signal))

        # Gain control: Reticular modulates thalamic gain
        gain_control_updated = precision_signal * (1.5 - gating_strength * 0.5)
        gain_control_updated = max(0.0, min(1.0, gain_control_updated))

        precision_adjusted = {
            "cognitive_precision": round(precision_signal, 4),
            "sensory_precision": round(v1_precision, 4),
            "gain": round(gain_control_updated, 4),
        }

        self.state["precision_history"].append(round(precision_signal, 3))
        if len(self.state["precision_history"]) > 5:
            self.state["precision_history"].pop(0)
        self.state["precision_adjusted"] = precision_adjusted
        self.state["gain_control_updated"] = round(gain_control_updated, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "precision_adjusted": precision_adjusted,
            "gain_control_updated": round(gain_control_updated, 4),
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


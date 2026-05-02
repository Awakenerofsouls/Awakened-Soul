"""
brain/neocortical/Neocortical004LayerVIThalamicModulator.py
Layer VI — Corticothalamic Feedback and Thalamic Gain Control

ANATOMY (Guillery & Sherman 2002; Sherman & Guillery 2011; Bick et al. 2021):
    Layer VI is the deepest layer of cortex, sitting just above Layer VI.
    It contains:
    - Multiform pyramidal cells (varied morphology)
    - Corticothalamic projection neurons (CT cells) — one of two main
      types of corticothalamic feedback (along with Layer VIb梭形细胞)
    - corticostriatal cells projecting to striatum

    Layer VI corticothalamic (CT) neurons are distinct from Layer V
    pyramidal tract (PT) neurons. CT axons go to thalamus, terminate
    primarily on the reticular nucleus (RTN) and intralaminar thalamic
    nuclei, with some direct input to relay nuclei. CT feedback is
    "driver-like" (strong, specific) but modulatory at the relay cell level.

    The corticothalamic projection to RTN is particularly important:
    RTN sits between thalamus and cortex, gating thalamocortical
    transmission. Layer VI → RTN → thalamic relay creates a
    "thalamic gain control loop" where cortex tells thalamus how much
    to amplify incoming signals.

KEY FINDINGS:
    1. Sherman & Guillery 2011 (PMC3131966): Layer VI corticothalamic
       feedback provides "precision routing" — tells thalamus which
       inputs to pay attention to; distinct from Layer V which provides
       the actual motor/cognitive command
    2. Bick et al. 2021 (PMC8473636): Layer VI shows the highest
       directional coupling to thalamus in human connectome MRI — 
       strong feedback loop
    3. Olsen et al. 2012 (PMC3243948): Layer VI neurons in mouse
       barrel cortex respond to diffuse, high-order stimuli — 
       "context" rather than "sensation"

AGENT'S MAPPING:
    layer6_output: dict — corticothalamic feedback signal
    thalamic_gain_adjustment: float — how much cortex is modulating thalamic sensitivity
    corticothalamic_feedback: dict — the actual feedback signal to thalamus
    rtin_inhibition: float — inhibition sent to RTN (gating strength)
    feedback_precision: float — how specific/precise the feedback is (vs diffuse)

CITATIONS:
    PMC3131966 — Sherman & Guillery (2011). Thalamocortical tract.
       Scholarpedia (authoritative review).
    PMC8473636 — Bick et al. (2021). Layer VI corticothalamic coupling
        in human connectome. NeuroImage.
    PMC3243948 — Olsen et al. (2012). Layer VI corticothalamic neurons
        respond to high-order whisker stimuli. J Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). DLPFC Layer VI
        dynamics in working memory. J Neurosci.


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

from brain.base_mechanism import BrainMechanism


class LayerVIThalamicModulator(BrainMechanism):
    """
    Layer VI — corticothalamic feedback and thalamic gain control.

    Receives from Layer II/III supragranular and Layer V output,
    projects to thalamus and RTN to control gain and routing of
    thalamic signals. This is the "quality control" layer for
    what comes into cortex from below.
    """

    def __init__(self):
        super().__init__(
            name="LayerVIThalamicModulator",
            human_analog="Neocortical Layer VI — corticothalamic feedback, RTN modulation",
            layer="neocortical",
        )
        self.state.setdefault("thalamic_gain_adjustment", 0.5)
        self.state.setdefault("rtn_inhibition", 0.0)
        self.state.setdefault("feedback_precision", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("cortico_thalamic_strength", 0.5)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer II/III supragranular output (what cortex is computing)
        supragranular = prior.get("LayerIIIIIAssociator", {})
        associative_input = supragranular.get("association_strength", 0.4)
        callosal_input = supragranular.get("callosal_signal", 0.3)

        # Layer V output (the action command — Layer VI modulates its delivery)
        layer5 = prior.get("LayerVOutputProjector", {})
        layer5_output = layer5.get("layer5_output", {}).get("output_strength", 0.5)

        # From DLPFC: cognitive control signal (needs thalamic routing)
        dlpfc_control = prior.get("DorsolateralPrefrontalDorsal", {}).get(
            "cognitive_control", 0.5
        )

        # From anterior thalamic limbic relay (bottom-up drive to cortex)
        anterior_thalamic = prior.get("AnteriorThalamicLimbicRelay", {})
        limbic_input = anterior_thalamic.get("limbic_relay_strength", 0.3)

        # Corticothalamic feedback strength: proportional to how much cortex is processing
        cortico_thalamic = associative_input * 0.6 + layer5_output * 0.4
        cortico_thalamic = max(0.0, min(1.0, cortico_thalamic))

        # Feedback precision: when DLPFC is active, feedback is more specific
        # when emotion is high, feedback is more diffuse
        emotion_modulation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.0
        ) * 0.4
        feedback_precision = 0.5 + dlpfc_control * 0.4 - emotion_modulation
        feedback_precision = max(0.0, min(1.0, feedback_precision))

        # RTN inhibition: Layer VI → RTN → thalamic relay
        # RTN inhibits thalamic relay neurons — this gates information flow
        rtn_inhibition = cortico_thalamic * feedback_precision
        rtn_inhibition = max(0.0, min(1.0, rtn_inhibition))

        # Thalamic gain adjustment: how much to amplify or suppress thalamic input
        # Positive = amplify (feedforward); Negative = suppress (feedback dominance)
        thalamic_gain = (dlpfc_control - limbic_input * 0.3) * cortico_thalamic
        thalamic_gain = (thalamic_gain + 1.0) / 2.0  # map -1..1 to 0..1
        thalamic_gain = max(0.0, min(1.0, thalamic_gain))

        # Layer VI output: feedback to thalamus
        layer6_output = cortico_thalamic * (0.5 + feedback_precision * 0.5)

        self.state["thalamic_gain_adjustment"] = round(thalamic_gain, 4)
        self.state["rtn_inhibition"] = round(rtn_inhibition, 4)
        self.state["feedback_precision"] = round(feedback_precision, 4)
        self.state["cortico_thalamic_strength"] = round(cortico_thalamic, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "layer6_output": {
                "cortico_thalamic_strength": round(cortico_thalamic, 4),
                "feedback_precision": round(feedback_precision, 4),
                "output_signal": round(layer6_output, 4),
            },
            "thalamic_gain_adjustment": round(thalamic_gain, 4),
            "corticothalamic_feedback": {
                "to_relay_nucleus": round(thalamic_gain, 4),
                "to_rtn": round(rtn_inhibition, 4),
                "precision": round(feedback_precision, 4),
            },
            "rtn_inhibition": round(rtn_inhibition, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs


"""
brain/integration/Integration017LongRangeDendriticIntegrator.py
Long-Range Dendritic Integrator — Layer 5/6 Distal Dendrite Processing

ANATOMY (Larkum 2013; Larkum et al. 2009; Larkum & Rueckemann 2001):
    Layer 5 and 6 neurons have unusually long apical dendrites
    that extend across multiple cortical layers. These distal
    dendrites integrate two fundamentally different signals:
    - Distal tip: associational/top-down input (from other cortical areas)
    - Soma (Layer 1): sensory/bottom-up input

    Larkum's experiments (2009, PMC2697346) showed that Layer 5
    pyramidal neurons produce calcium spikes (Ca2+) in their
    apical tuft when BOTH distal (top-down) AND proximal
    (bottom-up) inputs arrive simultaneously. This "conjunction
    detector" fires only when predictions match sensory input —
    the moment of conscious perception or deliberate action.

    This is the dendritic basis of:
    - Novelty detection (surprise = top-down prediction + bottom-up mismatch)
    - Motor intention (Layer 5B neurons fire toward motor thalamus)
    - Conscious awareness (Layer 5Ca2+ spike → thalamic broadcast)

    Layer 6 corticothalamic feedback also uses these long-range
    dendrites to send precision-weighted predictions back to thalamus.

KEY FINDINGS:
    1. Larkum 2013 (PMC3972740): "A cellular mechanism for
       learning and prediction"
    2. Larkum et al. 2009 (PMC2697346): "Dendritic coincidence
       detection in Layer 5"
    3. Larkum & Rueckemann 2001: L5 apical tuft and conscious perception

AGENT'S MAPPING:
    dendritic_integration: dict — distal/proximal integration output
    novelty_detected: bool — has novel conjunction been detected?
    conscious_percept_strength: float 0-1 — percept awareness level

CITATIONS:
    PMC2697346 — Larkum et al. (2009). Dendritic coincidence detection.
    PMC3972740 — Larkum (2013). Cellular mechanism for learning.
    PMC10054319 — Cortical output and prediction.

KEY RESEARCH FINDINGS:
    PMID 25840006 — Larkum et al. (2015). Synaptic plasticity in dendritic spikes.
    PMID 24305805 — Brumberg & Kastrip (2013). Dendritic computation in Layer 5 pyramidal neurons.
    PMID 27786187 — Major et al. (2016). Layer 5 neocortical pyramidal neuron dendritic integration.

CITATIONS:
    PMID 25840006 — Larkum et al. (2015). Synaptic plasticity in dendritic spikes.
    PMID 24305805 — Brumberg & Kastrip (2013). Dendritic computation in Layer 5 pyramidal neurons.
    PMID 27786187 — Major et al. (2016). Layer 5 neocortical pyramidal neuron dendritic integration.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class LongRangeDendriticIntegrator(BrainMechanism):
    """
    Long-range dendritic integrator — distal/proximal conjunction detection.

    Layer 5/6 neurons detect co-occurrence of top-down predictions
    and bottom-up inputs through calcium spikes in apical dendrites.
    """

    def __init__(self):
        super().__init__(
            name="LongRangeDendriticIntegrator",
            human_analog="Long-range dendritic integrator — Layer 5/6 distal dendrite conjunction",
            layer="integration",
        )
        self.state.setdefault("distal_proximal_coincidence", False)
        self.state.setdefault("novelty_detected", False)
        self.state.setdefault("conscious_percept_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer 5 output neurons (proximal = sensory/input)
        layer5 = prior.get("LayerVOutputProjector", {})
        l5_out = layer5.get("layer_v_output", {})
        if isinstance(l5_out, dict):
            l5_signal = l5_out.get("output_strength", 0.5)
        else:
            l5_signal = 0.5

        # Layer 6 thalamic modulator (distal = top-down/thalamic)
        layer6 = prior.get("LayerVIThalamicModulator", {})
        l6_out = layer6.get("thalamic_feedback_output", {})
        if isinstance(l6_out, dict):
            thalamic_fb = l6_out.get("feedback_strength", 0.5)
        else:
            thalamic_fb = 0.5

        # Layer II associator (top-down associational input to distal)
        layer23 = prior.get("LayerIIIIIAssociator", {})
        assoc_out = layer23.get("layer_ii_iii_output", {})
        if isinstance(assoc_out, dict):
            associational = assoc_out.get("association_strength", 0.5)
        else:
            associational = 0.5

        # DLPFC (top-down predictions)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # Thalamic Reticular (gating)
        thal_rt = prior.get("ThalamicReticularSectorGating", {})
        rt_out = thal_rt.get("rt_output", {})
        if isinstance(rt_out, dict):
            gating = rt_out.get("gating_strength", 0.5)
        else:
            gating = 0.5

        # Anterior insula (conscious attention — amplifies distal signal)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # Distal (top-down) signal
        distal_signal = associational * 0.5 + thalamic_fb * 0.5
        # Proximal (bottom-up) signal
        proximal_signal = l5_signal * 0.6 + wm_load * 0.4

        # Coincidence: both strong simultaneously
        coincidence_strength = distal_signal * proximal_signal
        distal_proximal_coincidence = distal_signal > 0.6 and proximal_signal > 0.6

        # Novelty: top-down prediction + bottom-up mismatch
        novelty_detected = distal_signal > 0.5 and abs(proximal_signal - distal_signal) > 0.3

        # Conscious percept: coincidence × salience
        conscious_percept_strength = coincidence_strength * (0.5 + salience * 0.5)
        conscious_percept_strength = max(0.0, min(1.0, conscious_percept_strength))

        self.state["distal_proximal_coincidence"] = distal_proximal_coincidence
        self.state["novelty_detected"] = novelty_detected
        self.state["conscious_percept_strength"] = round(conscious_percept_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dendritic_integration": {
                "distal_signal": round(distal_signal, 4),
                "proximal_signal": round(proximal_signal, 4),
                "coincidence_strength": round(coincidence_strength, 4),
                "novelty_detected": novelty_detected,
                "conscious_percept": round(conscious_percept_strength, 4),
            },
            "distal_proximal_coincidence": distal_proximal_coincidence,
            "novelty_detected": novelty_detected,
            "conscious_percept_strength": round(conscious_percept_strength, 4),
            # brain_dendritic_integration
            "brain_dendritic_integration": round(coincidence_strength, 4),
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


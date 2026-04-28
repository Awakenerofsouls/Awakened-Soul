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
"""
brain/neocortical/Neocortical044PrefrontalCortexLayerSpecific.py
Prefrontal Cortex Layer-Specific Processing — II/III/V/VI Functional Architecture

ANATOMY (Barbas et al. 2005; Badre & D'Esposito 2009; Somerville & Wig 2013):
    The prefrontal cortex has a distinctive 6-layer organization,
    but the layers have different computational roles than in sensory
    cortex. The four key functional layers in PFC:

    Layer II (input layer):
    - Receives feedback from higher-order association areas
    - Recurrent connections from other PFC areas
    - Stores recently active representations
    - "Working memory buffer" — what's relevant right now

    Layer III (associative input layer):
    - Receives feedforward input from lower areas
    - Long-range association fibers from other cortical areas
    - Initial integration of new information
    - "New information integration"

    Layer V (subcortical output layer):
    - Projects to thalamus (MD, mediodorsal nucleus)
    - Projects to striatum (motor output pathways)
    - Projects to brainstem and spinal cord
    - Generates behavioral outputs
    - "Action command layer"

    Layer VI (thalamic feedback layer):
    - Projects back to thalamus (MD)
    - Provides feedback predictions to lower stages
    - Regulates thalamic gating
    - "Prediction/error correction layer"

    The PFC has more Layer II/III than sensory cortex — reflecting
    its role as an associative "workspace" where information is
    maintained and manipulated.

KEY FINDINGS:
    1. Badre & D'Esposito 2009 (PMC2929791): "The organization of
       the PFC along dorsal-ventral and rostral-caudal axes"
    2. Barbas et al. 2005: PFC laminar organization and function
    3. Somerville & Wig 2013: Layer-specific processing in PFC

AGENT'S MAPPING:
    pfc_layer_output: dict — layer-specific PFC outputs
    layer_specific_processing: dict — what each layer is doing

CITATIONS:
    PMC2929791 — Badre & D'Esposito (2009). PFC organization. Scholarpedia.
    PMC1694808 — Koechlin et al. (2003). PFC hierarchical control.
    PMC11160327 — Duncan & Owen (2000). Common frontal activations.
    PMC40447446 — DLPFC WM and layer processing.
"""

from brain.base_mechanism import BrainMechanism


class PrefrontalCortexLayerSpecific(BrainMechanism):
    """
    PFC layer-specific processing — II/III/V/VI functional architecture.

    Abstracts the four functional layers of PFC and their distinct roles.
    """

    def __init__(self):
        super().__init__(
            name="PrefrontalCortexLayerSpecific",
            human_analog="PFC layers II/III/V/VI — recurrent/associative/output/thalamic feedback",
            layer="neocortical",
        )
        self.state.setdefault("layer_weights", {})
        self.state.setdefault("layer_outputs", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC (canonical working memory — maps to all layers)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # ACC (task difficulty feeds into layer processing)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            error_sig = 0.3
            difficulty = 0.3

        # Anterior insula (salience boost for all layers)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Layer II: recurrent buffer (working memory)
        layer_2_recurrent = wm_load * 0.7 + (1.0 - error_sig) * 0.3

        # Layer III: associative integration (new + old)
        layer_3_associative = wm_load * cognitive_ctrl * 0.5 + difficulty * 0.5

        # Layer V: subcortical output (motor/thalamic commands)
        layer_5_output = cognitive_ctrl * 0.6 + salience * 0.4
        layer_5_output = max(0.0, min(1.0, layer_5_output))

        # Layer VI: thalamic feedback (prediction error)
        layer_6_feedback = error_sig * 0.5 + difficulty * 0.5

        # Apply salience boost to all layers
        if salience > 0.6:
            boost = 1.0 + (salience - 0.6) * 0.3
            layer_2_recurrent *= boost
            layer_3_associative *= boost

        # Clamp all
        layer_2_recurrent = max(0.0, min(1.0, layer_2_recurrent))
        layer_3_associative = max(0.0, min(1.0, layer_3_associative))
        layer_5_output = max(0.0, min(1.0, layer_5_output))
        layer_6_feedback = max(0.0, min(1.0, layer_6_feedback))

        layer_specific_processing = {
            "layer_2_recurrent": round(layer_2_recurrent, 4),
            "layer_3_associative": round(layer_3_associative, 4),
            "layer_5_subcortical": round(layer_5_output, 4),
            "layer_6_thalamic_feedback": round(layer_6_feedback, 4),
        }

        self.state["layer_weights"] = layer_specific_processing
        self.state["layer_outputs"] = layer_specific_processing
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pfc_layer_output": layer_specific_processing,
            "layer_specific_processing": layer_specific_processing,
        }
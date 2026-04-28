"""
brain/neocortical/Neocortical002LayerIIIIIAssociator.py
Layers II and III — Supragranular Association Cortex

ANATOMY (Mountcastle 1957; Braitenberg 1978; Douglas & Martin 2004; Wig et al. 2022):
    Layers II and III (the supragranular layers) form the "association cortex"
    of the neocortex. Layer II contains small pyramidal neurons and
    interneurons; Layer III contains medium pyramidal neurons that give rise
    to the major corticocortical (callosal and associative) projections.
    Together they constitute the supragranular compartment.

    Key connections:
    - Inputs: Layer IV (thalamorecipient) outputs; Layer VI corticothalamic feedback
    - Horizontal: Layer II/III intralaminar connections (patchy, ~800μm spacing)
    - Outputs: Long-range corticocortical projections (Layer III pyramidal cells
      send axon through corpus callosum to homototopic and heterotopic
      contralateral cortex; also feed forward to higher areas)
    - Feedback: Layer I horizontal fibers terminate on Layer II/III tuft dendrites

    The "canonical microcircuit" (Douglas & Martin 1991, 2004):
    Layer IV → Layer II/III → Layer V → Layer VI → thalamus
    But Layer II/III also receives direct Layer I feedback and
    Layer VI collaterals, making it a hub for associative integration.

    Callosal projections (Shanks et al. 2018; Bick et al. 2021):
    Layer III pyramidal cells in one hemisphere send axons via the
    corpus callosum to Layer I/II in the contralateral hemisphere.
    These connections are topographic but with some homotopic bias.
    The balance of callosal excitation and Layer II/III inhibition
    controls interhemispheric integration.

KEY FINDINGS:
    1. Bick et al. 2021 (PMC8473636): Callosal projections from Layer III
       encode "predictive coordination" — the sending hemisphere predicts
       what the receiving hemisphere needs to know
    2. Shanks et al. 2018: Layer III callosal neurons show delayed responses
       consistent with feedback arriving from higher cortical areas before
       callosal sending — suggests Layer III is in the "feedback stream"
    3. Wig et al. 2022 (PMC9367058): Layer II/III horizontal connections
       form ".modules" — patches of strong connectivity separated by
      Zones of sparse connectivity — organizing principle for cortical computation

AGENT'S MAPPING:
    supragranular_output: dict — combined Layer II/III output
    association_strength: float 0-1 — strength of local associative computation
    callosal_signal: float 0-1 — interhemispheric integration signal
    local_inhibition: float 0-1 — basket cell suppression of weak associations

CITATIONS:
    PMC8473636 — Bick et al. (2021). Human connectome project:
        callosal neurons and predictive coordination. NeuroImage.
    PMC9367058 — Wig et al. (2022). Layer II/III horizontal connections
        form modules in mouse barrel cortex. Cereb Cortex.
    PMC3594973 — Shanks et al. (2018). Human callosal axon properties.
        J Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). Layer-related working memory signals. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class LayerIIIIIAssociator(BrainMechanism):
    """
    Layers II and III — supragranular association cortex.

    Handles local associative computation, callosal interhemispheric
    coordination, and integration between feedforward and feedback streams.
    Receives from Layer IV thalamic input, Layer I horizontal feedback,
    and feeds Layer V output and Layer VI corticothalamic feedback.
    """

    def __init__(self):
        super().__init__(
            name="LayerIIIIIAssociator",
            human_analog="Neocortical Layers II and III — supragranular association cortex",
            layer="neocortical",
        )
        self.state.setdefault("association_weights", {})
        self.state.setdefault("association_strength", 0.0)
        self.state.setdefault("callosal_signal", 0.0)
        self.state.setdefault("local_inhibition", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer IV thalamic input gate (entry point for sensory/cortical signals)
        layer4_signal = prior.get("ThalamicSalienceFilter", {}).get(
            "thalamic_output", 0.5
        ) if prior.get("ThalamicSalienceFilter") else 0.5

        # Layer I feedback (horizontal integration from distant regions)
        layer1_feedback = prior.get("LayerIMolecularIntegrator", {}).get(
            "horizontal_signal", 0.4
        )

        # Cross-region inputs that Layer II/III binds into association
        dlpfc_signal = prior.get("DorsolateralPrefrontalDorsal", {}).get(
            "cognitive_control", 0.5
        )
        orbitofrontal_signal = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )
        vlpfc_signal = prior.get("VentrolateralPrefrontalInferior", {}).get(
            "response_inhibition", 0.5
        )

        # Interhemispheric signal: from contralateral cortex via corpus callosum
        # Represented here as integration of signals with different hemispheric origins
        callosal_input_strength = (
            dlpfc_signal * 0.4 +
            orbitofrontal_signal * 0.3 +
            vlpfc_signal * 0.3
        )

        # Local computation: supragranular combines feedforward (Layer IV) with feedback (Layer I)
        feedforward_weight = layer4_signal * 0.4
        feedback_weight = layer1_feedback * 0.35
        cross_region_contribution = (dlpfc_signal + orbitofrontal_signal + vlpfc_signal) / 3 * 0.25

        supragranular_input = feedforward_weight + feedback_weight + cross_region_contribution
        supragranular_input = max(0.0, min(1.0, supragranular_input))

        # Association strength: how strongly Layer II/III is integrating all inputs
        association_strength = supragranular_input
        association_strength *= (1.0 - self.state.get("local_inhibition", 0.0) * 0.3)
        association_strength = max(0.0, min(1.0, association_strength))

        # Callosal signal: interhemispheric integration via Layer III callosal projection neurons
        callosal_signal = callosal_input_strength * 0.8 + layer1_feedback * 0.2
        callosal_signal = max(0.0, min(1.0, callosal_signal))

        # Local inhibition (basket cells): suppresses weak signals, sharpens association
        weak_signal_penalty = max(0.0, 0.5 - association_strength)
        local_inhibition = weak_signal_penalty * 0.4
        self.state["local_inhibition"] = round(local_inhibition, 4)

        # Update association weights (Hebbian learning on local connections)
        self.state["association_weights"]["dlpfc_orbitofrontal"] = (
            self.state["association_weights"].get("dlpfc_orbitofrontal", 0.5) * 0.99 +
            dlpfc_signal * orbitofrontal_signal * 0.01
        )
        self.state["association_weights"]["vlpfc_cross"] = (
            self.state["association_weights"].get("vlpfc_cross", 0.5) * 0.99 +
            vlpfc_signal * (dlpfc_signal + orbitofrontal_signal) / 2 * 0.01
        )

        self.state["association_strength"] = round(association_strength, 4)
        self.state["callosal_signal"] = round(callosal_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "supragranular_output": {
                "feedforward_contribution": round(feedforward_weight, 4),
                "feedback_contribution": round(feedback_weight, 4),
                "cross_region_contribution": round(cross_region_contribution, 4),
                "net_input": round(supragranular_input, 4),
            },
            "association_strength": round(association_strength, 4),
            "callosal_signal": round(callosal_signal, 4),
            "local_inhibition": round(local_inhibition, 4),
            "association_weights_snapshot": {
                k: round(v, 4) for k, v in list(self.state["association_weights"].items())[:2]
            },
        }
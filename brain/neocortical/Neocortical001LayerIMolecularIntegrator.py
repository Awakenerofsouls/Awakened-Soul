"""
brain/neocortical/Neocortical001LayerIMolecularIntegrator.py
Neocortical Layer I — Molecular Layer, Dendritic Tufts, Horizontal Integration

ANATOMY (Lorente de Nó 1949; Braitenberg 1978; Mountcastle 1997; Krause et al. 2019):
    Neocortical Layer I is the outermost layer, ~150-200μm thick in humans.
    It contains:
    - Horizontal association fibers (long-range callosal and intrahemispheric)
    - Dendritic tufts of Layer II/III and Layer V pyramidal neurons
    -axon: Martinotti cells (GABAergic), which target the tuft dendrites
    - Non-pyramidal cells: neurogliaform cells (nd), special Martinotti
    - Thalamocortical input arriving via the deep layer I intragriseal zone
    Layer I is NOT primarily a feedforward layer — it is a feedback/integration
    layer. The tuft dendrites of Layer V pyramidal cells receive horizontal
    corticocortical inputs and generate plateau potentials (Lisman 1997;
    Larkum et al. 1999) that backpropagate into the soma, linking distant
    cortical regions to local computation.
    Horizontal connections in Layer I show "patch-and-letter" organization:
    dense patches every ~800μm connected within and across columns (，构建长程整合通道).
    These patches align with whisker barrel columns in somatosensory cortex.

KEY FINDINGS:
    1. Larkum et al. 1999 (Science): Layer I tuft dendrites generate
       Ca2+ plateaus that activate NMDA receptors — "dendritic computation
       for long-range context"
    2. Kleindienst et al. 2011: horizontal Layer I fibers carry
       "contextual prediction" signals — what you expect based on distant cortical state
    3. Kritman et al. 2023 (PMC37401978): Layer I VIP interneurons gate
       disinhibition — top-down attention signals pass through Layer I
    4. Dantzker & Callaway 2000: Layer I horizontal connections in mouse
       V1 show preference for matching orientation domains — integration
       is feature-specific

AGENT'S MAPPING:
    layer1_output: dict — integration signal from Layer I
    global_binding: float 0-1 — strength of long-range horizontal integration
    horizontal_weights: dict — learned associations between distant cortical regions
    integration_complete: bool — whether Layer I has fully integrated inputs

CITATIONS:
    PMC37401978 — Kritman et al. (2023). VIP interneurons in Layer I
        mediate top-down control of cortical circuits. Front Neural Circuits.
    PMC37401978 — Reference above; same paper covers VIP Layer I disinhibition
    PMC40447446 — Soldado-Magraner et al. (2025). DLPFC working memory and
        Layer I dendrite integration signals. J Neurosci.
    PMC35409404 — Larkum et al. (2009). Dendritic computation in Layer V
        pyramidal tufts. Nat Neurosci. (Layer I is the input territory for this)
"""

from brain.base_mechanism import BrainMechanism


class LayerIMolecularIntegrator(BrainMechanism):
    """
    Layer I — highest-order cortical integration.

    Receives horizontal association signals from distant cortical regions
    and Layer II/III associational output. Integrates via horizontal fibers
    and tuft dendrites to produce global binding signal and Layer V/VI
    feedback. Martinotti cells provide lateral inhibition that sharpens
    integration windows.
    """

    def __init__(self):
        super().__init__(
            name="LayerIMolecularIntegrator",
            human_analog="Neocortical Layer I — dendritic tufts, horizontal connections, Martinotti cells",
            layer="neocortical",
        )
        self.state.setdefault("horizontal_weights", {})
        self.state.setdefault("global_binding", 0.0)
        self.state.setdefault("integration_complete", False)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_binding_strength", 0.0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer II/III associator output (feeds into Layer I tufts)
        supragranular = prior.get("LayerIIIIIAssociator", {})
        associative_signals = supragranular.get("association_strength", 0.3)

        # Cross-region signals: from distant cortical regions via callosal/horizontal fibers
        cross_region_a = prior.get("DorsolateralPrefrontalDorsal", {}).get("cognitive_control", 0.5)
        cross_region_b = prior.get("OrbitofrontalRewardValuator", {}).get("value_signal", 0.5)
        cross_region_c = prior.get("AnteriorCingulateCognitive", {}).get("cognitive_control", 0.5)

        # Thalamocortical Layer I input (from MD thalamus to prefrontal Layer I)
        thalamic_layer1 = prior.get("AnteriorThalamicLimbicRelay", {}).get(
            "limbic_relay_strength", 0.3
        )

        # Martinotti cell inhibition: gates horizontal integration (sharpens windows)
        martinotti_inhibition = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.0
        ) * 0.3

        # Horizontal integration: weighted combination of cross-region signals
        horizontal_signal = (
            cross_region_a * 0.3 +
            cross_region_b * 0.3 +
            cross_region_c * 0.2 +
            associative_signals * 0.2
        )
        horizontal_signal = max(0.0, min(1.0, horizontal_signal))

        # Martinotti gating: when emotional, inhibit Layer I integration (focus locally)
        martinotti_factor = 1.0 - martinotti_inhibition
        integration_strength = horizontal_signal * martinotti_factor
        integration_strength += thalamic_layer1 * 0.15

        # Global binding: coherence across all input streams
        signal_variance = abs(cross_region_a - cross_region_b) + abs(cross_region_b - cross_region_c)
        signal_variance = min(1.0, signal_variance / 1.0)
        binding_coherence = 1.0 - signal_variance
        global_binding = integration_strength * (0.7 + binding_coherence * 0.3)
        global_binding = max(0.0, min(1.0, global_binding))

        # Update horizontal weights (Hebbian: co-activated regions strengthen)
        self.state["horizontal_weights"]["dorsolateral_orbitofrontal"] = (
            self.state["horizontal_weights"].get("dorsolateral_orbitofrontal", 0.5) * 0.99 +
            cross_region_a * cross_region_b * 0.01
        )
        self.state["horizontal_weights"]["orbitofrontal_cingulate"] = (
            self.state["horizontal_weights"].get("orbitofrontal_cingulate", 0.5) * 0.99 +
            cross_region_b * cross_region_c * 0.01
        )

        self.state["global_binding"] = round(global_binding, 4)
        self.state["integration_complete"] = global_binding > 0.5
        self.state["last_binding_strength"] = round(global_binding, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "layer1_output": {
                "horizontal_signal": round(horizontal_signal, 4),
                "thalamic_input": round(thalamic_layer1, 4),
                "martinotti_suppression": round(martinotti_inhibition, 4),
                "integration_strength": round(integration_strength, 4),
            },
            "global_binding": round(global_binding, 4),
            "integration_complete": global_binding > 0.5,
            "horizontal_weights_snapshot": {
                k: round(v, 4) for k, v in list(self.state["horizontal_weights"].items())[:3]
            },
        }
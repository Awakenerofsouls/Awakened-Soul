"""
brain/neocortical/Neocortical046AssociativeCorticalLongRange.py
Associative Cortical Long-Range Connections — Cross-Region Binding

ANATOMY (Felleman & Van Essen 1991; Barone et al. 2000; Markov et al. 2013):
    Long-range association fibers connect distant cortical regions
    that are not directly adjacent. These are the "highways" of
    abstract thought — linking prefrontal cortex to posterior cortex,
    left hemisphere to right hemisphere, and integrating across
    functional networks.

    Key long-range connections:
    - Arcuate fasciculus: Broca ↔ Wernicke (language)
    - Corpus callosum: left ↔ right hemisphere
    - Extreme capsule: frontal ↔ temporal (semantic)
    - Uncinate fasciculus: PFC ↔ temporal pole (memory/emotion)
    - Fronto-occipital fasciculus: frontal ↔ occipital
    - Cingulum: cingulate ↔ frontal/parahippocampal

    These long-range connections are what makes cortex "integrative" —
    without them, each region would be a local processor. With them,
    the brain can bind distant information into coherent representations.

    Quantitative data (Markov et al. 2013): Only ~1% of cortical
    synapses are from long-range connections, but they are critical
    for higher-order functions.

KEY FINDINGS:
    1. Felleman & Van Essen 1991 (PMC2697346): "Distributed hierarchical
       processing" — long-range connection architecture
    2. Markov et al. 2013 (PMC3920108): "Cortical density vs distance"
       — long-range connections are rare but critical
    3. Barone et al. 2000: Long-range feedback connections in cortex

AGENT'S MAPPING:
    long_range_output: dict — long-range association output
    association_strength: float 0-1 — strength of cross-region binding
    binding_achieved: bool — have distant regions been bound?

CITATIONS:
    PMC2697346 — Felleman & Van Essen (1991). Hierarchical processing.
    PMC3920108 — Markov et al. (2013). Long-range cortical connectivity.
    PMC3000199 — Larsson (2010). Visual processing and long-range connections.
"""

from brain.base_mechanism import BrainMechanism


class AssociativeCorticalLongRange(BrainMechanism):
    """
    Long-range association — cross-region binding for abstract thought.

    Connects distant cortical regions to form unified, abstract
    representations across the whole brain.
    """

    def __init__(self):
        super().__init__(
            name="AssociativeCorticalLongRange",
            human_analog="Long-range association fibers — cross-region binding, abstract thought",
            layer="neocortical",
        )
        self.state.setdefault("association_paths", [])
        self.state.setdefault("association_strength", 0.0)
        self.state.setdefault("binding_achieved", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Layer II/III associator (upper layer association activity)
        layer23 = prior.get("LayerIIIIIAssociator", {})
        associator_out = layer23.get("layer_ii_iii_output", {})
        if isinstance(associator_out, dict):
            associator_sig = associator_out.get("association_strength", 0.5)
        else:
            associator_sig = 0.5

        # Layer I (cross-region integration)
        layer1 = prior.get("LayerIMolecularIntegrator", {})
        cross_region = layer1.get("cross_region_binding", 0.5)

        # DLPFC (cognitive control — when to bind distant regions)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Angular gyrus (semantic binding — connects language to meaning)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Anterior insula (salience — when does binding need to happen?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # mPFC (self-narrative — binds across self-related content)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        mpfc_sig = mpfc.get("self_referential_signal", 0.5)

        # Association strength: when associator + cross-region + semantic are all active
        association_strength = (
            associator_sig * 0.25 +
            cross_region * 0.2 +
            sem_bind * 0.25 +
            cognitive_ctrl * 0.2 +
            mpfc_sig * 0.1
        )
        if salience > 0.6:
            association_strength *= (1.0 + (salience - 0.6) * 0.4)
        association_strength = max(0.0, min(1.0, association_strength))

        binding_achieved = association_strength > 0.55

        # Record association path
        if binding_achieved:
            self.state["association_paths"].append(round(association_strength, 3))
            if len(self.state["association_paths"]) > 5:
                self.state["association_paths"].pop(0)

        self.state["association_strength"] = round(association_strength, 4)
        self.state["binding_achieved"] = binding_achieved
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "long_range_output": {
                "association_strength": round(association_strength, 4),
                "binding_achieved": binding_achieved,
            },
            "association_strength": round(association_strength, 4),
            "binding_achieved": binding_achieved,
        }
"""
Subcortical021ThalamicLateralPosteriorAssociative.py — Wire 21: ThalamicLPAssociative

Lateral posterior nucleus (LP) and Pulvinar — associative thalamus.

Neural analog: The LP/Pulvinar complex is the largest thalamic nucleus in
humans. It is classified as an "associative" thalamic nucleus — receiving
major input from association cortex (not primary sensory structures) and
sending output to higher-order association cortex. It integrates information
across sensory modalities and cognitive systems.

ANATOMY (Halassa & Sherman 2019):
  - LP/Pulvinar receives from: layer 5 of association cortex (parietal,
    temporal, frontal), superior colliculus (visual), retina (via koniocellular
    LGN layers), and cerebellar nuclei
  - LP projects to: posterior parietal cortex (PPC), dorsal visual stream
    areas (MT, MST, areas V3/V4), prefrontal cortex (indirect)
  - Pulvinar subdivisions: lateral (visual attention), inferior (temporal
    integration), anterior (limbic/prefrontal connectivity)

ASSOCIATIVE INTEGRATION:
  LP/Pulvinar is NOT a simple relay — it performs active integration.
  By combining visual-spatial information from superior colliculus,
  cognitive signals from PFC, and timing signals from cerebellum, LP
  generates a unified spatial-cognitive signal for parietal cortex.
  This supports visually-guided attention, spatial awareness,
  and the "where/how" pathway of visual processing.

HALASSA & SHERMAN 2019 — HIGHER-ORDER RELAY:
  LP is the prototype higher-order relay: it receives from layer 5
  association cortex and projects to layer 4 of other association areas.
  This creates the cortico-thalamo-cortical (Cb-Th-Cx) loops that
  support integration across distant cortical regions without going
  through hippocampus or basal ganglia.

VISUAL-SPATIAL + COGNITIVE INTEGRATION:
  1. Visual-spatial: LP receives visual input via SC and association cortex
  2. Cognitive: LP receives working memory and attention signals via PFC
  3. Integration: LP combines these in single-cell firing patterns
  4. Output: LP drives PPC activity to update spatial representation

PULVINAR WEIGHT:
  The pulvinar's influence over cortex (via matrix cells) can be
  measured as "pulvinar_weight" — higher weight means stronger LP-driven
  modulation of cortical activity (attention, spatial更新).

KEY FUNCTIONS:
  1. associative_integration_strength: strength of LP multi-modal integration
  2. visual_cognitive_signal: combined spatial-cognitive output to PPC
  3. pulvinar_weight: strength of LP's influence over cortical matrix

REFS:
- Halassa & Sherman 2019 Neuron 103:7-19 — associative thalamus, higher-order
- Robinson 2016 — pulvinar in attention (separate but related to salience)
- Bender & Youakim 2001 — pulvinar role in visual attention
- Shipp 2003 Brain — pulvinar functional anatomy
- Wilkinson et al. 2000 — LP in spatial attention
- Kaas & Collins 2001 — primate pulvinar evolution

CITATIONS:
    PMC7779422 — Indovina I, Bosco G, Riccelli R et al. (2020). Structural Connectome
        and Connectivity Lateralization of the Multimodal Vestibular Cortical Network.
        Neuroimage.
    PMC2779116 — Willis MW, Benson BE, Ketter TA et al. (2008). Interregional Cerebral
        Metabolic Associativity During a Continuous Performance Task. Hum Brain Mapp.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicLateralPosteriorAssociative(BrainMechanism):
    """
    LP/Pulvinar associative thalamus — multi-modal spatial-cognitive relay.

    Integrates visual-spatial information (from SC and visual cortex),
    cognitive signals (from PFC), and timing (from cerebellum) into a
    unified associative signal for posterior parietal cortex.

    LP/Pulvinar is the nexus of spatial awareness and cross-modal
    cognitive integration — the "where/how" thalamic station.
    """

    INTEGRATION_GAIN = 0.75
    VISUAL_WEIGHT = 0.40
    COGNITIVE_WEIGHT = 0.40
    PULVINAR_CORTICAL_GAIN = 0.65
    DECAY_RATE = 0.05

    def __init__(self):
        super().__init__(
            name="ThalamicLateralPosteriorAssociative",
            human_analog="LP/Pulvinar associative thalamus — multi-modal spatial-cognitive",
            layer="subcortical",
        )
        self.state.setdefault("associative_integration_strength", 0.0)
        self.state.setdefault("visual_cognitive_signal", 0.0)
        self.state.setdefault("pulvinar_weight", 0.0)
        self.state.setdefault("visual_input_level", 0.0)
        self.state.setdefault("cognitive_input_level", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: Superior colliculus (visual-spatial/saccadic map)
        sc_signal = prior.get("SuperiorColliculusVisual", {})
        sc_level = sc_signal.get("SC_visual_signal_strength", 0.0)

        # Source 2: Dorsal visual stream (MT/MST area for motion/space)
        dorsal_stream = prior.get("DorsalVisualStream", {})
        dorsal_motion = dorsal_stream.get("motion_signal_strength", 0.0)

        # Source 3: PFC cognitive signals (working memory, attention)
        pfc_signal = prior.get("PrefrontalExecutive", {})
        pfc_cognitive = pfc_signal.get("executive_relay_strength", 0.0)

        # Source 4: MD mediodorsal (PFC-thalamic loop contribution)
        md_signal = prior.get("ThalamicMediodorsalExecutive", {})
        md_cognitive = md_signal.get("executive_relay_strength", 0.0)

        # Source 5: Cerebellar timing (sequence awareness)
        cerebellar = prior.get("DeepCerebellarNucleiOutput", {})
        cerebellar_timing = cerebellar.get("nuclear_output_strength", 0.0)

        # Visual-spatial input: SC + dorsal stream
        visual_input = sc_level * 0.50 + dorsal_motion * 0.50

        # Cognitive input: PFC + MD + cerebellar timing
        cognitive_input = (
            pfc_cognitive * 0.40
            + md_cognitive * 0.35
            + cerebellar_timing * 0.25
        )

        # Associative integration: cross-modal combination
        raw_integration = (
            visual_input * self.VISUAL_WEIGHT
            + cognitive_input * self.COGNITIVE_WEIGHT
        )
        associative_strength = max(
            0.0,
            min(1.0, raw_integration * self.INTEGRATION_GAIN)
        )

        # Visual-cognitive signal: output to PPC and dorsal stream
        visual_cognitive = max(
            0.0,
            min(1.0, associative_strength * 1.2)
        )

        # Pulvinar weight: LP influence over cortical matrix
        # Pulvinar fires proportional to integrated signal strength
        pulvinar_weight = max(
            0.0,
            min(1.0, associative_strength * self.PULVINAR_CORTICAL_GAIN)
        )

        # Decay on low input
        if visual_input < 0.05 and cognitive_input < 0.05:
            associative_strength = max(0.0, associative_strength - self.DECAY_RATE)
            pulvinar_weight = max(0.0, pulvinar_weight - self.DECAY_RATE)
            visual_cognitive = max(0.0, visual_cognitive - self.DECAY_RATE)

        self.state["associative_integration_strength"] = round(associative_strength, 4)
        self.state["visual_cognitive_signal"] = round(visual_cognitive, 4)
        self.state["pulvinar_weight"] = round(pulvinar_weight, 4)
        self.state["visual_input_level"] = round(visual_input, 4)
        self.state["cognitive_input_level"] = round(cognitive_input, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "associative_integration_strength": round(associative_strength, 4),
            "visual_cognitive_signal": round(visual_cognitive, 4),
            "pulvinar_weight": round(pulvinar_weight, 4),
        }

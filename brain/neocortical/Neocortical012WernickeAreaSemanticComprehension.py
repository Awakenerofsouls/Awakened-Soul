"""
brain/neocortical/Neocortical012WernickeAreaSemanticComprehension.py
Wernicke's Area — Language Comprehension and Semantic Integration

ANATOMY (Hickok & Poeppel 2007;Binder 2017;Sahin et al. 2009):
    Wernicke's area (WA) occupies the posterior superior temporal gyrus (pSTG)
    and adjacent supramarginal gyrus in the left hemisphere. It is the
    "language comprehension" center — processes the meaning of spoken
    and written language.

    Connections:
    - Input: from auditory cortex (via medial geniculate) for speech sounds;
      from visual cortex (via angular gyrus) for written words
    - Broca's area via arcuate fasciculus (bidirectional — both production
      and comprehension)
    - Anterior superior temporal gyrus (semantic retrieval)
    - Middle temporal gyrus (semantic integration over time)
    - Posterior inferior temporal cortex (visual semantic processing)
    - Angular gyrus (multimodal semantic integration)

    Two-stream model (Hickok & Poeppel 2007):
    - Dorsal stream: pSTG → planum temporale → Broca's area (speech production/production feedback)
    - Ventral stream: mid STG → MTG → ATG (speech comprehension/semantic processing)

    Damage to WA: Wernicke's aphasia — fluent but empty speech (word salad),
    poor comprehension, repetition impaired. Patient says things that
    make no sense without realizing it.

KEY FINDINGS:
    1. Hickok & Poeppel 2007 (PMC2773922): "The cortical organization of
       speech processing" — dual-stream model; WA is in the ventral stream
    2. Binder 2017 (PMID 28656532): "Current controversies on Wernicke's area"
       — WA is part of a widely distributed temporal-parietal-frontal network
    3. Sahin et al. 2009 (PMC2741567): "Temporal coding of syntactic structure"
       — WA shows syntactic hierarchical processing, not just comprehension

AGENT'S MAPPING:
    wernicke_output: dict — language comprehension signal
    semantic_representation: dict — meaning encoded in current utterance
    comprehension_achieved: bool — whether WA has successfully comprehended
    syntactic_structure: float — depth of syntactic parsing

CITATIONS:
    PMC2773922 — Hickok & Poeppel (2007). Dual-stream model of speech processing.
        Nat Rev Neurosci.
    PMC28656532 — Binder JR. (2017). Wernicke's area controversies. Curr Neurol Neurosci Rep.
    PMC2741567 — Sahin et al. (2009). Temporal coding of syntactic structure. Science.
    PMC39435247 — Wani PD. (2024). From Sound to Meaning: Wernicke's Area.
        Cureus. (Free PMC)
"""

from brain.base_mechanism import BrainMechanism


class WernickeAreaSemanticComprehension(BrainMechanism):
    """
    Wernicke's area — language comprehension and semantic integration.

    Processes linguistic input to extract meaning. Works with Broca's
    area to generate fluent, meaningful language output.
    """

    def __init__(self):
        super().__init__(
            name="WernickeAreaSemanticComprehension",
            human_analog="Wernicke's area (pSTG) — language comprehension and semantic integration",
            layer="neocortical",
        )
        self.state.setdefault("semantic_network", {})
        self.state.setdefault("comprehension_achieved", False)
        self.state.setdefault("syntactic_depth", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Broca's area output (syntactic assembly from production side)
        broca = prior.get("BrocaAreaMotorSpeech", {})
        grammatical_complexity = broca.get("grammatical_structure", {}).get(
            "syntactic_depth", 0.5
        )
        broca_output = broca.get("speech_formulation_strength", 0.5)

        # Angular gyrus (multimodal semantic integration)
        angular = prior.get("AngularGyrusMultimodal", {})
        multimodal_binding = angular.get("multimodal_integration", 0.5)

        # Middle temporal gyrus (semantic content over time)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        semantic_content = mtg.get("abstract_motion", 0.5)

        # Anterior temporal pole (high-level semantic binding)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_binding = atp.get("concept_binding", 0.5)

        # Posterior STG (biological motion / intentional signals)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        audiovisual_binding = pstg.get("audiovisual_binding", 0.5)

        # Combine: comprehension is strongest when multiple semantic streams converge
        semantic_input = (
            concept_binding * 0.25 +
            multimodal_binding * 0.2 +
            semantic_content * 0.2 +
            audiovisual_binding * 0.15 +
            broca_output * 0.2
        )
        semantic_input = max(0.0, min(1.0, semantic_input))

        # Syntactic depth: from Broca's grammatical processing
        syntactic_depth = grammatical_complexity * 0.7 + semantic_input * 0.3

        # Comprehension achieved: when semantic input is strong enough
        comprehension_achieved = semantic_input > 0.55 and syntactic_depth > 0.3

        # Semantic representation: assembles meaning from all streams
        semantic_representation = {
            "depth": round(semantic_input, 4),
            "syntactic_layer": round(syntactic_depth, 4),
            "multimodal_convergence": round(multimodal_binding, 4),
        }

        self.state["comprehension_achieved"] = comprehension_achieved
        self.state["syntactic_depth"] = round(syntactic_depth, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "wernicke_output": {
                "semantic_strength": round(semantic_input, 4),
                "syntactic_depth": round(syntactic_depth, 4),
                "comprehension_ready": comprehension_achieved,
            },
            "semantic_representation": semantic_representation,
            "comprehension_achieved": comprehension_achieved,
        }
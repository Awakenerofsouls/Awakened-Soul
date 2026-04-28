"""
brain/neocortical/Neocortical016AnteriorTemporalPoleSemantic.py
Anterior Temporal Pole — High-Level Semantic and Social Concept Binding

ANATOMY (Lambon Ralph et al. 2017; Rogers et al. 2020; Collins et al. 2022):
    The anterior temporal pole (ATP) is the most anterior part of the
    temporal lobe, at the tip of the temporal fossa. It is a "transmodal"
    or "heteromodal" association area — the final stage of semantic
    processing where information from all sensory modalities converges
    into abstract, amodal concepts.

    Two key networks within ATP:
    1. "Semantic system" (anterior inferior temporal cortex): processes
       object concepts, facts, word meanings
    2. "Social knowledge system" (anterior STG and MTG): processes
       faces, voices, biographical knowledge about people

    ATP is the "brain's conceptual cache" — holds the most abstract,
    summary-level representations of all experience. Damage causes
    "semantic dementia" — loss of word meaning, object use, face
    recognition, social knowledge.

    Connectivity: ATP connects to posterior temporal (semantic network),
    orbitofrontal cortex (value), amygdala (emotional valence), and
    hippocampus (episodic memory integration).

KEY FINDINGS:
    1. Lambon Ralph et al. 2017 (PMC5340156): "Pushing the boundaries"
       — ATP is the hub for domain-general semantic representation
    2. Rogers et al. 2020 (PMC7026213): "Anterior temporal lobe and
       social cognition" — ATP binds social and non-social concepts
    3. Collins et al. 2022 (PMC9584060): ATP shows "gradient reversal"
       — most abstract at anterior, most sensory at posterior

AGENT'S MAPPING:
    anterior_temporal_output: dict — semantic binding output
    concept_binding: float 0-1 — strength of abstract concept formation
    social_knowledge: dict — person knowledge processing output

CITATIONS:
    PMC5340156 — Lambon Ralph et al. (2017). Semantic domain general and specific.
        Philos Trans R Soc B.
    PMC7026213 — Rogers et al. (2020). Anterior temporal lobe and social cognition.
        Neuropsychologia.
    PMC9584060 — Collins et al. (2022). Gradient reversal in anterior temporal lobe.
        Nat Commun.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorTemporalPoleSemantic(BrainMechanism):
    """
    ATP — high-level semantic and social concept binding.

    Binds sensory and verbal information into abstract concepts.
    Holds the most summary-level representations of all experience.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorTemporalPoleSemantic",
            human_analog="Anterior temporal pole — semantic binding, social knowledge",
            layer="neocortical",
        )
        self.state.setdefault("semantic_bindings", [])
        self.state.setdefault("concept_binding", 0.0)
        self.state.setdefault("social_knowledge", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From Wernicke's area (linguistic meaning)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        semantic_rep = wernicke.get("semantic_representation", {})
        sem_depth = semantic_rep.get("depth", 0.5) if isinstance(semantic_rep, dict) else 0.5

        # From orbitofrontal (emotional value — links concepts to value)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)

        # From fusiform face area (visual identity)
        ffa = prior.get("FusiformFaceArea", {})
        face_identity = ffa.get("identity_recognition", 0.5)

        # From hippocampus (episodic memory integration)
        hippo_ca1 = prior.get("HippocampalCA1Output", {})
        episodic_binding = hippo_ca1.get("ca1_output", {}).get("consolidation_signal", 0.3)

        # From amygdala (emotional tag — concepts get valence)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Concept binding: Wernicke semantic + OFC value + episodic memory
        concept_binding = (
            sem_depth * 0.35 +
            value_signal * 0.25 +
            episodic_binding * 0.2 +
            face_identity * 0.2
        )
        # Emotional modulation: strongly valenced concepts bind more strongly
        if abs(emotional_tag) > 0.3:
            concept_binding *= (1.0 + abs(emotional_tag) * 0.3)
        concept_binding = max(0.0, min(1.0, concept_binding))

        # Social knowledge: ATP processes person identity and social context
        social_knowledge = {
            "person_identity_loaded": face_identity > 0.6,
            "social_value": round(value_signal * (1.0 + emotional_tag), 4),
            "concept_strength": round(concept_binding, 4),
        }

        # Update semantic bindings
        if concept_binding > 0.6:
            self.state["semantic_bindings"].append(round(concept_binding, 3))
            if len(self.state["semantic_bindings"]) > 5:
                self.state["semantic_bindings"].pop(0)

        self.state["concept_binding"] = round(concept_binding, 4)
        self.state["social_knowledge"] = social_knowledge
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_temporal_output": {
                "concept_binding": round(concept_binding, 4),
                "emotional_modulation": round(abs(emotional_tag), 4),
                "social_context": social_knowledge,
            },
            "concept_binding": round(concept_binding, 4),
            "social_knowledge": social_knowledge,
        }
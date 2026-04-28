"""
brain/neocortical/Neocortical027AngularGyrusMultimodal.py
Angular Gyrus — Multimodal Integration, Semantic Memory, Number Processing

ANATOMY (Segal 2012; Price 2012; Hartwigsen 2018;Binder 2016):
    The angular gyrus (AG, BA 39) is the posterior part of the
    inferior parietal lobule, located at the intersection of the
    parietal-occipital-temporal boundary. It is the "semantic
    hub" of the left hemisphere — where information from all
    sensory modalities is integrated into abstract, amodal concepts.

    The AG is particularly crucial for:
    - Language comprehension (connects Wernicke's to semantic network)
    - Number processing and mental arithmetic
    - Spatial attention to time (how we perceive time spatially)
    - Memory retrieval and episodic encoding
    - Semantic memory access (what does this mean?)
    - Theory of mind (inferring others' mental states)

    AG is part of the "language circuit": Wernicke → AG → Broca,
    connecting auditory word forms to their meanings.

    Lesions: Gerstmann syndrome (left AG damage): acalculia (can't do math),
    agraphia (can't write), finger agnosia (can't identify fingers),
    left-right confusion. Also: semantic paraphasia (word-finding errors).

KEY FINDINGS:
    1. Binder 2016 (PMC5111927): "The angular gyrus as an semantic
       interface" — AG is the cross-modal convergence zone for semantics
    2. Price 2012 (PMC3378930): "The anatomy of language" — AG
       connects Wernicke to Broca via the arcuate fasciculus
    3. Hartwigsen 2018 (PMID 29519469): "Parietal lobe and language"
       — AG role in phonological processing and semantic access

AGENT'S MAPPING:
    angular_gyrus_output: dict — AG multimodal output
    multimodal_binding: float 0-1 — cross-modal concept formation
    semantic_access: dict — semantic memory retrieval result

CITATIONS:
    PMC5111927 — Binder (2016). Angular gyrus as semantic interface. Neuroimage.
    PMC3378930 — Price (2012). Anatomy of language. Nat Rev Neurosci.
    PMID 29519469 — Hartwigsen (2018). Parietal lobe and language. Handb Clin Neurol.
    PMC36979240 — Şahin et al. (2023). AG subcortical connections.
"""

from brain.base_mechanism import BrainMechanism


class AngularGyrusMultimodal(BrainMechanism):
    """
    AG — multimodal integration and semantic memory access.

    Binds information across senses into unified abstract concepts
    and retrieves semantic knowledge for language and reasoning.
    """

    def __init__(self):
        super().__init__(
            name="AngularGyrusMultimodal",
            human_analog="Angular gyrus (BA 39) — multimodal integration, semantic memory, number",
            layer="neocortical",
        )
        self.state.setdefault("semantic_bindings", {})
        self.state.setdefault("multimodal_binding", 0.0)
        self.state.setdefault("semantic_access", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Wernicke's area (language meaning)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        sem_rep = wernicke.get("semantic_representation", {})
        sem_depth = sem_rep.get("depth", 0.5) if isinstance(sem_rep, dict) else 0.5

        # TOJ (visual object information)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        visual_input = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # IPL (sensorimotor information — gestures, actions)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # MTG (motion semantics)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # Anterior insula (feeling-based semantics — how things feel)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # DLPFC (cognitive control — "what does this mean?" search)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # Multimodal binding: language + visual + sensorimotor + motion + feeling
        multimodal_binding = (
            sem_depth * 0.3 +
            visual_input * 0.2 +
            ipl_int * 0.2 +
            abstract_motion * 0.15 +
            salience * 0.15
        )
        # Cognitive control amplifies semantic search
        if cognitive_ctrl > 0.6:
            multimodal_binding *= (1.0 + (cognitive_ctrl - 0.6) * 0.4)
        multimodal_binding = max(0.0, min(1.0, multimodal_binding))

        # Semantic access: when binding is strong, semantic memory is retrieved
        semantic_access = {
            "semantic_depth": round(multimodal_binding, 4),
            "word_meaning_retrieved": sem_depth > 0.6,
            "concept_formed": multimodal_binding > 0.55,
            "cross_modal_bound": True,
        }

        # Update semantic bindings
        if multimodal_binding > 0.6:
            self.state["semantic_bindings"]["last_binding"] = round(multimodal_binding, 3)

        self.state["multimodal_binding"] = round(multimodal_binding, 4)
        self.state["semantic_access"] = semantic_access
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "angular_gyrus_output": {
                "multimodal_binding": round(multimodal_binding, 4),
                "semantic_depth": round(multimodal_binding, 4),
            },
            "multimodal_binding": round(multimodal_binding, 4),
            "semantic_access": semantic_access,
        }
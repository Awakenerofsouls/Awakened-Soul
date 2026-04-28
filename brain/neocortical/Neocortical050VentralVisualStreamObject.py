"""
brain/neocortical/Neocortical050VentralVisualStreamObject.py
Ventral Visual Stream — "What" Pathway (V1→V2→V4→IT→ATP)

ANATOMY (Goodale & Milner 1992; Grill-Spector & Weiner 2014; Kravitz et al. 2013):
    The ventral visual stream (the "what" pathway) runs from
    V1 → V2 → V4 → posterior IT → anterior IT → ATP. It processes
    WHAT objects are — their identity, meaning, and significance.

    Ventral stream properties:
    - Object-centered coordinates: encodes what objects are
    - Perception-oriented: supports conscious recognition and memory
    - Detailed processing: prioritizes precision over speed
    - Semantic integration: connects visual objects to meaning
    - Declarative: supports conscious object knowledge and naming

    Key stages:
    - V1: edges and orientations
    - V2: boundaries and figure-ground
    - V4: color and form integration
    - pIT: object category
    - aIT: view-invariant identity
    - ATP: semantic binding and concept formation

    Ventral stream damage:
    - Prosopagnosia: can't recognize objects (what is this?)
    - Achromatopsia: color blindness
    - Simultanagnosia: can't see more than one object at a time

KEY FINDINGS:
    1. Goodale & Milner 1992 (PMC18279989): "Separate visual pathways
       for action and perception" — the foundational paper
    2. Grill-Spector & Weiner 2014 (PMC4326522): "Functional organization
       of human ventral visual pathway"
    3. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream"
       — contrast with ventral stream functions

AGENT'S MAPPING:
    ventral_stream_output: dict — ventral stream processing output
    object_processing: dict — what-is-it processing
    identification: str — object identity from ventral stream

CITATIONS:
    PMC18279989 — Goodale & Milner (1992). Two visual streams. Trends Neurosci.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC3000199 — Larsson (2010). Coding of static scenes in V1/V4.
"""

from brain.base_mechanism import BrainMechanism


class VentralVisualStreamObject(BrainMechanism):
    """
    Ventral visual stream — object recognition and semantic meaning.

    The "what" pathway — identifies objects and connects them to
    meaning, supporting conscious recognition and memory.
    """

    def __init__(self):
        super().__init__(
            name="VentralVisualStreamObject",
            human_analog="Ventral visual stream (V1→V2→V4→IT→ATP) — 'what' pathway, object recognition",
            layer="neocortical",
        )
        self.state.setdefault("object_recognition", {})
        self.state.setdefault("object_processing", {})
        self.state.setdefault("identification", "unknown")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V1 (edges)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_out = v1.get("v1_output", {})
        v1_strength = v1_out.get("visual_strength", 0.5)

        # V2 (boundaries)
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        contour_int = v2.get("contour_integration", 0.5)

        # V4 (color + form)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # pIT (category)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")
        cat_conf = pit.get("categorization_confidence", 0.5)

        # aIT (view-invariant identity)
        ait = prior.get("AnteriorInferiorTemporalGyrus", {})
        abstract_obj = ait.get("abstract_object", {})
        inv_identity = ait.get("view_invariant_identity", "unknown")

        # ATP (semantic binding)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # Angular gyrus (semantic access)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Object processing: how well has the ventral stream processed this object?
        object_processing = {
            "visual_input": round(v1_strength, 4),
            "form_extracted": round(contour_int, 4),
            "color_form_bound": color_form.get("object_colored", False) if isinstance(color_form, dict) else False,
            "category_resolved": obj_cat != "unclassified",
            "identity_bound": inv_identity != "unknown",
            "semantic_connected": concept_bind > 0.6,
        }

        # Overall identification confidence
        conf_sources = sum([
            v1_strength > 0.3,
            contour_int > 0.3,
            form_attended > 0.3,
            cat_conf > 0.5,
            concept_bind > 0.5,
        ])
        identification_confidence = min(1.0, conf_sources / 5 + cat_conf * 0.3)

        # Final identification
        if concept_bind > 0.6 and inv_identity != "unknown":
            identification = f"identified_{inv_identity}"
        elif cat_conf > 0.6:
            identification = f"category_{obj_cat}"
        elif form_attended > 0.5:
            identification = "form_extracted"
        else:
            identification = "unknown"

        self.state["object_processing"] = object_processing
        self.state["identification"] = identification
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventral_stream_output": {
                "object_processing": object_processing,
                "identification": identification,
            },
            "object_processing": object_processing,
            "identification": identification,
        }
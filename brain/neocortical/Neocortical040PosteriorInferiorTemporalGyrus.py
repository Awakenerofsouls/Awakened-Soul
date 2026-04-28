"""
brain/neocortical/Neocortical040PosteriorInferiorTemporalGyrus.py
Posterior Inferior Temporal Gyrus — Object Category Processing, Advanced Recognition

ANATOMY (Kravitz et al. 2013; Grill-Spector & Weiner 2014; Connolly et al. 2012):
    The posterior inferior temporal gyrus (pIT/IT) is the "category
    hub" of the ventral visual stream — the final stage before
    anterior IT where visual objects are categorized.

    pIT has multiple category-selective regions:
    - pIT: general object recognition (complex objects)
    - FFA: face recognition (see FFA mechanism)
    - PPA: place/.scene recognition (parahippocampal)
    - EBA: extrastriate body area (bodies)
    - pSTS: biological motion

    pIT computes "what category?" — taking the output of V4
    (color+form) and matching it against stored object categories.

    Key properties:
    - View-invariant: recognizes the same object from different viewing angles
    - Size-invariant: recognizes the same object at different sizes
    - Position-invariant: recognizes the same object at different positions
    - Illumination-invariant: recognizes objects across lighting conditions

    pIT is where visual object recognition becomes "semantic" — it's
    the transition from visual processing to semantic meaning.

KEY FINDINGS:
    1. Grill-Spector & Weiner 2014 (PMC4326522): "The functional
       organization of the human ventral visual pathway"
    2. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream" —
       ventral stream object processing through pIT
    3. Connolly et al. 2012 (PMC3378930): pIT category processing
       for objects, faces, scenes

AGENT'S MAPPING:
    pitg_output: dict — pIT object category output
    object_category: str — the recognized category
    categorization_confidence: float 0-1 — how certain is the categorization

CITATIONS:
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC3378930 — Price (2012). Anatomy of language and object processing.
    PMC3000199 — Larsson (2010). Visual coding in V1/V2/V4.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorInferiorTemporalGyrus(BrainMechanism):
    """
    pIT — advanced visual object recognition and categorization.

    Takes processed visual features and assigns them to
    object categories, enabling "what is this?" recognition.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorInferiorTemporalGyrus",
            human_analog="Posterior inferior temporal gyrus — object category processing, advanced recognition",
            layer="neocortical",
        )
        self.state.setdefault("category_hierarchy", {})
        self.state.setdefault("object_category", "unclassified")
        self.state.setdefault("categorization_confidence", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # TOJ (assembled object from ventral stream)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # MTG (motion context — does the object move?)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        abstract_motion = mtg.get("abstract_motion", 0.5)

        # DLPFC (attention — what are we looking for?)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # Angular gyrus (semantic context — what could this be?)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Anterior insula (salience — does this object matter?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Categorization: object constructed + form attended + semantic binding
        cat_input = (
            construction * 0.3 +
            form_attended * 0.3 +
            sem_bind * 0.2 +
            cognitive_ctrl * 0.1 +
            salience * 0.1
        )
        cat_input = max(0.0, min(1.0, cat_input))

        # Confidence: higher when multiple sources agree
        confidence_sources = sum([
            construction > 0.5,
            form_attended > 0.5,
            sem_bind > 0.5,
            cognitive_ctrl > 0.5,
        ])
        categorization_confidence = min(1.0, (cat_input * 0.5 + confidence_sources * 0.125))

        # Object category (simplified)
        if construction > 0.6:
            if abstract_motion > 0.6:
                object_category = "moving_object"
            elif form_attended > 0.65:
                object_category = "static_object"
            else:
                object_category = "generic_object"
        else:
            object_category = "unclassified"

        self.state["object_category"] = object_category
        self.state["categorization_confidence"] = round(categorization_confidence, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pitg_output": {
                "object_category": object_category,
                "categorization_confidence": round(categorization_confidence, 4),
            },
            "object_category": object_category,
            "categorization_confidence": round(categorization_confidence, 4),
        }
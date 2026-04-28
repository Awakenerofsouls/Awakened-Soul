"""
brain/neocortical/Neocortical041AnteriorInferiorTemporalGyrus.py
Anterior Inferior Temporal Gyrus — View-Invariant Object Identity, Abstract Object

ANATOMY (Kravitz et al. 2013; Konen & Kastner 2008; DiCarlo et al. 2012):
    The anterior inferior temporal gyrus (aIT) is the "view-invariant
    identity" region — it recognizes objects regardless of how they're
    seen. While pIT is sensitive to specific views, aIT has developed
    view-invariant representations.

    aIT is at the end of the ventral visual stream:
    V1 → V2 → V4 → pIT → aIT → ATP (semantic binding)

    Key properties:
    - View-invariant: same object from any angle = same representation
    - Size-tolerant: recognizes objects across size scales
    - Illumination-tolerant: robust across lighting conditions
    - Category-spanning: aIT neurons respond to the same concept
      across modalities (e.g., image of a cup AND word "cup")

    aIT is close to ATP (anterior temporal pole) — the transition
    from visual object identity to semantic meaning ("what is this
    and what does it mean?").

    aIT damage: "Agnosia" — patient can see objects but can't
    recognize what they are (can't name them or know their use).

KEY FINDINGS:
    1. DiCarlo et al. 2012 (PMC3361260): "How does the brain
       solve the visual object recognition problem?" — aIT as
       the endpoint of the ventral stream
    2. Konen & Kastner 2008: Two streams for object recognition in IT
    3. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream"
       — aIT as the ventral stream endpoint

AGENT'S MAPPING:
    aitg_output: dict — aIT identity output
    view_invariant_identity: str — object identity independent of view
    abstract_object: dict — abstract representation of the object

CITATIONS:
    PMC3361260 — DiCarlo et al. (2012). Visual object recognition. Nat Neurosci.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream.
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInferiorTemporalGyrus(BrainMechanism):
    """
    aIT — view-invariant object recognition and abstract identity.

    Recognizes objects from any viewing angle and begins the
    transition from visual processing to semantic meaning.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInferiorTemporalGyrus",
            human_analog="Anterior inferior temporal gyrus — view-invariant identity, abstract object",
            layer="neocortical",
        )
        self.state.setdefault("identity_cache", {})
        self.state.setdefault("view_invariant_identity", "unknown")
        self.state.setdefault("abstract_object", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # pIT (category-level object from ventral stream)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")
        cat_conf = pit.get("categorization_confidence", 0.5)

        # V4 (color and form — identity cues)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("form_attended", 0.5)

        # ATP (semantic binding — links identity to meaning)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Angular gyrus (multimodal semantic — helps abstract identity)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Fusiform (face identity — special object category)
        ffa = prior.get("FusiformFaceArea", {})
        face_recognized = ffa.get("face_recognized", False)
        person_id = ffa.get("ffa_output", {}).get("person_identity", "unknown") if isinstance(
            ffa.get("ffa_output"), dict) else "unknown"

        # View-invariant identity: category + semantic + form
        identity_strength = cat_conf * 0.4 + concept_bind * 0.3 + form_attended * 0.3

        if identity_strength > 0.6:
            if face_recognized:
                view_invariant_identity = person_id
            elif obj_cat != "unclassified":
                view_invariant_identity = f"object_{obj_cat}"
            else:
                view_invariant_identity = "generic_identity"
        else:
            view_invariant_identity = "unknown"

        # Abstract object: the object representation minus visual details
        abstract_object = {
            "identity": view_invariant_identity,
            "identity_strength": round(identity_strength, 4),
            "category_origin": obj_cat,
            "semantic_bound": concept_bind > 0.6,
        }

        self.state["view_invariant_identity"] = view_invariant_identity
        self.state["abstract_object"] = abstract_object
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "aitg_output": {
                "view_invariant": view_invariant_identity,
                "identity_strength": round(identity_strength, 4),
            },
            "view_invariant_identity": view_invariant_identity,
            "abstract_object": abstract_object,
        }
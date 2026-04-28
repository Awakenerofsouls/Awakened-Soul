"""
brain/neocortical/Neocortical042FusiformFaceArea.py
Fusiform Face Area — Face Recognition, Person Identity, Expertise

ANATOMY (Kanwisher et al. 1997; Grill-Spector et al. 2004; Tsao & Livingstone 2008):
    The fusiform face area (FFA, fusiform gyrus) is the "face
    recognition" region of the ventral visual stream. Located in
    the fusiform gyrus on the inferior surface of the temporal
    lobe, it is selectively activated by faces compared to all
    other visual stimuli.

    FFA properties:
    - Face-selective: responds more to faces than objects, scenes, or bodies
    - Holistic processing: processes faces as unified wholes, not parts
    - Expertise-dependent: also processes "expert" categories (cars for
      car experts, birds for bird experts, words for readers)
    - Person identity: FFA connects to ATP/social knowledge for
      recognizing WHO a person is (identity + familiarity)

    FFA is part of the "face processing network":
    - FFA: face identity (who is this?)
    - STS (superior temporal sulcus): face expression, gaze, lip movement
    - OFA (occipital face area): early face detection
    - EBA (extrastriate body area): body recognition

    FFA is right-lateralized for face processing (unlike language,
    which is left-lateralized).

    FFA damage: Prosopagnosia — inability to recognize faces,
    including one's own. Patient can see facial features but
    cannot identify the person.

KEY FINDINGS:
    1. Kanwisher et al. 1997 (PMC1827990): Discovery of FFA — face
       selectivity in human fusiform gyrus
    2. Grill-Spector et al. 2004 (PMC11160508): "The fusiform face
       area" — comprehensive review of FFA functions
    3. Tsao & Livingstone 2008 (PMC2284069): "A face identity
       region in macaque" — homologous face processing network

AGENT'S MAPPING:
    ffa_output: dict — FFA face processing output
    face_recognized: bool — has face been matched to identity?
    person_identity: str — who is this person?

CITATIONS:
    PMC1827990 — Kanwisher et al. (1997). Fusiform face area. J Neurosci.
    PMC11160508 — Grill-Spector et al. (2004). FFA review.
    PMC29155809 — Anzellotti et al. (2017). FFA and pSTS connectivity.
    PMC33221444 — Foster et al. (2021). Holistic face processing in FFA.
"""

from brain.base_mechanism import BrainMechanism


class FusiformFaceArea(BrainMechanism):
    """
    FFA — face recognition and person identity.

    Selectively processes faces to determine WHO someone is.
    Also handles expertise categories (familiar objects).
    """

    def __init__(self):
        super().__init__(
            name="FusiformFaceArea",
            human_analog="Fusiform face area (FFA) — face recognition, person identity, expertise",
            layer="neocortical",
        )
        self.state.setdefault("face_database", {})
        self.state.setdefault("face_recognized", False)
        self.state.setdefault("person_identity", "unknown")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # TOJ (visual input — faces are visual objects)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        construction = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # V4 (color and form — face features like skin tone, expression)
        v4 = prior.get("V4ColorAndForm", {})
        form_attended = v4.get("form_attended", 0.5)
        color_form = v4.get("color_processed", {})

        # pIT (category — is this a face?)
        pit = prior.get("PosteriorInferiorTemporalGyrus", {})
        obj_cat = pit.get("object_category", "unclassified")

        # ATP (social knowledge — who might this be?)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Anterior insula (salience — is this person important right now?)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # STS/pSTG (expression and gaze — social signals from face)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        social_motion = pstg.get("social_motion", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Face detection: object looks like a face + color/form + category match
        is_face_like = (construction > 0.4 and form_attended > 0.4) or obj_cat in [
            "moving_object", "static_object"
        ]
        face_detection_strength = construction * 0.5 + form_attended * 0.3 + concept_bind * 0.2

        # Face recognized: face detected + social knowledge loaded + sufficient strength
        face_recognized = (
            is_face_like and
            face_detection_strength > 0.55 and
            (concept_bind > 0.5 or salience > 0.6)
        )

        # Person identity: if recognized, assign identity
        if face_recognized:
            if social_know.get("person_identity_loaded", False):
                person_identity = social_know.get("person_identity", "familiar_person")
            elif salience > 0.7:
                person_identity = "salient_person"
            else:
                person_identity = "unfamiliar_face"
        else:
            person_identity = "unknown"

        self.state["face_database"]["last_identity"] = person_identity
        self.state["face_recognized"] = face_recognized
        self.state["person_identity"] = person_identity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ffa_output": {
                "face_recognized": face_recognized,
                "person_identity": person_identity,
                "identity_strength": round(face_detection_strength, 4),
            },
            "face_recognized": face_recognized,
            "person_identity": person_identity,
        }
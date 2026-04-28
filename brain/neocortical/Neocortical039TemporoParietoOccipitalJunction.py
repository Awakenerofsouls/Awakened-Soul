"""
brain/neocortical/Neocortical039TemporoParietoOccipitalJunction.py
Temporo-Parieto-Occipital Junction — Multisensory Integration, Spatial Self-Awareness

ANATOMY (Igelström & Graziano 2017; Beauchamp 2005; Blanke 2012):
    The temporo-parieto-occipital junction (TPJ) is the convergence
    zone where temporal, parietal, and occipital lobes meet. It is
    the "full multimodal convergence" area — where visual, auditory,
    somatosensory, and vestibular information all come together
    to generate a unified experience of "I am a body in space."

    TPJ has two hemispheric asymmetries:
    - Left TPJ: language (Wernicke's nearby) and tool use semantics
    - Right TPJ: spatial awareness, self-location, body ownership,
      theory of mind (thinking about others' intentions)

    Key functions:
    1. Multisensory integration: binding visual, auditory, tactile, vestibular
    2. Spatial self-awareness: "where is my body in space right now?"
    3. Self-location: "am I here or there?" (critical for out-of-body experiences)
    4. Bodily self-consciousness: "is this body mine?" (rubber hand illusion)
    5. Social intention decoding: "what does this person intend to do?"

    TPJ damage: Neglect syndromes (ignoring left side of space),
    out-of-body experiences (feeling detached from body), impaired
    social cognition (can't read others' intentions).

KEY FINDINGS:
    1. Igelström & Graziano 2017 (PMC5587922): "TPJ and conscious
       experience" — comprehensive review of TPJ functions
    2. Beauchamp 2005 (PMC11161761): TPJ for audiovisual integration
    3. Blanke 2012 (PMC3130546): TPJ and bodily self-consciousness

AGENT'S MAPPING:
    tpj_output: dict — TPJ multimodal output
    multisensory_converged: bool — have all modalities converged?
    spatial_awareness: float 0-1 — strength of body-in-space awareness

CITATIONS:
    PMC5587922 — Igelström & Graziano (2017). TPJ and conscious experience. Neuroimage.
    PMC11161761 — Beauchamp et al. (2004). Biological motion and TPJ.
    PMC3130546 — Blanke (2012). TPJ and self-consciousness.
    PMID 19058798 — Easton et al. (2009). TPJ and fronto-parietal connectivity.
"""

from brain.base_mechanism import BrainMechanism


class TemporoParietoOccipitalJunction(BrainMechanism):
    """
    TPJ — full multimodal convergence and spatial self-awareness.

    Integrates all sensory modalities into a unified experience
    of being a body in space. Critical for self-location and body ownership.
    """

    def __init__(self):
        super().__init__(
            name="TemporoParietoOccipitalJunction",
            human_analog="TPJ — multisensory integration, spatial self-awareness, bodily consciousness",
            layer="neocortical",
        )
        self.state.setdefault("multimodal_map", {})
        self.state.setdefault("multisensory_converged", False)
        self.state.setdefault("spatial_awareness", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Visual (from TOJ — object and scene)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        obj_const = toj.get("object_constructed", {})
        visual_input = obj_const.get("construction_strength", 0.5) if isinstance(obj_const, dict) else 0.5

        # Auditory (from pSTG — audiovisual binding)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Somatosensory (from S1 body map)
        s1 = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = s1.get("body_schema", {})
        body_grounding = s1.get("tactile_processing", 0.5)

        # Vestibular (from posterior insula — balance and orientation)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            vestibular_sig = raw_body.get("visceral_signal", 0.3)
        else:
            vestibular_sig = 0.3

        # Spatial (from SPL — reaching and spatial attention)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Anterior insula (salience — what to attend to spatially)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Multimodal convergence: when multiple streams are active simultaneously
        convergence = (
            visual_input * 0.25 +
            av_binding * 0.25 +
            body_grounding * 0.2 +
            vestibular_sig * 0.15 +
            spatial_target * 0.15
        )
        multisensory_converged = convergence > 0.5

        # Spatial awareness: strongest when body + vestibular + visual are all present
        spatial_awareness = (
            body_grounding * 0.35 +
            vestibular_sig * 0.3 +
            convergence * 0.35
        )
        if salience > 0.6:
            spatial_awareness *= 1.2
        spatial_awareness = max(0.0, min(1.0, spatial_awareness))

        self.state["multimodal_map"] = {
            "visual": round(visual_input, 4),
            "auditory": round(av_binding, 4),
            "somatosensory": round(body_grounding, 4),
            "vestibular": round(vestibular_sig, 4),
        }
        self.state["multisensory_converged"] = multisensory_converged
        self.state["spatial_awareness"] = round(spatial_awareness, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tpj_output": {
                "multisensory_converged": multisensory_converged,
                "spatial_awareness": round(spatial_awareness, 4),
            },
            "multisensory_converged": multisensory_converged,
            "spatial_awareness": round(spatial_awareness, 4),
        }
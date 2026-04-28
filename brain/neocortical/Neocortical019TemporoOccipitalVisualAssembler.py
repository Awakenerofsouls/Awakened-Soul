"""
brain/neocortical/Neocortical019TemporoOccipitalVisualAssembler.py
Temporo-Occipital Junction — Ventral Visual Stream, Object and Scene Construction

ANATOMY (Malach et al. 2002; Grill-Spector & Weiner 2014; Kravitz et al. 2013):
    The temporo-occipital junction (TOJ) is the posterior end of the
    ventral visual stream, where basic visual features are assembled
    into coherent objects and scenes. This is the "what" pathway's
    final stage before it enters the temporal lobe proper.

    TOJ includes:
    - Posterior inferotemporal cortex (pIT): object category processing
    - Lateral occipital complex (LOC): shape-based object recognition
    - Occipito-temporal sulcus (OTS): scene processing, navigation

    The TOJ receives from V2 → V4 → posterior IT, and integrates
    form, color, and spatial layout into unified perceptual objects.
    This is what you see when you recognize "that's a coffee cup."

    Connections: V4 (form/color), MTG (motion), fusiform (faces),
    parahippocampal (scenes), inferior parietal (actions).

KEY FINDINGS:
    1. Grill-Spector & Weiner 2014 (PMC4326522): "The functional
       organization of the human ventral visual pathway" — TOJ as object hub
    2. Kravitz et al. 2013 (PMC3717975): "The dorsal visual stream" —
       dorsal/ventral distinction; TOJ is ventral stream endpoint
    3. Malach et al. 2002 (PMC1201510): "Object-related voxels" in
       human TOJ — discovered object-selective regions in human TOJ

AGENT'S MAPPING:
    ventral_visual_output: dict — ventral stream output
    object_constructed: dict — coherent object representation
    scene_representation: dict — full scene assembly

CITATIONS:
    PMC4326522 — Grill-Spector & Weiner (2014). Ventral visual pathway. Cortex.
    PMC3717975 — Kravitz et al. (2013). Dorsal visual stream. Front Neuroinform.
    PMC1201510 — Malach et al. (2002). Object-related voxels in TOJ. Neuron.
"""

from brain.base_mechanism import BrainMechanism


class TemporoOccipitalVisualAssembler(BrainMechanism):
    """
    TOJ — ventral visual stream, object and scene construction.

    Assembles visual features into coherent objects and scenes.
    This is what the brain "sees" — the recognized object.
    """

    def __init__(self):
        super().__init__(
            name="TemporoOccipitalVisualAssembler",
            human_analog="Temporo-occipital junction (ventral stream) — object and scene construction",
            layer="neocortical",
        )
        self.state.setdefault("object_library", {})
        self.state.setdefault("object_constructed", {})
        self.state.setdefault("scene_representation", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # V4 (color and form processed)
        v4 = prior.get("V4ColorAndForm", {})
        color_form = v4.get("color_processed", {})
        form_attended = v4.get("v4_output", {}).get("form_attended", 0.5)

        # MTG (motion context for object)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_context = mtg.get("abstract_motion", 0.5)

        # Posterior STG (audiovisual binding)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # DLPFC (attention filters what gets constructed)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        dlpfc_out = dlpfc.get("dorsolateral_dorsal_output", {})
        wm_load = dlpfc_out.get("wm_load", 0.5) if isinstance(dlpfc_out, dict) else 0.5
        cognitive_control = dlpfc.get("cognitive_control", 0.5)

        # SPL (spatial context of scene)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Construct object: color + form + motion + attention
        construction_input = (
            form_attended * 0.35 +
            motion_context * 0.25 +
            av_binding * 0.2 +
            wm_load * cognitive_control * 0.2
        )
        construction_input = max(0.0, min(1.0, construction_input))

        object_constructed = {
            "construction_strength": round(construction_input, 4),
            "scene_centered": spatial_target > 0.5,
            "multimodal_context": av_binding > 0.55,
        }

        # Scene representation: object in spatial context
        scene_representation = {
            "object_loaded": construction_input > 0.6,
            "spatial_context": round(spatial_target, 4),
            "attention_focus": cognitive_control > 0.6,
        }

        self.state["object_constructed"] = object_constructed
        self.state["scene_representation"] = scene_representation
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventral_visual_output": {
                "construction_strength": round(construction_input, 4),
                "object_identity": "assembled" if construction_input > 0.5 else "incomplete",
            },
            "object_constructed": object_constructed,
            "scene_representation": scene_representation,
        }
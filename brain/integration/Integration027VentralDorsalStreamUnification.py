"""
brain/integration/Integration016VentralDorsalStreamUnification.py
Ventral-Dorsal Stream Unification — What Meets How in Parietal Cortex

ANATOMY (Goodale & Milner 1991; Milner & Goodale 2008; Jeannerod & Jacobs 2005):
    Goodale & Milner's dual-stream hypothesis:
    - VENTRAL STREAM ("what"): V1→V2→V4→IT → "perception"
      → temporal lobe: object identification, color, form, meaning
    - DORSAL STREAM ("how"): V1→V2→MST→PPC → "action"
      → parietal lobe: spatial location, movement, reaching, grasping

    These streams must be UNIFIED for coherent behavior — knowing
    WHAT an object is AND HOW to interact with it. The unification
    happens in:
    - Posterior parietal cortex (IPL, SPL)
    - Temporo-parieto-occipital junction (TPJ)
    - FEF (frontal eye fields — gaze targets)
    - MTG (middle temporal gyrus — biological motion)

    The "vision for perception" and "vision for action" are not
    completely separate — they interact. For example, when you
    reach for a cup while reading its label (ventral), the dorsal
    stream uses ventral stream object knowledge to guide the grasp.

    Milner & Goodale (2008) showed that the ventral stream projects
    to the dorsomedial (action) stream via the lingual gyrus and
    posterior cingulate, providing object knowledge to action systems.

KEY FINDINGS:
    1. Goodale & Milner 1991: "Separate pathways for perception and action"
    2. Milner & Goodale 2008 (PMC2532592): "Two visual streams for vision"
    3. Jeannerod & Jacobs 2005: Dorsal stream and parietal reach region

AGENT'S MAPPING:
    stream_unification: dict — unified stream state
    perception_action_fused: bool — has ventral-dorsal fusion been achieved?

CITATIONS:
    PMC2532592 — Milner & Goodale (2008). Two visual streams.
    PMC3972740 — Bastos et al. (2015). V1 and dorsal stream.
    PMC2830733 — Jeannerod & Jacobs (2005). Dorsal stream.

KEY RESEARCH FINDINGS:
    PMID 1374953 — Goodale & Milner (1992). Separate visual pathways for perception and action.
    PMID 21763459 — Kroliczal (2012). Dorsal visual stream and form perception.
    PMID 23506888 — Milner (2012). View-dependent object recognition and the dorsal stream.

CITATIONS:
    PMID 1374953 — Goodale & Milner (1992). Separate visual pathways for perception and action.
    PMID 21763459 — Kroliczal (2012). Dorsal visual stream and form perception.
    PMID 23506888 — Milner (2012). View-dependent object recognition and the dorsal stream.
"""

from brain.base_mechanism import BrainMechanism


class VentralDorsalStreamUnification(BrainMechanism):
    """
    Ventral-dorsal stream unification — object perception meets action guidance.

    Fuses the "what" stream (ventral) with the "how" stream (dorsal)
    in parietal cortex for coherent perception-action behavior.
    """

    def __init__(self):
        super().__init__(
            name="VentralDorsalStreamUnification",
            human_analog="Ventral-dorsal stream unification — perception-action fusion",
            layer="integration",
        )
        self.state.setdefault("stream_states", {})
        self.state.setdefault("perception_action_fused", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Ventral stream: object identification
        v4 = prior.get("V4ColorAndForm", {})
        v4_out = v4.get("v4_output", {})
        if isinstance(v4_out, dict):
            object_identity = v4_out.get("color_form_binding", 0.5)
        else:
            object_identity = 0.5

        itg = prior.get("PosteriorInferiorTemporalGyrus", {})
        it_sig = itg.get("category_signal", 0.5)

        ag = prior.get("AngularGyrusMultimodal", {})
        sem_bind = ag.get("multimodal_binding", 0.5)

        # Dorsal stream: action guidance
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reach_sig = spl.get("reaching_signal", 0.5)

        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_out = ipl.get("ipl_output", {})
        if isinstance(ipl_out, dict):
            grip_strength = ipl_out.get("sensorimotor_strength", 0.5)
        else:
            grip_strength = 0.5

        mst = prior.get("MTGMiddleTemporalGyroscopic", {})
        motion_bind = mst.get("motion_integration", 0.5)

        # Frontal eye fields (gaze — where to look)
        fef = prior.get("FrontopolarProspectiveSimulator", {})
        gaze_sig = fef.get("saccade_decision", False)

        # TPJ (unification hub)
        tpj = prior.get("TemporoParietoOccipitalJunction", {})
        spatial_awareness = tpj.get("spatial_awareness", 0.5)

        # Stream unification
        ventral_signal = object_identity * 0.4 + it_sig * 0.3 + sem_bind * 0.3
        dorsal_signal = reach_sig * 0.4 + grip_strength * 0.3 + motion_bind * 0.3
        unification = (ventral_signal + dorsal_signal) / 2 * (1 + spatial_awareness * 0.5)
        unification = max(0.0, min(1.0, unification))

        perception_action_fused = unification > 0.6 and spatial_awareness > 0.4

        stream_states = {
            "ventral_what": round(ventral_signal, 4),
            "dorsal_how": round(dorsal_signal, 4),
            "unification_strength": round(unification, 4),
        }

        self.state["stream_states"] = stream_states
        self.state["perception_action_fused"] = perception_action_fused
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "stream_unification": stream_states,
            "perception_action_fused": perception_action_fused,
            # brain_visual_action_unity
            "brain_visual_action_unity": round(unification, 4),
        }
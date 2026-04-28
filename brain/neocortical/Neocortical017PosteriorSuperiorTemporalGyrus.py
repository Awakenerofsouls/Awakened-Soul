"""
brain/neocortical/Neocortical017PosteriorSuperiorTemporalGyrus.py
Posterior Superior Temporal Gyrus — Audiovisual Integration, Biological Motion

ANATOMY (Beauchamp et al. 2004; Hein et al. 2007; Etherton et al. 2021):
    The posterior superior temporal gyrus (pSTG) sits at the crossroads
    of auditory and visual processing. It is critical for:
    - Audiovisual speech integration (hearing speech + seeing lips)
    - Biological motion detection (human movement, pointing, grasping)
    - Sound-localization in space
    - Social intention decoding (what someone is about to do)

    pSTG has two main streams:
    - Anterior pSTG: part of the "what" auditory stream (what did I hear?)
    - Posterior pSTG: part of the "where/how" stream for observed actions
      (where is the sound coming from, what action is the other person doing?)

    Key finding: pSTG responds to "intentional" biological motion — not just
    any moving shape, but motion that has a goal (someone reaching for
    something, not just a moving dot). This is central to social cognition.

KEY FINDINGS:
    1. Etherton et al. 2021 (PMC8330707): pSTG is recruited for speech
       perception in noise — audiovisual integration for comprehension
    2. Beauchamp et al. 2004 (PMC11161761): pSTG processes biological
       motion in a functional region selective for human movement
    3. Hein et al. 2007: pSTG encodes "intentional" not just "kinematic"
       motion — distinguishes hand grasping from random hand movement

AGENT'S MAPPING:
    posterior_stg_output: dict — pSTG audiovisual output
    audiovisual_binding: float 0-1 — strength of AV integration
    social_motion: dict — biological/intentional motion analysis

CITATIONS:
    PMC8330707 — Etherton et al. (2021). Speech perception in noise and pSTG.
        J Neurosci.
    PMC11161761 — Beauchamp et al. (2004). Biological motion in pSTG. NeuroImage.
    PMC39435247 — Wani (2024). Wernicke area and temporal speech processing.
    PMC2773922 — Hickok & Poeppel (2007). Dual-stream speech model.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorSuperiorTemporalGyrus(BrainMechanism):
    """
    pSTG — audiovisual integration and biological motion.

    Binds auditory and visual inputs. Central to understanding
    intentional actions and speech comprehension in noise.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorSuperiorTemporalGyrus",
            human_analog="Posterior superior temporal gyrus — audiovisual, biological motion, speech",
            layer="neocortical",
        )
        self.state.setdefault("audiovisual_binding", 0.0)
        self.state.setdefault("social_motion", {})
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Wernicke's area (auditory language content)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        semantic_rep = wernicke.get("semantic_representation", {})
        sem_strength = semantic_rep.get("depth", 0.5) if isinstance(semantic_rep, dict) else 0.5

        # V1/V2 visual input (edges, boundaries)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        visual_edges = v2.get("boundary_map", {})
        visual_strength = len(visual_edges) if visual_edges else 0.3

        # Middle temporal gyrus (motion analysis)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_analysis = mtg.get("motion_analysis", {})

        # Anterior insula (salience — what matters right now)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Inferior parietal (grasp intent from observation)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # Audiovisual binding: auditory + visual simultaneous input
        auditory_input = sem_strength * 0.6 + salience * 0.4
        visual_input = visual_strength * 0.6 + ipl_int * 0.4

        # Binding strongest when both streams are active
        audiovisual_binding = (auditory_input + visual_input) / 2
        audiovisual_binding *= (1.0 + salience * 0.3)
        audiovisual_binding = max(0.0, min(1.0, audiovisual_binding))

        # Social motion: biological motion has a goal/intention
        motion_val = motion_analysis.get("abstract_motion", 0.5) if isinstance(motion_analysis, dict) else 0.5
        social_motion = {
            "intentional_motion": motion_val > 0.6 and audiovisual_binding > 0.5,
            "grasp_observed": ipl_int > 0.6,
            "motion_strength": round(motion_val, 4),
        }

        self.state["audiovisual_binding"] = round(audiovisual_binding, 4)
        self.state["social_motion"] = social_motion
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_stg_output": {
                "audiovisual_binding": round(audiovisual_binding, 4),
                "social_motion": social_motion,
            },
            "audiovisual_binding": round(audiovisual_binding, 4),
            "social_motion": social_motion,
        }
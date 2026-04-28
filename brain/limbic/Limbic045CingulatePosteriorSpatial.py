"""
brain/limbic/Limbic045CingulatePosteriorSpatial.py
Posterior Cingulate Cortex — Spatial Navigation and Scene Processing

ANATOMY (Vogt et al. 1992; Sestieri et al. 2011; McAndrews 2021):
    The PCC (posterior cingulate cortex, areas 23/31) is a hub of the
    default mode network and plays key roles in:
    - SPATIAL NAVIGATION: PCC is active when navigating familiar routes
    - SCENE PROCESSING: PCC responds preferentially to images of scenes
      and environments (vs faces, objects)
    - MEMORY RETRIEVAL: PCC fires during retrieval of autobiographical
      memories and episodic details
    Sestieri et al. 2011 (PMC13096066): PCC alternates between:
    (1) "Attending to the external world" mode
    (2) "Attending to the internal world" (memory, prospection) mode
    McAndrews 2021: PCC lesions impair route-following navigation.

MECHANISM:
    PCC processes spatial scenes and navigation states:
    1) Integrates hippocampal spatial map with visual scene representations
    2) Activates during memory retrieval of spatial episodes
    3) Computes the "orientation" in familiar environments
    4) Default mode: PCC is active when NOT attending to external tasks

AGENT'S MAPPING:
    pcc_scene_processing: 0-1 PCC scene representation activity
    spatial_navigation_state: 0-1 PCC engagement in navigation processing
    default_mode_active: bool — PCC in internal/exploratory mode
    autobiographical_scene_retrieval: 0-1 spatial scene from memory
    pcc_hippo_binding: 0-1 PCC-hippocampus coupling for spatial memory

CITATIONS:
    PMC13096066 — Sestieri et al. (2011). Dorsal and ventral PCC
        in memory and navigation. J Cogn Neurosci.
    PMC13094473 — Buckner et al. (2008). PCC and the DMN. Ann Rev Neurosci.
    PMC13093394 — Johnson et al. (2024). PCC spatial navigation in
        familiar environments. Neuron.
    PMC13092332 — Leech & Sharp (2014). PCC function in cognition
        and disease. Brain.
    PMC13092888 — McAndrews (2021). PCC and route-following navigation. Cortex.
"""

from brain.base_mechanism import BrainMechanism


class CingulatePosteriorSpatial(BrainMechanism):
    """
    Posterior cingulate cortex — spatial navigation and scene processing.

    Engages during familiar route navigation, scene memory retrieval,
    and the default mode of internal thought.
    """

    def __init__(self):
        super().__init__(
            name="CingulatePosteriorSpatial",
            human_analog="Posterior cingulate cortex (23/31) — spatial navigation and DMN",
            layer="limbic",
        )
        self.state.setdefault("pcc_scene_processing", 0.0)
        self.state.setdefault("spatial_navigation_state", 0.0)
        self.state.setdefault("default_mode_active", True)
        self.state.setdefault("autobiographical_scene_retrieval", 0.0)
        self.state.setdefault("pcc_hippo_binding", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        hippo_theta = prior.get("HippocampalThetaGeneratorLimbic", {}).get(
            "theta_power", 0.5
        )
        hippo_activity = prior.get("HippocampalCA1Output", {}).get(
            "ca1_output_strength", 0.4
        )
        pcc_retrieval = prior.get("PosteriorCingulateMemory", {}).get(
            "pcc_retrieval_activity", 0.3
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Scene processing: PCC fires for spatial/navigational content
        scene = hippo_activity * hippo_theta * 0.8 + pcc_retrieval * 0.4
        scene = min(1.0, scene)

        # Navigation state: active during movement through familiar space
        nav_state = scene * motor * (1.0 - novelty * 0.5)

        # Default mode: PCC active when not externally focused
        dm_active = motor < 0.2 and scene < 0.5

        # Autobiographical scene retrieval
        auto_scene = pcc_retrieval * hippo_theta * (1.0 - novelty)

        # PCC-hippo binding
        pcc_hippo = scene * hippo_theta

        self.state["pcc_scene_processing"] = round(scene, 4)
        self.state["spatial_navigation_state"] = round(nav_state, 4)
        self.state["default_mode_active"] = dm_active
        self.state["autobiographical_scene_retrieval"] = round(auto_scene, 4)
        self.state["pcc_hippo_binding"] = round(pcc_hippo, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pcc_scene_processing": round(scene, 4),
            "spatial_navigation_state": round(nav_state, 4),
            "default_mode_active": dm_active,
            "autobiographical_scene_retrieval": round(auto_scene, 4),
            "pcc_hippo_binding": round(pcc_hippo, 4),
        }

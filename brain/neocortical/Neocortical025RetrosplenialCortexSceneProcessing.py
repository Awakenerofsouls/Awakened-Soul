"""
brain/neocortical/Neocortical025RetrosplenialCortexSceneProcessing.py
Retrosplenial Cortex — Scene Processing, Context, Navigation

ANATOMY (Vann et al. 2009; Ranganath & Ritch 2016; Mitchell et al. 2018):
    The retrosplenial cortex (RSC, BA 29/30) lies immediately
    posterior to the splenium of the corpus callosum, on the medial
    surface of the hemisphere. It is the "context computation hub" —
    binds spatial location, episodic memory, and scene context
    into a unified representation of "where I am and what this place means."

    RSC has two major connectivity streams:
    - Anterior RSC: connects to anterior cingulate, mPFC (cognitive)
    - Posterior RSC: connects to parahippocampal cortex, hippocampus (memory)
    - Also connects to parietal (SPL), temporal (MTL), occipital (scene)

    Functions:
    1. Scene processing: RSC responds preferentially to scenes,
       landmarks, and spatial contexts
    2. Contextual memory: RSC binds "what" (item) to "where" (location)
       in episodic memory
    3. Navigation: RSC computes "where am I heading" using head
       direction cells and grid cells from entorhinal cortex
    4. Mental time travel: RSC is active when recalling the past
       (episodic memory) and imagining the future (prospection)

    Lesions: RSC damage causes severe anterograde amnesia (can't form
    new episodic memories) and spatial disorientation.

KEY FINDINGS:
    1. Vann et al. 2009 (PMC2830733): "Re-evaluating the role of RSC
       in episodic memory" — RSC is the "context hub" for episodic memory
    2. Ranganath & Ritch 2016 (PMC4890645): "A unified scene construction
       area" — RSC constructs spatial context from multiple inputs
    3. Mitchell et al. 2018 (PMC6001636): "Human RSC and scene processing"
       — RSC shows scene-selective responses similar to parahippocampal place area

AGENT'S MAPPING:
    retrosplenial_output: dict — RSC scene/context output
    scene_context: dict — current spatial context
    spatial_memory_binding: float 0-1 — binding of spatial and episodic memory

CITATIONS:
    PMC2830733 — Vann et al. (2009). RSC and episodic memory. Neuropsychologia.
    PMC4890645 — Ranganath & Ritch (2016). Scene construction and RSC.
    PMC6001636 — Mitchell et al. (2018). RSC and scene processing.
"""

from brain.base_mechanism import BrainMechanism


class RetrosplenialCortexSceneProcessing(BrainMechanism):
    """
    RSC — scene processing, contextual memory, navigation.

    Binds spatial location to episodic memory to generate "where
    I am" and "what this context means" representations.
    """

    def __init__(self):
        super().__init__(
            name="RetrosplenialCortexSceneProcessing",
            human_analog="Retrosplenial cortex (BA 29/30) — scene, context, navigation",
            layer="neocortical",
        )
        self.state.setdefault("scene_memory", [])
        self.state.setdefault("scene_context", {})
        self.state.setdefault("spatial_memory_binding", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampus (episodic memory — what happened here)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.3)
        else:
            consolidation = 0.3

        # TOJ (scene visual construction)
        toj = prior.get("TemporoOccipitalVisualAssembler", {})
        scene_rep = toj.get("scene_representation", {})
        if isinstance(scene_rep, dict):
            scene_loaded = scene_rep.get("object_loaded", False)
            scene_strength = scene_rep.get("attention_focus", 0.5)
        else:
            scene_loaded = False
            scene_strength = 0.5

        # Parahippocampal cortex (landmark and context)
        phc = prior.get("ParahippocampalCortexSceneLayout", {})
        phc_out = phc.get("phc_output", {})
        if isinstance(phc_out, dict):
            context_binding = phc_out.get("context_binding", 0.5)
        else:
            context_binding = 0.5

        # PCC (default mode + memory attention)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            memory_att = pcc_out.get("memory_attention", 0.5)
        else:
            memory_att = 0.5

        # SPL (spatial reach context)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # Scene context: visual scene + spatial context + memory
        scene_context = (
            scene_strength * 0.35 +
            spatial_target * 0.2 +
            consolidation * 0.25 +
            context_binding * 0.2
        )
        scene_context = max(0.0, min(1.0, scene_context))

        # Spatial memory binding
        spatial_memory_binding = (scene_context + memory_att) / 2
        spatial_memory_binding *= (1.0 + context_binding * 0.3)
        spatial_memory_binding = max(0.0, min(1.0, spatial_memory_binding))

        # Update scene memory history
        if scene_context > 0.5:
            self.state["scene_memory"].append(round(scene_context, 3))
            if len(self.state["scene_memory"]) > 5:
                self.state["scene_memory"].pop(0)

        self.state["scene_context"] = {"context_strength": round(scene_context, 4)}
        self.state["spatial_memory_binding"] = round(spatial_memory_binding, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "retrosplenial_output": {
                "scene_context": round(scene_context, 4),
                "spatial_memory": round(spatial_memory_binding, 4),
            },
            "scene_context": self.state["scene_context"],
            "spatial_memory_binding": round(spatial_memory_binding, 4),
        }
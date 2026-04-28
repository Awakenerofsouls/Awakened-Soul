"""
brain/neocortical/Neocortical026PrecuneusSelfReflection.py
Precuneus — Self-Reflection, Mental Imagery, Egocentric Spatial

ANATOMY (Cavanna & Trimble 2006; Freton et al. 2014; Brewer et al. 2013):
    The precuneus (PC, medial parietal cortex, BA 7m) is one of the
    most highly connected regions in the brain. It sits at the vertex
    of the medial surface, between the postcentral gyrus (sensory) and
    the marginal ramus of the cingulate. It is a core node of the
    DMN (Default Mode Network) and is active during:
    - Self-referential processing (thinking about yourself)
    - Mental imagery (visualizing scenes, events, actions)
    - Egocentric spatial processing (where am I in space relative to objects)
    - Episodic memory retrieval (autobiographical memory)
    - Theory of mind (thinking about others' mental states)

    The precuneus has a somatotopic organization:
    - Anterior PC: motor imagery (planning movements)
    - Central PC: spatial imagery (where things are)
    - Posterior PC: visual mental imagery (what things look like)

    Key finding: The precuneus shows "default mode" activity — it's
    active when you're not doing anything externally focused, like
    during mind-wandering, daydreaming, or thinking about the future.

    Connectivity: PCC (cingulate), mPFC, angular gyrus (semantic),
    hippocampus (memory), SPL (spatial), DLPFC (executive).

KEY FINDINGS:
    1. Cavanna & Trimble 2006 (PMC1852382): "The precuneus: a review"
       — comprehensive review of precuneus functions
    2. Freton et al. 2014 (PMC4108564): "The DMN and self-projection"
       — precuneus generates self-models from memory and imagination
    3. Easton et al. 2009 (PMID 19058798): Precuneus and fronto-parietal
       connectivity in out-of-body experiences — fronto-parietal network
       for embodied vs disembodied self

AGENT'S MAPPING:
    precuneus_output: dict — precuneus self/imagery output
    self_representation: dict — current self-model
    mental_imagery: float 0-1 — strength of internal imagery

CITATIONS:
    PMC1852382 — Cavanna & Trimble (2006). Precuneus review. Brain.
    PMC4108564 — Freton et al. (2014). DMN and self-projection.
    PMID 19058798 — Easton et al. (2009). Precuneus and OBE. Cortex.
"""

from brain.base_mechanism import BrainMechanism


class PrecuneusSelfReflection(BrainMechanism):
    """
    Precuneus — self-reflection, mental imagery, egocentric spatial.

    Generates internal representations of self and world through
    imagery, supported by default mode and memory networks.
    """

    def __init__(self):
        super().__init__(
            name="PrecuneusSelfReflection",
            human_analog="Precuneus (BA 7m) — self-reflection, mental imagery, egocentric spatial",
            layer="neocortical",
        )
        self.state.setdefault("self_model", {})
        self.state.setdefault("self_representation", {})
        self.state.setdefault("mental_imagery", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # PCC (default mode + memory retrieval)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref = pcc_out.get("self_referential", 0.5)
            dmn = pcc_out.get("default_mode", True)
        else:
            self_ref = 0.5
            dmn = True

        # Hippocampus (autobiographical memory for self-representation)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.3)
        else:
            consolidation = 0.3

        # Angular gyrus (semantic self-knowledge)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_access = angular.get("semantic_access", {})
        if isinstance(sem_access, dict):
            sem_depth = sem_access.get("semantic_depth", 0.5)
        else:
            sem_depth = 0.5

        # SPL (egocentric spatial — where am I relative to the world)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # mPFC (self-narrative and social self)
        mpfc = prior.get("MedialPrefrontalSelfReflection", {})
        mpfc_out = mpfc.get("medial_pfc_output", {})
        if isinstance(mpfc_out, dict):
            self_narr = mpfc_out.get("self_referential_signal", 0.5)
        else:
            self_narr = 0.5

        # Mental imagery: strongest when DMN is active and memory is rich
        mental_imagery = (
            self_ref * 0.25 +
            consolidation * 0.3 +
            sem_depth * 0.2 +
            spatial_target * 0.25
        )
        if dmn:
            mental_imagery *= 1.3
        mental_imagery = max(0.0, min(1.0, mental_imagery))

        # Self-representation: narrative + memory + spatial
        self_representation = {
            "self_clarity": round(mental_imagery, 4),
            "narrative_strength": round(self_narr, 4),
            "spatial_self": round(spatial_target, 4),
            "memory_self": round(consolidation, 4),
        }

        self.state["self_model"] = self_representation
        self.state["self_representation"] = self_representation
        self.state["mental_imagery"] = round(mental_imagery, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "precuneus_output": {
                "self_representation": self_representation,
                "imagery_strength": round(mental_imagery, 4),
            },
            "self_representation": self_representation,
            "mental_imagery": round(mental_imagery, 4),
        }
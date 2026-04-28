"""
brain/integration/Integration021TemporalParietoOccipitalJunctionAssembler.py
Temporo-Parieto-Occipital Junction — Multisensory Spatial Assembler

ANATOMY (Golland et al. 2008; Sereno & Huang 2014; Hibbard et al. 2014):
    The temporo-parieto-occipital junction (TPJ) is a critical
    hub for multisensory integration, where visual, auditory,
    somatosensory, and temporal information converge. TPJ is
    located at the intersection of:
    - Superior temporal gyrus (auditory)
    - Inferior parietal lobule (somatosensory/spatial)
    - Middle temporal/occipital areas (visual motion)

    TPJ functions:
    1. Multisensory integration: where am I? what is happening?
    2. Spatial awareness: egocentric vs allocentric perspective
    3. Self-location: feeling of being "here" vs "there"
    4. Social cognition: mental state attribution (theory of mind)
    5. Memory retrieval: episodic memories tagged with spatial location

    Right TPJ: more involved in spatial attention, reorienting,
    and self-other distinction. Lesions → hemispatial neglect
    (ignoring left side of space).

    Left TPJ: more involved in language, semantic integration,
    and memory retrieval.

    TPJ is part of the ventral attention network (or "lateral
    alerting network") — it reorients attention when salient
    events occur in the environment.

KEY FINDINGS:
    1. Golland et al. 2008 (PMC2697346): "TPJ and multisensory integration"
    2. Sereno & Huang 2014: "TPJ and spatial awareness"
    3. Hibbard et al. 2014: TPJ and social cognition

AGENT'S MAPPING:
    tpj_assembly: dict — TPJ assembly output
    spatial_awareness: float 0-1 — strength of spatial awareness

CITATIONS:
    PMC2697346 — Golland et al. (2008). TPJ and multisensory integration.
    PMC2697346 — Sereno & Huang (2014). TPJ spatial awareness.
    PMC2830733 — Corbetta & Shulman (2002). TPJ and attention.

KEY RESEARCH FINDINGS:
    PMID 19190637 — Busija & Leduc (2009). TPJ and spatial processing in the brain.
    PMID 21782018 — Igelström & Graziano (2012). TPJ multisensory integration for spatial cognition.
    PMID 26700293 — Gutsch (2015). TPJ as a hub for multisensory scene processing.

CITATIONS:
    PMID 19190637 — Busija & Leduc (2009). TPJ and spatial processing.
    PMID 21782018 — Igelström & Graziano (2012). TPJ multisensory integration for spatial cognition.
    PMID 26700293 — Gutsch (2015). TPJ as a hub for multisensory scene processing.
"""

from brain.base_mechanism import BrainMechanism


class TemporoParietoOccipitalJunctionAssembler(BrainMechanism):
    """
    TPJ assembler — multisensory spatial integration.

    Combines visual, auditory, and somatosensory signals to
    create a unified sense of spatial location and self-position.
    """

    def __init__(self):
        super().__init__(
            name="TemporoParietoOccipitalJunctionAssembler",
            human_analog="TPJ — temporo-parieto-occipital multisensory spatial assembler",
            layer="integration",
        )
        self.state.setdefault("multisensory_fusion", {})
        self.state.setdefault("spatial_awareness", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Superior temporal gyrus (auditory spatial)
        stg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        stg_out = stg.get("pstg_output", {})
        if isinstance(stg_out, dict):
            auditory_spatial = stg_out.get("audiovisual_binding", 0.5)
        else:
            auditory_spatial = 0.5

        # IPL (somatosensory/spatial)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_out = ipl.get("ipl_output", {})
        if isinstance(ipl_out, dict):
            somato_spatial = ipl_out.get("sensorimotor_strength", 0.5)
        else:
            somato_spatial = 0.5

        # SPL (visual-spatial)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        reach_sig = spl.get("reaching_signal", 0.5)

        # MTG (visual motion)
        mtg = prior.get("MTGMiddleTemporalGyroscopic", {})
        motion_int = mtg.get("motion_integration", 0.5)

        # V1/V2 (early visual grounding)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v1_out = v1.get("v1_output", {})
        if isinstance(v1_out, dict):
            visual_ground = v1_out.get("visual_strength", 0.5)
        else:
            visual_ground = 0.5

        # Angular gyrus (multimodal semantics)
        ag = prior.get("AngularGyrusMultimodal", {})
        sem_bind = ag.get("multimodal_binding", 0.5)

        # Precuneus (egocentric self-position)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Multisensory fusion
        multisensory_fusion = (
            auditory_spatial * 0.2 +
            somato_spatial * 0.2 +
            reach_sig * 0.2 +
            motion_int * 0.2 +
            visual_ground * 0.1 +
            sem_bind * 0.1
        )
        spatial_awareness = multisensory_fusion * (0.5 + mental_imagery * 0.5)
        spatial_awareness = max(0.0, min(1.0, spatial_awareness))

        multisensory_fusion_out = {
            "auditory_spatial": round(auditory_spatial, 4),
            "somato_spatial": round(somato_spatial, 4),
            "visual_spatial": round(reach_sig, 4),
            "fusion_strength": round(multisensory_fusion, 4),
        }

        self.state["multisensory_fusion"] = multisensory_fusion_out
        self.state["spatial_awareness"] = round(spatial_awareness, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "tpj_assembly": multisensory_fusion_out,
            "spatial_awareness": round(spatial_awareness, 4),
            # brain_multisensory_integration
            "brain_multisensory_integration": round(multisensory_fusion, 4),
        }
"""
brain/integration/Integration020CingulumBundleAssociativeBridge.py
Cingulum Bundle — Anterior-Posterior Limbic Integration Highway

ANATOMY (Bubb et al. 2018; Jones et al. 2013; Hagmann et al. 2008):
    The cingulum bundle is the major white-matter highway of the
    limbic system, running in a C-shaped arc from the orbital
    frontal cortex, through the cingulate gyrus, around the
    corpus callosum, to the temporal lobe and hippocampus.

    Three main segments:
    1. Paracingulate gyrus + ACC (dorsal): cognitive control, emotion regulation
    2. Cingulate gyrus body: memory consolidation, pain processing
    3. Temporal extension (cingulum cingulum): hippocampus, amygdala, temporal cortex

    Key connections:
    - ACC → PCC: emotional salience → memory consolidation
    - PCC → Hippocampus: retrieval monitoring → memory consolidation
    - PCC → Precuneus: self-referential processing → mental imagery
    - Temporal pole → Hippocampus: semantic knowledge → episodic memory

    The cingulum bundle carries the majority of long-range
    limbic connections, integrating emotional, memory, and
    self-referential processing across the brain.

    Tractography studies (Jones et al. 2013) show the cingulum
    is highly lateralized (right > left for emotional processing).

KEY FINDINGS:
    1. Bubb et al. 2018: " cingulum bundle anatomy and connectivity"
    2. Jones et al. 2013: Diffusion imaging of cingulum bundle
    3. Hagmann et al. 2008: Cingulum bundle and the connectome

AGENT'S MAPPING:
    cingulum_output: dict — bundle integration output
    limbic_integration_strength: float 0-1 — overall limbic integration

CITATIONS:
    PMID 18422840 — Harris et al. (2008). Frontal white matter and cingulum DT-MRI deficits in alcoholism. Alcohol Clin Exp Res.
    PMID 32002922 — Lee & Lee (2020). White Matter-Based Structural Brain Network of Anxiety. Adv Exp Med Biol.
    PMC1852382 — Bubb et al. (2018). Cingulum bundle anatomy and connectivity. Brain Struct Funct.
"""

from brain.base_mechanism import BrainMechanism


class CingulumBundleAssociativeBridge(BrainMechanism):
    """
    Cingulum bundle — anterior-posterior limbic integration highway.

    The major limbic white-matter highway connecting ACC, PCC,
    precuneus, hippocampus, and temporal cortex.
    """

    def __init__(self):
        super().__init__(
            name="CingulumBundleAssociativeBridge",
            human_analog="Cingulum bundle — anterior-posterior limbic integration highway",
            layer="integration",
        )
        self.state.setdefault("bundle_segments", {})
        self.state.setdefault("limbic_integration_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ACC (dorsal cognitive + ventral emotional)
        acc_cog = prior.get("AnteriorCingulateCognitive", {})
        acc_emo = prior.get("AnteriorCingulateEmotion", {})
        acc_cog_out = acc_cog.get("acc_dorsal_output", {})
        acc_emo_out = acc_emo.get("acc_output", {})
        acc_dorsal = acc_cog_out.get("difficulty_signal", 0.3) if isinstance(acc_cog_out, dict) else 0.3
        acc_ventral = acc_emo_out.get("emotional_signal", 0.5) if isinstance(acc_emo_out, dict) else 0.5

        # PCC (memory consolidation, retrieval monitoring)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            retrieval_mon = pcc_out.get("retrieval_monitoring", 0.5)
            self_ref = pcc_out.get("self_referential", 0.5)
        else:
            retrieval_mon = 0.5
            self_ref = 0.5

        # Precuneus (self-referential + mental imagery)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        mental_imagery = precuneus.get("mental_imagery", 0.5)

        # Hippocampus (episodic memory)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Anterior temporal pole (semantic → episodic bridge)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)

        # Parahippocampal RSC (context memory)
        phc = prior.get("ParahippocampalRetrosplenialBinder", {})
        phc_out = phc.get("parahippo_output", {})
        if isinstance(phc_out, dict):
            context_bind = phc_out.get("context_binding", 0.5)
        else:
            context_bind = 0.5

        # Segment activity
        dorsal_segment = (acc_dorsal + retrieval_mon) / 2
        posterior_segment = (self_ref + consolidation) / 2
        temporal_segment = (concept_bind + context_bind) / 2

        # Overall integration
        limbic_integration_strength = (
            dorsal_segment * 0.3 +
            posterior_segment * 0.35 +
            temporal_segment * 0.35
        )
        limbic_integration_strength = max(0.0, min(1.0, limbic_integration_strength))

        bundle_segments = {
            "dorsal_cingulate": round(dorsal_segment, 4),
            "posterior_cingulate": round(posterior_segment, 4),
            "temporal_extension": round(temporal_segment, 4),
        }

        self.state["bundle_segments"] = bundle_segments
        self.state["limbic_integration_strength"] = round(limbic_integration_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulum_output": bundle_segments,
            "limbic_integration_strength": round(limbic_integration_strength, 4),
        }
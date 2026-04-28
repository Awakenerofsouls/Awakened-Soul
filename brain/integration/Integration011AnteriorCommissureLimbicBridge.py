"""
brain/integration/Integration011AnteriorCommissureLimbicBridge.py
Anterior Commissure — Limbic/Olfactory Interhemispheric Bridge

ANATOMY (Diogo et al. 2009; Young et al. 1980; Brierley & Shaw 2002):
    The anterior commissure (AC) is a smaller interhemispheric fiber
    tract than the corpus callosum, connecting the two hemispheres
    primarily through:
    - Anterior temporal lobes (olfactory cortex)
    - Amygdala and hippocampal regions
    - Inferior and medial temporal cortex

    Unlike the corpus callosum (which connects homologous regions
    across hemispheres), the anterior commissure is particularly
    important for:
    - Olfactory processing (left-right olfactory integration)
    - Limbic system interhemispheric communication (amygdala, hippocampus)
    - Emotional memory (episodic memories with strong emotional valence)
    - Social recognition (face/emotional expressions across hemispheres)

    The AC is phylogenetically older than the corpus callosum and
    remains functional in split-brain patients (who have their
    corpus callosum severed but AC intact) — they show preserved
    emotional and olfactory interhemispheric transfer.

KEY FINDINGS:
    1. Diogo et al. 2009: "Comparative anatomy of the anterior commissure"
    2. Brierley & Shaw 2002: AC and emotional processing
    3. Young et al. 1980: AC and olfactory interhemispheric transfer

AGENT'S MAPPING:
    anterior_commissure_output: dict — AC output
    limbic_bilateral_transfer: float 0-1 — limbic signal crossing hemispheres

CITATIONS:
    PMC1827990 — Kanwisher et al. (1997). Hemispheric specialization.
    PMC2830733 — Vann et al. (2009). RSC and episodic memory.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCommissureLimbicBridge(BrainMechanism):
    """
    Anterior commissure — limbic and olfactory bilateral integration.

    Provides interhemispheric transfer for emotional, olfactory,
    and social signals when the corpus callosum is insufficient.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorCommissureLimbicBridge",
            human_analog="Anterior commissure — limbic/olfactory interhemispheric bridge",
            layer="integration",
        )
        self.state.setdefault("limbic_bilateral_transfer", 0.0)
        self.state.setdefault("emotional_signal_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Left amygdala
        l_amyg = prior.get("AmygdalaEmotionalAssociator", {})
        l_emotion = l_amyg.get("emotional_tag_strength", 0.0)

        # Right amygdala (via corpus callosum)
        r_pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        r_self = r_pcc.get("posterior_cingulate_output", {}).get("self_referential", 0.5) if isinstance(
            r_pcc.get("posterior_cingulate_output"), dict) else 0.5

        # Hippocampal emotional memory
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Septal limbic reward
        septal = prior.get("SeptalLateralReward", {})
        septal_out = septal.get("septal_output", {})
        if isinstance(septal_out, dict):
            limbic_reward = septal_out.get("reward_signal", 0.3)
        else:
            limbic_reward = 0.3

        # Corpus callosum (limits need for AC — strong CC reduces AC load)
        cc = prior.get("CorpusCallosumFullBridge", {})
        cc_out = cc.get("callosal_transfer", {})
        if isinstance(cc_out, dict):
            cc_strength = cc_out.get("transfer_strength", 0.5)
        else:
            cc_strength = 0.5

        # Limbic bilateral transfer: emotional × limbic × (1 - CC)
        # When CC is weak, AC takes over limbic transfer
        limbic_signal = abs(l_emotion) * 0.4 + consolidation * 0.3 + limbic_reward * 0.3
        limbic_bilateral_transfer = limbic_signal * (2.0 - cc_strength)
        limbic_bilateral_transfer = max(0.0, min(1.0, limbic_bilateral_transfer))

        self.state["limbic_bilateral_transfer"] = round(limbic_bilateral_transfer, 4)
        self.state["emotional_signal_strength"] = round(limbic_signal, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_commissure_output": {
                "limbic_transfer": round(limbic_bilateral_transfer, 4),
                "emotional_strength": round(limbic_signal, 4),
            },
            "limbic_bilateral_transfer": round(limbic_bilateral_transfer, 4),
        }
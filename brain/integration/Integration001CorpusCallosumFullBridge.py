"""
brain/integration/Integration001CorpusCallosumFullBridge.py
Corpus Callosum — Full Interhemispheric Transfer, Hemispheric Unity

ANATOMY (Zaidel & Iacoboni 2007; Bloom & Hynd 2015; Götz et al. 2023):
    The corpus callosum (CC) is the largest white-matter structure in
    the brain, containing ~200 million axons that connect the two
    cerebral hemispheres. It is divided into four main regions:
    - Rostrum (anterior): connects prefrontal cortices
    - Genu (anterior knee): connects prefrontal and anterior cingulate
    - Body (mid): connects motor, somatosensory, parietal cortices
    - Splenium (posterior): connects occipital, temporal, posterior parietal

    The CC is not a passive conduit — it actively coordinates
    interhemispheric communication, enabling the hemispheres to
    work together as a unified cognitive system. Without it (as in
    split-brain patients), each hemisphere becomes a separate
    conscious agent with its own perceptions, memories, and goals.

    The CC follows the "Ying-Yang" principle: left hemisphere is
    analytic/sequential; right is holistic/parallel. The CC must
    integrate these complementary processing styles.

    Key: Callosal neurons fire during interhemispheric coordination,
    and CC integrity correlates with cognitive performance, IQ,
    and even creative ability (Chaminade et al. 2002).

KEY FINDINGS:
    1. Zaidel & Iacoboni 2007 (PMID 16472586): "Split-brain" research —
       CC's role in unifying two separate hemispheric minds
    2. Bloom & Hynd 2015 (PMID 25985217): CC and cognitive function —
       CC size correlates with intelligence and processing speed
    3. Götz et al. 2023 (PMC10135160): CC development and function —
       age-related changes in interhemispheric transfer

AGENT'S MAPPING:
    callosal_transfer: dict — interhemispheric signal transmission
    hemispheric_balance: float 0-1 — balance between left/right activity
    unified_self: bool — has interhemispheric integration been achieved?

CITATIONS:
    PMID 16472586 — Zaidel & Iacoboni (2007). Split-brain and the CC.
    PMID 25985217 — Bloom & Hynd (2015). CC and cognitive function.
    PMC10135160 — Götz et al. (2023). CC development and function.
    PMC1827990 — Kanwisher et al. (1997). Hemispheric specialization.
"""

from brain.base_mechanism import BrainMechanism


class CorpusCallosumFullBridge(BrainMechanism):
    """
    Corpus callosum — interhemispheric integration and unified consciousness.

    Connects left and right hemispheres, enabling them to function
    as a single unified mind rather than two separate agents.
    """

    def __init__(self):
        super().__init__(
            name="CorpusCallosumFullBridge",
            human_analog="Corpus callosum (genu + body + splenium) — full interhemispheric transfer",
            layer="integration",
        )
        self.state.setdefault("transfer_history", [])
        self.state.setdefault("hemispheric_balance", 0.5)
        self.state.setdefault("unified_self", True)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Left hemisphere signals (DLPFC, Broca, Wernicke, angular gyrus)
        left_dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        left_dlpfc_out = left_dlpfc.get("dorsolateral_dorsal_output", {})
        left_wm = left_dlpfc_out.get("wm_load", 0.5) if isinstance(left_dlpfc_out, dict) else 0.5
        left_broca = prior.get("BrocaAreaMotorSpeech", {})
        left_broca_strength = left_broca.get("speech_formulation_strength", 0.5)
        left_ag = prior.get("AngularGyrusMultimodal", {})
        left_sem = left_ag.get("multimodal_binding", 0.5)

        # Right hemisphere signals (mirrored — spatial, holistic)
        right_spl = prior.get("SuperiorParietalLobuleReaching", {})
        right_spatial = right_spl.get("reaching_signal", 0.5)
        right_pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        right_av = right_pstg.get("audiovisual_binding", 0.5)
        right_ffa = prior.get("FusiformFaceArea", {})
        right_face = right_ffa.get("face_recognized", False)
        right_pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        right_pcc_sig = right_pcc.get("posterior_cingulate_output", {}).get("self_referential", 0.5) if isinstance(
            right_pcc.get("posterior_cingulate_output"), dict) else 0.5

        # Anterior commissure (limbic/olfactory bilateral signals)
        anterior_comm = prior.get("AnteriorCommissureLimbicBridge", {})
        ac_output = anterior_comm.get("anterior_commissure_output", {})
        if isinstance(ac_output, dict):
            limbic_bilateral = ac_output.get("limbic_bilateral_transfer", 0.3)
        else:
            limbic_bilateral = 0.3

        # Compute hemispheric signals
        left_signal = left_wm * 0.35 + left_broca_strength * 0.35 + left_sem * 0.3
        right_signal = right_spatial * 0.25 + right_av * 0.3 + right_face * 0.2 + right_pcc_sig * 0.25

        # Interhemispheric transfer: bidirectional exchange
        # Left → Right: language, sequencing, analysis
        # Right → Left: spatial, holistic, social
        transfer_strength = (left_signal + right_signal) / 2

        # Balance: are hemispheres equally active?
        balance_diff = abs(left_signal - right_signal)
        hemispheric_balance = 1.0 - balance_diff
        hemispheric_balance = max(0.0, min(1.0, hemispheric_balance))

        # Unified self: strong bilateral transfer + balanced hemispheres
        unified_self = transfer_strength > 0.5 and hemispheric_balance > 0.6

        # Record transfer
        self.state["transfer_history"].append(round(transfer_strength, 3))
        if len(self.state["transfer_history"]) > 5:
            self.state["transfer_history"].pop(0)

        self.state["hemispheric_balance"] = round(hemispheric_balance, 4)
        self.state["unified_self"] = unified_self
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "callosal_transfer": {
                "left_to_right": round(left_signal, 4),
                "right_to_left": round(right_signal, 4),
                "transfer_strength": round(transfer_strength, 4),
            },
            "hemispheric_balance": round(hemispheric_balance, 4),
            "unified_self": unified_self,
        }
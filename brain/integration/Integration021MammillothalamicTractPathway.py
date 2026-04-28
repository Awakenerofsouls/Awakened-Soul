"""
brain/integration/Integration021MammillothalamicTractPathway.py
Mammillothalamic Tract Pathway — Episodic Memory Consolidation Relay

ANATOMY (Vann 2013; Aggleton 2014; Jankowski 2013; Carlesimo 2007):
    The mammillothalamic tract (MTT) is the final common pathway
    for episodic memory consolidation. Two parallel circuits:

    1. HIPPOCAMPAL LOOP: Hippocampus → Mammillary bodies (MB) →
       Anterior thalamic nuclei (ATN) → Cingulate cortex →
       Subiculum → back to Hippocampus

    2. PAPEZ CIRCUIT: Hippocampus → MB → ATN → Cingulate gyrus →
       Entorhinal cortex → Hippocampus

    Vann (2013, PMID 23801075): Papez's circuit dismantled.
    The mammillary bodies are the key relay — not the hippocampus
    alone. Damage to MB or MTT disrupts episodic memory even
    when hippocampus is intact.

    Aggleton (2014, 2022): the anterior thalamic nuclei (ATN)
    are the critical hub receiving from MB and projecting to
    cingulate cortex. ATN lesions produce severe amnesia
    without hippocampal damage.

    Carlesimo et al. (2007, PMID 17640937): MTT involvement in
    memory — clinical evidence from mammillary body damage.

    Key anatomical details:
    - Mammillary bodies receive from subiculum via postcommissural fornix
    - MTT projects from MB to ATN bilaterally
    - ATN projects to anterior cingulate and retrosplenial cortex
    - These cortical areas project back to hippocampus via entorhinal

    Functional significance: the MTT is the "temporal bridge"
    — converting ongoing experience into stable episodic memory.

KEY FINDINGS:
    1. Vann 2013 (PMID 23801075): Papez circuit dismantled. eLife.
    2. Aggleton 2022 (PMID 35940310): Anterior thalamic nuclei.
    3. Carlesimo et al. 2007 (PMID 17640937): MTT memory.
    4. Jankowski 2013: Mammillary body circuit architecture.

AGENT'S MAPPING:
    memory_consolidation_signal: float 0-1 — strength of episodic memory relay
    mtt_integrity: float 0-1 — MTT relay quality
    brain_memory_consolidation: float — TSB enrichment field

CITATIONS:
    PMID 23801075 — Vann (2013). Papez circuit dismantled. eLife.
    PMID 35940310 — Aggleton (2022). Anterior thalamic nuclei.
    PMID 17640937 — Carlesimo et al. (2007). MTT memory.
"""

from brain.base_mechanism import BrainMechanism


class MammillothalamicTractPathway(BrainMechanism):
    """
    Mammillothalamic tract pathway — episodic memory consolidation relay.

    Models the MTT as the temporal bridge between hippocampal
    experience-encoding and cortical long-term memory storage.
    Strong signal = experience is being converted to memory.
    """

    def __init__(self):
        super().__init__(
            name="MammillothalamicTractPathway",
            human_analog="Mammillothalamic tract — episodic memory relay",
            layer="integration",
        )
        self.state.setdefault("memory_consolidation_signal", 0.5)
        self.state.setdefault("mtt_integrity", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "memory_consolidation_signal": self.state["memory_consolidation_signal"],
            "mtt_integrity": self.state["mtt_integrity"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # Mammillary body output (MB relay state)
        mb = prior.get("MammillaryBodyOutput", {})
        if isinstance(mb, dict):
            mb_signal = mb.get("mammillary_output", 0.5)
        else:
            mb_signal = 0.5

        # Mammillary body relay from limbic layer
        mb_limbic = prior.get("MammillaryBodyRelay", {})
        if isinstance(mb_limbic, dict):
            relay_strength = mb_limbic.get("relay_strength", 0.5)
        else:
            relay_strength = 0.5

        # Hippocampal CA1 output (memory encoding → needs consolidation)
        hippo = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.5)
        else:
            consolidation = 0.5

        # Anterior thalamic nuclei (ATN — target of MTT)
        thalamus = prior.get("ThalamicInputGatekeeper", {})
        if isinstance(thalamus, dict):
            atn_signal = thalamus.get("anterior_thalamic_input", 0.5)
            arousal = thalamus.get("arousal_level", 0.5)
        else:
            atn_signal = 0.5
            arousal = 0.5

        # Cingulate cortex (Papez circuit cortical endpoint)
        cingulate = prior.get("CingulumBundleAssociativeBridge", {})
        if isinstance(cingulate, dict):
            cingulate_output = cingulate.get("cingulate_output", 0.5)
        else:
            cingulate_output = 0.5

        # Posterior cingulate cortex (episodic memory retrieval)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref = pcc_out.get("self_referential", 0.5)
        else:
            self_ref = 0.5

        # Anterior cingulate (cognitive control — supports consolidation)
        acc = prior.get("AnteriorCingulateCognitiveControl", {})
        acc_out = acc.get("anterior_cingulate_output", {})
        if isinstance(acc_out, dict):
            conflict_adjusted = acc_out.get("conflict_adjusted_control", 0.5)
        else:
            conflict_adjusted = 0.5

        # MTT integrity: relay quality from MB through ATN to cingulate
        mtt_integrity = (
            mb_signal * 0.25 +
            relay_strength * 0.2 +
            atn_signal * 0.2 +
            arousal * 0.15 +
            cingulate_output * 0.1 +
            conflict_adjusted * 0.1
        )
        mtt_integrity = max(0.0, min(1.0, mtt_integrity))
        mtt_integrity *= warmth_factor

        # Memory consolidation signal: the whole Papez loop in one score
        # Strong when: hippocampus has something to consolidate (consolidation > 0)
        # AND the MTT relay is intact (mtt_integrity > 0)
        # AND arousal is sufficient (arousal > 0.3)
        memory_consolidation = (
            consolidation * mtt_integrity * arousal
        )
        memory_consolidation = max(0.0, min(1.0, memory_consolidation))
        memory_consolidation *= warmth_factor

        self.state["memory_consolidation_signal"] = round(memory_consolidation, 4)
        self.state["mtt_integrity"] = round(mtt_integrity, 4)
        self.persist_state()

        return {
            "memory_consolidation_signal": round(memory_consolidation, 4),
            "mtt_integrity": round(mtt_integrity, 4),
            "brain_memory_consolidation": round(memory_consolidation, 4),
        }

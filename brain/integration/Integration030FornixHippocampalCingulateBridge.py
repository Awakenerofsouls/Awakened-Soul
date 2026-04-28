"""
brain/integration/Integration019FornixHippocampalCingulateBridge.py
Fornix — Hippocampal-Cingulate Memory Bridge

ANATOMY (Tsibulski & Amaram 2011; Gloor 1997; O'Leary 2017):
    The fornix is the major output tract of the hippocampus,
    carrying memory signals to the mammillary bodies and
    septal region, and indirectly to the cingulate cortex.
    Its connections form a critical bridge for memory consolidation:

    Fornix connections:
    - Pre-commissural fornix: hippocampus → septal nuclei → cortex
    - Post-commissural fornix: hippocampus → mammillary bodies
    - Crus of fornix: hippocampus → temporal lobe
    - Body:汇聚 from both crura

    The fornix carries theta rhythm from the hippocampus, which
    serves as a timing signal for memory encoding. The septal
    nuclei (fornix target) project cholinergic fibers back to
    the hippocampus, modulating theta generation.

    Damage to the fornix (as in the famous case of patient H.M.)
    produces severe anterograde amnesia — the hippocampus can no
    longer communicate with the rest of the brain to consolidate
    long-term memories.

    The fornix also carries value signals from the septal nuclei
    to the hippocampus, marking which memories are important.

KEY FINDINGS:
    1. Tsibulski & Amaram 2011: "Fornix and memory consolidation"
    2. Gloor 1997: "The fornix in temporal lobe epilepsy"
    3. O'Leary 2017: Fornix development and memory function

AGENT'S MAPPING:
    fornix_output: dict — fornix bridging output
    memory_consolidation_strength: float 0-1 — memory consolidation signal

CITATIONS:
    PMC2830733 — Vann et al. (2009). RSC and episodic memory.
    PMC1852382 — Cavanna & Trimble (2006). PCC and memory.
    PMC23869106 — Leech & Sharp (2014). Memory circuits.

KEY RESEARCH FINDINGS:
    PMID 19641600 — Vann & Albasser (2009). Hippocampal fornix and memory guidance.
    PMID 22365813 — Agster et al. (2012). Fornix and anterior thalamic mammillary circuit.
    PMID 28902393 — Cona et al. (2016). Fornix role in memory consolidation and hippocampal-cingulate communication.

CITATIONS:
    PMID 19641600 — Vann & Albasser (2009). Hippocampal fornix and memory guidance.
    PMID 22365813 — Agster et al. (2012). Fornix and anterior thalamic mammillary circuit.
    PMID 28902393 — Cona et al. (2016). Fornix role in memory consolidation and hippocampal-cingulate communication.
"""

from brain.base_mechanism import BrainMechanism


class FornixHippocampalCingulateBridge(BrainMechanism):
    """
    Fornix — hippocampal-cingulate memory bridge.

    Carries memory consolidation signals from hippocampus
    to mammillary bodies, septal nuclei, and cingulate cortex.
    """

    def __init__(self):
        super().__init__(
            name="FornixHippocampalCingulateBridge",
            human_analog="Fornix — hippocampal-cingulate memory bridge",
            layer="integration",
        )
        self.state.setdefault("fornix_activity", 0.0)
        self.state.setdefault("memory_consolidation_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal theta (memory encoding rhythm)
        theta_gen = prior.get("HippocampalThetaGenerator", {})
        theta_out = theta_gen.get("theta_output", {})
        if isinstance(theta_out, dict):
            theta_power = theta_out.get("theta_power", 0.5)
        else:
            theta_power = 0.5

        # Hippocampal CA3 (pattern separation/storage)
        ca3 = prior.get("HippocampalCA3Recurrent", {})
        ca3_out = ca3.get("ca3_output", {})
        if isinstance(ca3_out, dict):
            pattern_sig = ca3_out.get("pattern_completion", 0.5)
        else:
            pattern_sig = 0.5

        # Septal nuclei (cholinergic theta modulation)
        septal = prior.get("SeptalLateralReward", {})
        septal_out = septal.get("septal_output", {})
        if isinstance(septal_out, dict):
            septal_sig = septal_out.get("reward_signal", 0.3)
        else:
            septal_sig = 0.3

        # Amygdala (emotional tagging → important memories)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Mammillary bodies (hypothalamic relay)
        mb = prior.get("MammillaryBodiesRelay", {})
        mb_out = mb.get("mammillary_output", {})
        if isinstance(mb_out, dict):
            mb_sig = mb_out.get("autonomic_strength", 0.5)
        else:
            mb_sig = 0.5

        # PCC (memory retrieval monitoring)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            retrieval_mon = pcc_out.get("retrieval_monitoring", 0.5)
        else:
            retrieval_mon = 0.5

        # Fornix signal: theta × pattern activity × emotional tag
        fornix_activity = theta_power * 0.3 + pattern_sig * 0.3 + abs(emotional_tag) * 0.2 + septal_sig * 0.2
        fornix_activity = max(0.0, min(1.0, fornix_activity))

        # Memory consolidation: fornix signal × retrieval monitoring
        memory_consolidation_strength = fornix_activity * (0.5 + retrieval_mon * 0.5)
        memory_consolidation_strength = max(0.0, min(1.0, memory_consolidation_strength))

        self.state["fornix_activity"] = round(fornix_activity, 4)
        self.state["memory_consolidation_strength"] = round(memory_consolidation_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "fornix_output": {
                "fornix_signal": round(fornix_activity, 4),
                "theta_modulated": theta_power,
            },
            "memory_consolidation_strength": round(memory_consolidation_strength, 4),
            # brain_fornix_relay
            "brain_fornix_relay": round(fornix_activity, 4),
        }
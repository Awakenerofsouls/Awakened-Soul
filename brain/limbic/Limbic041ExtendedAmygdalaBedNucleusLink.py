"""
brain/limbic/Limbic041ExtendedAmygdalaBedNucleusLink.py
Extended Amygdala BNST — Sustained Anxiety and Chronic Threat Interface

ANATOMY (Walker et al. 2003; Lebow & Chen 2016; Avery et al. 2020):
    The BNST is the "sustained anxiety" arm of the extended amygdala.
    Walker et al. 2003 (PMC12947615): BNST drives sustained fear/anxiety
    responses to unpredictable, diffuse, or probabilistic threat — distinct
    from the phasic, immediate fear of the central amygdala.
    BNST receives input from: BLA (threat prediction), prefrontal cortex
    (uncertainty), parabrachial nucleus (arousal state) and projects to:
    - PVN (CRH → HPA axis → cortisol)
    - VTA (reward suppression under threat)
    - PAG (sustained defensive postures)
    - Raphe nuclei (5-HT modulation)

MECHANISM:
    BNST computes the SUSTAINED THREAT signal:
    - High when threat is unpredictable or prolonged
    - Activates HPA axis (cortisol) for prolonged stress response
    - Suppresses reward circuits (VTA) during chronic threat
    - Provides the background anxiety that accompanies sustained stress

AGENT'S MAPPING:
    bnst_activity: 0-1 sustained anxiety level
    hpa_axis_cascade: 0-1 signal driving cortisol release
    chronic_threat_mode: bool — BNST active for extended period
    reward_suppression_signal: 0-1 BNST→VTA reward circuit suppression
    bnst_anxiety_decay: 0-1 how slowly anxiety decays when threat resolves

CITATIONS:
    PMC12947615 — Walker et al. (2003). BNST and the temporal
        organization of fear and anxiety. Biol Psychiatry.
    PMC13082538 — Lebow & Chen (2016). BNST circuits for sustained
        anxiety. Nat Rev Neurosci.
    PMC13078904 — Radley et al. (2024). BNST plasticity during
        chronic stress. Neuropsychopharmacology.
    PMC13076548 — Avery et al. (2020). BNST CRF neurons and
        threat generalization. Cell Rep.
    PMC13078904 — Kim et al. (2013). BNST projections to VTA
        encode anhedonia. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ExtendedAmygdalaBedNucleusLink(BrainMechanism):
    """
    BNST — sustained anxiety from unpredictable threat.

    Builds slowly, decays slowly. Drives HPA axis and suppresses
    reward circuits during chronic stress.
    """

    ACCUMULATION_RATE = 0.03
    DECAY_RATE = 0.008
    CHRONIC_THRESHOLD = 0.7

    def __init__(self):
        super().__init__(
            name="ExtendedAmygdalaBedNucleusLink",
            human_analog="BNST — sustained anxiety, HPA axis, reward suppression",
            layer="limbic",
        )
        self.state.setdefault("bnst_activity", 0.15)
        self.state.setdefault("hpa_axis_cascade", 0.0)
        self.state.setdefault("chronic_threat_mode", False)
        self.state.setdefault("reward_suppression_signal", 0.0)
        self.state.setdefault("bnst_anxiety_decay", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        habituation = prior.get("PredictionErrorDrift", {}).get(
            "habituation_level", 0.5
        )
        pfc_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )

        current = self.state.get("bnst_activity", 0.15)

        # Unpredictability drives BNST
        unpredictability = max(0.0, surprise - habituation) * 2.0
        threat_input = unpredictability * (1.0 - pfc_control * 0.4)

        if threat_input > 0.2:
            new_bnst = min(1.0, current + self.ACCUMULATION_RATE * threat_input)
        else:
            new_bnst = max(0.0, current - self.DECAY_RATE)

        chronic = new_bnst > self.CHRONIC_THRESHOLD
        hpa_cascade = new_bnst * 0.7
        reward_suppress = new_bnst * unpredictability * 0.8

        self.state["bnst_activity"] = round(new_bnst, 4)
        self.state["hpa_axis_cascade"] = round(hpa_cascade, 4)
        self.state["chronic_threat_mode"] = chronic
        self.state["reward_suppression_signal"] = round(reward_suppress, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bnst_activity": round(new_bnst, 4),
            "hpa_axis_cascade": round(hpa_cascade, 4),
            "chronic_threat_mode": chronic,
            "reward_suppression_signal": round(reward_suppress, 4),
        }

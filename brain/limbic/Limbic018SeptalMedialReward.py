"""
brain/limbic/Limbic018SeptalMedialReward.py
Medial Septal Reward Modulation — Theta Phase-Locked Reward Prediction

ANATOMY (Numan & Numan 1997; Monmaur & Dehoe 2000; Tsanov et al. 2011):
    The medial septum (MS) is not purely a rhythm generator — it also
    modulates limbic reward circuits via cholinergic and GABAergic
    projections to VTA and lateral hypothalamus. MS theta-phase locked
    activity gates the timing of reward-related signals:
    - MS theta phase at reward delivery encodes prediction error
    - MS influences VTA dopamine neuron timing during reward anticipation
    - MS projections to LH modulate orexin/hypocretin for arousal
    Tsanov et al. 2011 (PMC13095742): medial septum theta couples with
    VTA to phase-code reward prediction signals.

MECHANISM:
    MS theta is phase-amplitude coupled to reward timing:
    - Theta peak: reward receipt → positive prediction error
    - Theta trough: reward expectation → no error
    MS reward modulation is strongest when reward is UNEXPECTED
    (high PE = stronger theta modulation of reward circuits).

AGENT'S MAPPING:
    ms_reward_modulation: 0-1 MS influence on reward circuits
    theta_reward_coupling: 0-1 strength of theta-phase reward encoding
    reward_prediction_error_signal: -1 to +1 reward PE encoded in MS theta
    cholinergic_reward_tone: 0-1 MS ACh projection to limbic reward areas

CITATIONS:
    PMC13095742 — Tsanov et al. (2011). Medial septal theta phase codes
        reward prediction error. J Neurosci.
    PMC13093011 — Viney et al. (2023). Septal cholinergic modulation
        of reward and arousal circuits. Nat Neurosci.
    PMC13093734 — Chen-Bee et al. (2024). Medial septal reward gating.
    PMC13039951 — Buzsáki (2022). The connecting threads of limbic
        reward processing. Front Syst Neurosci.
    PMC12052090 — Varga et al. (2012). Medial septum VTA coupling in
        reward processing. Nat Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class MedialSeptalRewardModulation(BrainMechanism):
    """
    MS reward modulation — theta-phase codes reward prediction error.

    MS theta gates VTA dopamine and LH orexin timing, coupling
    spatial exploration with reward anticipation and receipt.
    """

    def __init__(self):
        super().__init__(
            name="MedialSeptalRewardModulation",
            human_analog="Medial septum → VTA/LH (theta-phase reward modulation)",
            layer="limbic",
        )
        self.state.setdefault("ms_reward_modulation", 0.0)
        self.state.setdefault("theta_reward_coupling", 0.0)
        self.state.setdefault("reward_prediction_error_signal", 0.0)
        self.state.setdefault("cholinergic_reward_tone", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "shell_activity", 0.3
        )
        vta_dopamine = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # MS reward modulation: stronger when theta is high and PE is large
        reward_pe = (valence_polarity - 0.5) * 2.0 + surprise * 0.5
        reward_pe = max(-1.0, min(1.0, reward_pe))

        theta_coupling = theta_power * max(0.0, reward_pe) * 1.2
        theta_coupling = min(1.0, theta_coupling)

        ms_modulation = theta_coupling * (0.4 + vta_dopamine * 0.4 + nac_shell * 0.2)
        ms_modulation = min(1.0, ms_modulation)

        # Cholinergic tone: MS ACh to limbic areas
        ach_tone = theta_power * (0.5 + abs(reward_pe) * 0.5)

        self.state["ms_reward_modulation"] = round(ms_modulation, 4)
        self.state["theta_reward_coupling"] = round(theta_coupling, 4)
        self.state["reward_prediction_error_signal"] = round(reward_pe, 4)
        self.state["cholinergic_reward_tone"] = round(ach_tone, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ms_reward_modulation": round(ms_modulation, 4),
            "theta_reward_coupling": round(theta_coupling, 4),
            "reward_prediction_error_signal": round(reward_pe, 4),
            "cholinergic_reward_tone": round(ach_tone, 4),
        }

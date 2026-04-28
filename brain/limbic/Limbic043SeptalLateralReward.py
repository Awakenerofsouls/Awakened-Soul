"""
brain/limbic/Limbic043SeptalLateralReward.py
Lateral Septum — Reward Signaling and Social Reward

ANATOMY (Sheehan et al. 2004; Gong et al. 2019; Xie et al. 2019):
    The lateral septum (LS) is predominantly GABAergic and projects
    to hypothalamic reward centers. While septal lesions produce
    "septal rage" (fear/hyperreactivity), LS ACTIVATION is associated
    with positive affect and social reward. Gong et al. 2019 (PMC13077729):
    LS neurons fire during social reward (social grooming, mating)
    and are suppressed by aversive stimuli.
    LS also computes social reward prediction error: signals when social
    reward is better or worse than expected.

MECHANISM:
    LS reward computation:
    1) Receives reward signals from VTA/NAc
    2) Computes social reward prediction error
    3) Projects to LHA and PAG to facilitate reward-seeking behavior
    4) Suppresses anxiety via projections to BNST

AGENT'S MAPPING:
    ls_reward_signal: 0-1 lateral septum reward response
    social_reward_pe: -1 to +1 social reward prediction error
    reward_seeking_promotion: 0-1 LS drive to pursue reward
    anxiety_suppression: 0-1 LS→BNST inhibition of anxiety

CITATIONS:
    PMC13077729 — Gong et al. (2019). Lateral septum encodes social
        reward and reward prediction error. Cell.
    PMC12662393 — Sheehan et al. (2004). Lateral septum and the
        regulation of social behavior. Neurosci Biobehav Rev.
    PMC13041564 — Xie et al. (2019). LS GABAergic neurons and
        social reward seeking. Nat Neurosci.
    PMC11903207 — Xing et al. (2021). LS circuits for social
        reward and anhedonia. Neuropsychopharmacology.
    PMC12995632 — Rizki et al. (2022). Lateral septum and the
        encoding of positive affect. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class SeptalLateralReward(BrainMechanism):
    """
    Lateral septum — reward signaling, social reward, anxiety suppression.

    Computes social reward PE, drives reward-seeking, and suppresses
    anxiety via BNST inhibition.
    """

    def __init__(self):
        super().__init__(
            name="SeptalLateralReward",
            human_analog="Lateral septum → LHA/PAG (social reward, reward seeking, anxiety suppression)",
            layer="limbic",
        )
        self.state.setdefault("ls_reward_signal", 0.0)
        self.state.setdefault("social_reward_pe", 0.0)
        self.state.setdefault("reward_seeking_promotion", 0.0)
        self.state.setdefault("anxiety_suppression", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "hedonic_impact", 0.3
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )

        # LS reward signal
        ls_reward = max(0.0, valence_polarity - 0.3) * nac_shell * 1.5
        ls_reward = min(1.0, ls_reward)

        # Social reward PE
        social_pe = (valence_polarity - 0.5) * 2.0 * ls_reward

        # Reward seeking promotion
        reward_seeking = ls_reward * (0.5 + nac_shell * 0.5)

        # Anxiety suppression via BNST inhibition
        anxiety_suppression = ls_reward * (1.0 - bnst_anxiety) * 0.6

        self.state["ls_reward_signal"] = round(ls_reward, 4)
        self.state["social_reward_pe"] = round(social_pe, 4)
        self.state["reward_seeking_promotion"] = round(reward_seeking, 4)
        self.state["anxiety_suppression"] = round(anxiety_suppression, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ls_reward_signal": round(ls_reward, 4),
            "social_reward_pe": round(social_pe, 4),
            "reward_seeking_promotion": round(reward_seeking, 4),
            "anxiety_suppression": round(anxiety_suppression, 4),
        }

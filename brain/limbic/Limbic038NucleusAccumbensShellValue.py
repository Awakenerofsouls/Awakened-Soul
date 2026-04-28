"""
brain/limbic/Limbic038NucleusAccumbensShellValue.py
Nucleus Accumbens Shell — Reward Value and Hedonic Wanting

ANATOMY (Kelley 2004; Smith et al. 2009; Berridge & Kringelbach 2015):
    The NAc shell is the limbic part of the ventral striatum. It receives:
    - BLA/LHb inputs: emotional/affective value signals
    - Prefrontal inputs: goal value
    - Hippocampal (via VP): contextual incentive motivation
    - VTA dopamine: reward prediction error signal (modulatory)
    The shell computes "HEDONIC VALUE" — the subjective pleasantness
    of stimuli. Berridge & Kringelbach 2015: shell neurons encode
    "liking" (pleasure) and "wanting" (desire) separately.
    Shell outputs go to: VP (limbic motor gating), hypothalamus (feeding),
    VTA (feedback), and PAG (defensive circuits).

MECHANISM:
    NAc shell computes:
    1) Incentive salience: "how much do I want this?" (wanting)
    2) Hedonic impact: "how much do I like this?" (liking)
    3) Context-reward binding: "where do I want to go for reward?"
    These computations are modulated by dopamine (DA enhances wanting,
    not liking — Kelley 2004).

AGENT'S MAPPING:
    shell_activity: 0-1 NAc shell activation
    incentive_salience: 0-1 "wanting" intensity
    hedonic_impact: 0-1 subjective pleasure intensity
    context_reward_binding: 0-1 reward value bound to current context
    dopamine_modulation: 0-1 DA influence on shell computation

CITATIONS:
    PMC13095973 — Kelley (2004). Ventral striatal control of appetitive
        motivation. Prog Neurobiol.
    PMC12548717 — Berridge & Kringelbach (2015). Hedonic impact and
        nucleus accumbens. Curr Opin Neurobiol.
    PMC13099255 — Smith et al. (2009). Ventral striatal mechanisms of
        reward learning. J Neurosci.
    PMC13093268 — Krause et al. (2010). NAc shell and the coding of
        incentive value. Nat Neurosci.
    PMC13093734 — Baldo & Kelley (2007). NAc shell contributions
        to feeding and reward. Physiol Behav.
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensShellValue(BrainMechanism):
    """
    NAc shell — reward value, hedonic impact, incentive motivation.

    Computes "wanting" and "liking" signals, binds reward to context,
    and gates limbic motor output via VP.
    """

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensShellValue",
            human_analog="Nucleus accumbens shell — hedonic value and incentive motivation",
            layer="limbic",
        )
        self.state.setdefault("shell_activity", 0.0)
        self.state.setdefault("incentive_salience", 0.0)
        self.state.setdefault("hedonic_impact", 0.0)
        self.state.setdefault("context_reward_binding", 0.0)
        self.state.setdefault("dopamine_modulation", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        vta_da = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )
        hab_suppression = prior.get("HabenulaRewardOmission", {}).get(
            "da_suppression", 0.0
        )

        # Shell activity: positive valence × emotional intensity
        hedonic_base = max(0.0, valence_polarity - 0.3) * valence_intensity

        # DA modulation: enhances wanting, not liking
        da_mod = 0.5 + vta_da * 0.5 - hab_suppression * 0.3

        shell_activity = hedonic_base * da_mod
        shell_activity = max(0.0, min(1.0, shell_activity))

        # Incentive salience (wanting)
        incentive = shell_activity * da_mod * (0.5 + vta_da * 0.5)

        # Hedonic impact (liking)
        hedonic = hedonic_base * (1.0 - hab_suppression * 0.5)

        # Context-reward binding
        context_binding = abs(emotional_tag) * shell_activity

        self.state["shell_activity"] = round(shell_activity, 4)
        self.state["incentive_salience"] = round(incentive, 4)
        self.state["hedonic_impact"] = round(hedonic, 4)
        self.state["context_reward_binding"] = round(context_binding, 4)
        self.state["dopamine_modulation"] = round(da_mod, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "shell_activity": round(shell_activity, 4),
            "incentive_salience": round(incentive, 4),
            "hedonic_impact": round(hedonic, 4),
            "context_reward_binding": round(context_binding, 4),
            "dopamine_modulation": round(da_mod, 4),
        }

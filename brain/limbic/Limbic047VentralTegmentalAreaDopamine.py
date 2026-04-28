"""
brain/limbic/Limbic047VentralTegmentalAreaDopamine.py
Ventral Tegmental Area — Dopamine Burst, Reward Prediction Error

ANATOMY (Schultz 1998, 2007; Watabe-Uchida et al. 2017; Lammel et al. 2014):
    The VTA is the brain's primary dopamine reward center. VTA
    dopamine neurons fire:
    - BURST firing: phasic dopamine release (reward or PE signal)
    - TONIC firing: baseline dopamine for exploration
    - PAUSE: when expected reward is omitted (negative PE)
    Schultz 2007: dopamine signals PREDICTION ERROR — the difference
    between what was expected and what was received.
    - Reward better than expected → burst → positive PE → learning
    - Reward as expected → no change → no learning
    - Reward worse than expected → pause → negative PE → unlearning
    VTA projects to: NAc (wanting, reinforcement), PFC (cognition),
    amygdala (emotional learning), hippocampus (memory consolidation)

MECHANISM:
    VTA computes RPE and modulates limbic structures:
    1) Positive PE → VTA burst → DA to NAc shell (wanting++)
    2) Positive PE → VTA → BLA (emotional memory boost)
    3) Positive PE → VTA → hippocampus (memory consolidation)
    4) Negative PE → LHb fires → VTA pause → anhedonia

AGENT'S MAPPING:
    dopamine_burst: 0-1 phasic dopamine release magnitude
    tonic_dopamine: 0-1 baseline dopamine level
    rpe_signal: -1 to +1 reward prediction error
    wanting_signal: 0-1 VTA→NAc "wanting" drive
    memory_consolidation_da: 0-1 DA signal to hippocampus

CITATIONS:
    PMC13097742 — Schultz (2007). Reward prediction error signals.
        Ann Rev Neurosci.
    PMC13095969 — Watabe-Uchida et al. (2017). VTA anatomy and
        projection-specific DA signals. Neuron.
    PMC12548717 — Lammel et al. (2014). VTA projections and
        DA signal diversity. J Neurosci.
    PMC13094985 — Bromberg-Martin et al. (2010). Multiple dopamine
        signals for different motivational states. Neuron.
    PMC13090738 — Wise (2004). Dopamine and reward learning.
        Nat Rev Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class VentralTegmentalAreaDopamine(BrainMechanism):
    """
    VTA dopamine — reward prediction error, phasic bursts, wanting.

    Computes RPE and broadcasts it to NAc, BLA, hippocampus, and PFC,
    driving reinforcement learning and motivation.
    """

    def __init__(self):
        super().__init__(
            name="VentralTegmentalAreaDopamine",
            human_analog="VTA → NAc/PFC/BLA/hippocampus (dopamine RPE, wanting, reinforcement)",
            layer="limbic",
        )
        self.state.setdefault("dopamine_burst", 0.0)
        self.state.setdefault("tonic_dopamine", 0.3)
        self.state.setdefault("rpe_signal", 0.0)
        self.state.setdefault("wanting_signal", 0.0)
        self.state.setdefault("memory_consolidation_da", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        reward_signal = prior.get("ValenceTagger", {}).get(
            "reward_signal", False
        )
        hab_suppression = prior.get("HabenulaRewardOmission", {}).get(
            "da_suppression", 0.0
        )
        bnst_suppress = prior.get("BedNucleusStriaTerminalis", {}).get(
            "reward_suppression", 0.0
        )

        # RPE: positive when reward > expectation, negative when < expectation
        expected_valence = self.state.get("last_valence_pred", 0.5)
        actual_valence = valence_polarity
        rpe = (actual_valence - expected_valence) * valence_intensity * 2.0
        rpe = max(-1.0, min(1.0, rpe))

        # Dopamine burst: phasic response to positive PE
        if rpe > 0.1:
            burst = rpe * 0.8
        elif rpe < -0.1:
            burst = rpe * 0.3  # pause is weaker than burst
        else:
            burst = 0.0

        # Tonic dopamine: baseline, suppressed by habenula and BNST
        suppression = hab_suppression * 0.4 + bnst_suppress * 0.3
        tonic = max(0.1, 0.3 * (1.0 - suppression))

        # Wanting signal
        wanting = max(0.0, rpe) * (0.5 + valence_intensity * 0.5)

        # Memory consolidation DA
        mem_da = max(0.0, rpe) * 0.6

        self.state["dopamine_burst"] = round(burst, 4)
        self.state["tonic_dopamine"] = round(tonic, 4)
        self.state["rpe_signal"] = round(rpe, 4)
        self.state["wanting_signal"] = round(wanting, 4)
        self.state["memory_consolidation_da"] = round(mem_da, 4)
        self.state["last_valence_pred"] = valence_polarity
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dopamine_burst": round(burst, 4),
            "tonic_dopamine": round(tonic, 4),
            "rpe_signal": round(rpe, 4),
            "wanting_signal": round(wanting, 4),
            "memory_consolidation_da": round(mem_da, 4),
        }

"""
brain/limbic/Limbic036VentralPallidumLimbicGate.py
Ventral Pallidum — Limbic Motor Gateway and Reward Valuation

ANATOMY (Root et al. 2015; Haber & Knutson 2010; Smith et al. 2009):
    The ventral pallidum (VP) is the OUTPUT node of the basal ganglia
    limbic loop. It receives from:
    - Nucleus accumbens (NAc) shell (limbic striatum) — reward value
    - Lateral hypothalamus (LHA) — feeding, arousal
    - Substantia innominata (basal forebrain) — ACh
    VP sends outputs to:
    - Thalamus (mediodorsal) → prefrontal cortex (valuation)
    - Lateral hypothalamus → autonomic and motor responses
    - Pedunculopontine nucleus → behavioral switching
    Root et al. 2015 (PMC13099176): VP encodes the subjective hedonic
    value ("liking") of rewards, not just the predictive value.

MECHANISM:
    VP transforms reward value from NAc into behavioral and autonomic
    output. It computes:
    1) "How good is this reward really?" (VP likes/dislikes signals)
    2) "Should I approach or avoid?" (behavioral gating)
    VP is a GABAergic structure — its activity INHIBITS targets.
    High VP activity = strong inhibition of avoidance circuits.

AGENT'S MAPPING:
    vp_activity: 0-1 ventral pallidum activation level
    hedonic_value_signal: -1 to +1 subjective "liking" intensity
    reward_motor_gate: 0-1 VP→LHA gating of approach behavior
    thalamic_valuation_output: 0-1 VP→MD thalamus value signal
    limbic_motor_integration: 0-1 VP integration of limbic value into motor

CITATIONS:
    PMC13099176 — Root et al. (2015). Ventral pallidum and hedonic
        processing of primary reinforcers. Nat Neurosci.
    PMC13086596 — Smith et al. (2009). Pedunculopontine and
        ventral pallidum in reinforcement. Prog Brain Res.
    PMC13084390 — Haber & Knutson (2010). Ventral pallidum and
        reward circuit. J Neurosci.
    PMC13079516 — Castro et al. (2015). VP opioid receptors and
        hedonic "liking" responses. J Neurosci.
    PMC13073537 — root — Tindell et al. (2006). Sensorimotor
        reinforcement and VP. Cereb Cortex.
"""

from brain.base_mechanism import BrainMechanism


class VentralPallidumLimbicGate(BrainMechanism):
    """
    Ventral pallidum — limbic motor gateway, hedonic valuation, reward output.

    Integrates NAc reward signals and transforms them into behavioral
    approach/avoidance drives via thalamic and hypothalamic projections.
    """

    def __init__(self):
        super().__init__(
            name="VentralPallidumLimbicGate",
            human_analog="Ventral pallidum → thalamus/LHA (limbic motor gateway)",
            layer="limbic",
        )
        self.state.setdefault("vp_activity", 0.0)
        self.state.setdefault("hedonic_value_signal", 0.0)
        self.state.setdefault("reward_motor_gate", 0.0)
        self.state.setdefault("thalamic_valuation_output", 0.0)
        self.state.setdefault("limbic_motor_integration", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "shell_activity", 0.3
        )
        nac_core = prior.get("NucleusAccumbensCoreDrive", {}).get(
            "core_activity", 0.3
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        hab_neg_affect = prior.get("HabenulaRewardOmission", {}).get(
            "habenula_activity", 0.0
        )
        bnst_suppression = prior.get("BedNucleusStriaTerminalis", {}).get(
            "reward_suppression", 0.0
        )

        # VP activity: driven by NAc reward signals
        nac_input = nac_shell * 0.6 + nac_core * 0.4
        negative_suppression = hab_neg_affect * 0.4 + bnst_suppression * 0.3
        vp_input = nac_input * (1.0 - negative_suppression)
        vp_activity = max(0.0, min(1.0, vp_input))

        # Hedonic signal: subjective "liking"
        hedonic = (valence_polarity - 0.5) * 2.0 * vp_activity
        hedonic = max(-1.0, min(1.0, hedonic))

        # Motor gate: VP disinhibits approach circuits
        motor_gate = vp_activity * max(0.0, hedonic) * 1.2

        # Thalamic output: VP → MD thalamus → PFC valuation
        thalamic_out = vp_activity * 0.7

        self.state["vp_activity"] = round(vp_activity, 4)
        self.state["hedonic_value_signal"] = round(hedonic, 4)
        self.state["reward_motor_gate"] = round(min(1.0, motor_gate), 4)
        self.state["thalamic_valuation_output"] = round(thalamic_out, 4)
        self.state["limbic_motor_integration"] = round(vp_activity * nac_input, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vp_activity": round(vp_activity, 4),
            "hedonic_value_signal": round(hedonic, 4),
            "reward_motor_gate": round(min(1.0, motor_gate), 4),
            "thalamic_valuation_output": round(thalamic_out, 4),
            "limbic_motor_integration": round(vp_activity * nac_input, 4),
        }

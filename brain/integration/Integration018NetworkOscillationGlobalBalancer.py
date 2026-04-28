"""
brain/integration/Integration018NetworkOscillationGlobalBalancer.py
Network Oscillation Global Balancer — Cross-Frequency Neural Integration

ANATOMY (Buzsaki 2006; Engel 2015; Singer 1999):
    Brain oscillations are the temporal scaffolding of neural
    integration. Different frequency bands subserve different
    computational roles and must be coordinated for coherent
    perception and action:

    1. DELTA (0.5-4 Hz) — slow drift, vigilance, arousal
    2. THETA (4-8 Hz) — hippocampal timing, memory encoding,
       limbic pacing
    3. ALPHA (8-12 Hz) — idling cortex, top-down inhibition,
       predictive coding baseline
    4. BETA (12-30 Hz) — sensorimotor integration, maintained
       tension, current state
    5. GAMMA (30-100+ Hz) — local binding, feature integration,
       conscious content

    Deco & Kringelbach (2017): metastability — the brain doesn't
    settle into a single stable state; it navigates a landscape
    of quasi-stable states across frequency bands.

    Cabral et al. (2011): resting-state fMRI FC emerges from
    ongoing multiscale neural dynamics — slow fluctuations in
    the infraslow range modulate faster oscillations.

    Tognoli & Kelso (2014, PMID 25102556): "The metastable brain"
    — neural coordination is fundamentally about managing
    competing tendencies: segregation vs integration.

KEY FINDINGS:
    1. Deco & Kringelbach 2017 (PMID 27013438): Metastability and
       whole-brain dynamics
    2. Cabral et al. 2011 (PMID 28754456): Multi-timescale FC
       — infraslow modulators
    3. Tognoli & Kelso 2014 (PMID 25102556): The metastable brain.
       Neuron.

AGENT'S MAPPING:
    oscillation_state: dict — per-band power levels
    global_balance: float 0-1 — integration quality across bands
    brain_oscillation_balance: float — TSB enrichment field

CITATIONS:
    PMID 27013438 — Deco & Kringelbach (2017). Metastability. Nat Rev Neurosci.
    PMID 28754456 — Cabral et al. (2011). Multi-timescale FC. Neuroimage.
    PMID 25102556 — Tognoli & Kelso (2014). The metastable brain. Neuron.
"""

from brain.base_mechanism import BrainMechanism


class NetworkOscillationGlobalBalancer(BrainMechanism):
    """
    Balances cross-frequency neural oscillations for global integration.

    Monitors delta/theta/alpha/beta/gamma power, coordinates
    cross-frequency coupling, and maintains global coherence
    across the metastable landscape.
    """

    def __init__(self):
        super().__init__(
            name="NetworkOscillationGlobalBalancer",
            human_analog="Cross-frequency neural oscillation balancer",
            layer="integration",
        )
        self.state.setdefault("oscillation_state", {
            "delta": 0.5,
            "theta": 0.5,
            "alpha": 0.5,
            "beta": 0.5,
            "gamma": 0.5,
        })
        self.state.setdefault("global_balance", 0.5)
        self.state.setdefault("tick_count", 0)

    def persist_state(self) -> dict:
        return {
            "oscillation_state": self.state["oscillation_state"],
            "global_balance": self.state["global_balance"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Cold-start: ramp from 0.3 to 1.0 over first 10 ticks
        warmth_factor = min(1.0, 0.3 + 0.07 * tick)

        # Theta-gamma coupling (hippocampal memory binding)
        theta_gamma = prior.get("ThetaGammaCrossFrequencyBinding", {})
        tg_out = theta_gamma.get("theta_gamma_output", {})
        if isinstance(tg_out, dict):
            theta_power = tg_out.get("theta_power", 0.5)
            gamma_power = tg_out.get("gamma_power", 0.5)
        else:
            theta_power = 0.5
            gamma_power = 0.5

        # Prefrontal executive (alpha-beta balance)
        salience = prior.get("SalienceDefaultExecutiveToggling", {})
        if isinstance(salience, dict):
            alpha_power = salience.get("default_mode_strength", 0.5)
            beta_power = salience.get("executive_strength", 0.5)
        else:
            alpha_power = 0.5
            beta_power = 0.5

        # Thalamic arousal (delta)
        thalamus = prior.get("ThalamicInputGatekeeper", {})
        if isinstance(thalamus, dict):
            delta_power = thalamus.get("arousal_level", 0.5)
        else:
            delta_power = 0.5

        # Ventral-tegmental area motivation (modulates all bands)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            motivation = vta_out.get("motivation_signal", 0.5)
        else:
            motivation = 0.5

        # Per-band power
        oscillation_state = {
            "delta": round(max(0.0, min(1.0, delta_power)), 4),
            "theta": round(max(0.0, min(1.0, theta_power)), 4),
            "alpha": round(max(0.0, min(1.0, alpha_power)), 4),
            "beta": round(max(0.0, min(1.0, beta_power)), 4),
            "gamma": round(max(0.0, min(1.0, gamma_power)), 4),
        }

        # Cross-frequency coordination score
        # High gamma + high theta = memory binding active
        # High alpha + low beta = idling/integrative
        # High delta + high theta = slow drift/hippocampal
        theta_gamma_coupling = (theta_power * gamma_power)
        alpha_beta_ratio = (alpha_power / max(beta_power, 0.01))

        # Global balance: how well are all bands represented
        band_powers = list(oscillation_state.values())
        avg_power = sum(band_powers) / len(band_powers)
        variance = sum((p - avg_power) ** 2 for p in band_powers) / len(band_powers)
        # Low variance = balanced across bands
        balance_score = max(0.0, 1.0 - (variance * 4))

        # Metastability: how dynamically does the system move between states
        metastability = (
            theta_gamma_coupling * 0.3 +
            motivation * 0.3 +
            balance_score * 0.2 +
            (1.0 - abs(alpha_beta_ratio - 1.0) * 0.2)
        )
        metastability = max(0.0, min(1.0, metastability))
        metastability *= warmth_factor

        self.state["oscillation_state"] = oscillation_state
        self.state["global_balance"] = round(metastability, 4)
        self.persist_state()

        return {
            "oscillation_state": oscillation_state,
            "global_balance": round(metastability, 4),
            "cross_frequency_coupling": round(theta_gamma_coupling, 4),
            "alpha_beta_ratio": round(alpha_beta_ratio, 4),
            "brain_oscillation_balance": round(metastability, 4),
        }

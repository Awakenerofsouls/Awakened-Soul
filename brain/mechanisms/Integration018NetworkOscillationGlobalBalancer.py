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


CITATIONS
---------
  - [Buzsaki 2006, Rhythms of the Brain]
  - [Steriade 1993, J Neurosci 13:3252, oscillations]
  - [Klimesch 1999, Brain Res Rev 29:169, EEG alpha theta]
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

    # ------------------------------------------------------------------
    # Extended derived-state helpers
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


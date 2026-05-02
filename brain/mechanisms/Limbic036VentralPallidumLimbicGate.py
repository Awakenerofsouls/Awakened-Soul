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

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs


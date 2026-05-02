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

CITATIONS
---------
  - [Lammel 2014, Neuron 76:855, VTA dopamine heterogeneity]
  - [Schultz 1998, J Neurophysiol 80:1, dopamine RPE]
  - [Watabe-Uchida 2017, Annu Rev Neurosci 40:373, VTA inputs]

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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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


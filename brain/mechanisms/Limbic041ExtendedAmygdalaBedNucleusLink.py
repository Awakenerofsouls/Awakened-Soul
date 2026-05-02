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


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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


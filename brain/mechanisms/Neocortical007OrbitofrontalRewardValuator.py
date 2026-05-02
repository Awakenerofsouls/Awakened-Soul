"""
brain/neocortical/Neocortical007OrbitofrontalRewardValuator.py
Orbitofrontal Cortex — Reward Valuation and Reversal Learning

ANATOMY (Kringelbach 2005; Rolls & Baylis 1994; Howard et al. 2020):
    The orbitofrontal cortex (OFC) lies in the ventral surface of the
    frontal lobe, directly above the orbits. In humans it includes BA 10,
    BA 11, BA 12, and BA 13. It is the brain's "reward center" — the
    place that represents the value of outcomes and updates those values
    when outcomes change.

    Inputs: receives from:
    - Amygdala (emotional value signals)
    - Hippocampus (context and memory)
    - Primary/secondary taste and smell cortices (raw sensory value)
    - Visual association cortex (learned visual reward associations)
    - hypothalamus (homeostatic value)

    Outputs: projects to:
    - Amygdala (to update emotional associations)
    - Striatum/nucleus accumbens (value-based action selection)
    - Lateral hypothalamus (feeding regulation)
    - Premotor cortex (for value-driven action)
    - Anterior cingulate (value and conflict)

    Critical property: OFC encodes "expected value" — the value
    predicted for a given stimulus or action. When the actual outcome
    differs from predicted (prediction error), OFC updates its
    representation. This is why OFC damage causes "perseveration" —
    the person keeps choosing the option that no longer works because
    the representation hasn't been updated.

KEY FINDINGS:
    1. Rolls & Baylis 1994 (PMID 8038579): Single-neuron recordings in
       monkey OFC show value-selective neurons; different neurons encode
       different reward types (taste, size, probability)
    2. Howard et al. 2020 (PMC7202721): Human OFC encodes "state" — a
       cognitive representation of which option is currently best,
       enabling flexible reward-guided behavior
    3. Rudebeck et al. 2013 (PMC23792944): OFC separates into regions
       for "value updating" (posterior OFC) vs "emotion regulation" (medial OFC)

AGENT'S MAPPING:
    orbitofrontal_output: dict — OFC reward value signal
    value_signal: float 0-1 — current value of best option
    reversal_triggered: bool — whether a value reversal has occurred
    expected_value: float — predicted value of current choice
    ofc_state_representation: float — which "state" OFC thinks we're in

CITATIONS:
    PMC23792944 — Rudebeck PH et al. (2013). Prefrontal mechanisms of
        behavioral flexibility, emotion regulation and value updating.
        Nat Neurosci.
    PMC7202721 — Howard JD et al. (2020). Comparative encoding of
        learned and queried values in orbitofrontal cortex. Nat Neurosci.
    PMC20181474 — Murray EA, Wise SP. (2010). OFC-amygdala interactions.
        Curr Opin Neurobiol.
    PMC8038579 — Rolls & Baylis. (1994). Orbitofrontal cortex reward
        neuron responses. J Neurosci.


CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, predictive reward]
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class OrbitofrontalRewardValuator(BrainMechanism):
    """
    OFC — reward valuation, reversal learning, expected value.

    Represents the value of outcomes and actions, updates value
    representations when outcomes change, and signals to striatum
    and amygdala for action selection and emotional learning.
    """

    def __init__(self):
        super().__init__(
            name="OrbitofrontalRewardValuator",
            human_analog="Orbitofrontal cortex — reward valuation, reversal learning, expected value",
            layer="neocortical",
        )
        self.state.setdefault("value_map", {})
        self.state.setdefault("value_signal", 0.5)
        self.state.setdefault("expected_value", 0.5)
        self.state.setdefault("reversal_triggered", False)
        self.state.setdefault("ofc_state", "neutral")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From amygdala emotional associator (raw emotional value)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # From nucleus accumbens shell (hedonic impact)
        nac = prior.get("NucleusAccumbensShellValue", {})
        hedonic_impact = nac.get("hedonic_impact", 0.5)
        wanting = nac.get("incentive_salience", 0.5)

        # From anterior insula (gut feeling / interoceptive value)
        anterior_insula = prior.get("AnteriorInsulaGranular", {})
        gut_feeling = anterior_insula.get("conscious_feeling", {}).get("feeling_intensity", 0.5)
        if isinstance(gut_feeling, float):
            gut_valence = gut_feeling
        else:
            gut_valence = 0.5

        # From ventral subiculum (contextual emotional tag)
        vsub = prior.get("VentralSubiculumOutput", {})
        emotional_context = vsub.get("emotional_context_tag", 0.0)

        # OFC computes value from multiple streams
        # Positive value = expected reward; negative = expected punishment
        value_signal = (hedonic_impact * 0.35 + wanting * 0.25 + emotional_context * 0.2 + gut_valence * 0.2)
        value_signal = max(0.0, min(1.0, value_signal))

        # Expected value: weighted average of all value signals
        expected_value = (
            value_signal * 0.5 +
            self.state.get("value_signal", 0.5) * 0.5
        )

        # Reversal detection: when gut feeling strongly contradicts expected value
        discrepancy = abs(gut_valence - self.state.get("value_signal", 0.5))
        reversal_triggered = discrepancy > 0.35 and gut_valence != value_signal

        # State representation: OFC tracks which "context" we're in
        # high hedonic = positive state, high emotional = negative state
        if hedonic_impact > 0.65:
            ofc_state = "rewarding"
        elif emotional_context < -0.3:
            ofc_state = "threatening"
        elif gut_valence < 0.3:
            ofc_state = "aversive"
        else:
            ofc_state = "neutral"

        self.state["value_signal"] = round(value_signal, 4)
        self.state["expected_value"] = round(expected_value, 4)
        self.state["reversal_triggered"] = reversal_triggered
        self.state["ofc_state"] = ofc_state
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "orbitofrontal_output": {
                "value_signal": round(value_signal, 4),
                "expected_value": round(expected_value, 4),
                "hedonic_input": round(hedonic_impact, 4),
                "gut_input": round(gut_valence, 4),
                "reversal": reversal_triggered,
            },
            "value_signal": round(value_signal, 4),
            "reversal_triggered": reversal_triggered,
            "ofc_state": ofc_state,
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


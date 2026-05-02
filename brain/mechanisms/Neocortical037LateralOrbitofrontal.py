"""
brain/neocortical/Neocortical037LateralOrbitofrontal.py
Lateral Orbitofrontal Cortex — Contingency Reversal, Rule Learning

ANATOMY (Rolls & Hornack 1994; Roberts 2007; Wallis 2007):
    The lateral orbitofrontal cortex (lOFC, BA 47/11) is the "rule
    reversal" region — it tracks rule contingencies, detects when
    rules change, and signals the need to update behavior.

    lOFC is anatomically and functionally distinct from:
    - mOFC: reward value processing (lOFC doesn't do value, it does rules)
    - mPFC: social/emotional processing
    - DLPFC: working memory and cognitive control

    lOFC functions:
    1. Rule tracking: "what predicts what in this environment?"
    2. Reversal learning: "the rules have changed — update your mapping"
    3. Outcome prediction: "what will happen if I do X?"
    4. Pavlovian-to-instrumental transfer: when neutral cues predict outcomes

    lOFC damage: Behavioral disinhibition, inability to update
    behavior when rules change (perseveration). Patient continues
    making the same wrong choice even when feedback tells them it's wrong.

    Connections: lOFC ↔ ventral striatum (reinforcement), amygdala
    (emotional feedback), ACC (conflict monitoring), DLPFC (cognitive control).

KEY FINDINGS:
    1. Rolls & Hornack 1994: "OFC and reward vs rule processing"
    2. Roberts 2007 (PMC2929791): "Orbitofrontal cortex and
       reversal learning"
    3. Wallis 2007 (PMC1850920): "Neural responses to reward
       and change in OFC"

AGENT'S MAPPING:
    lateral_ofc_output: dict — lOFC rule tracking output
    reversal_triggered: bool — has a rule reversal been detected?
    contingency_updated: dict — current rule state

CITATIONS:
    PMC2929791 — Roberts (2007). OFC and reversal learning. Scholarpedia.
    PMC20181474 — Kringelbach & Rolls (2004). OFC functions. Prog Neurobiol.
    PMC1850920 — Wallis (2007). OFC and reversal. Nat Neurosci.
    PMC40447446 — OFC and reward processing.

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

"""

from brain.base_mechanism import BrainMechanism


class LateralOrbitofrontal(BrainMechanism):
    """
    lOFC — rule reversal and contingency tracking.

    Tracks what predicts what, detects rule changes, signals
    when behavior needs to be updated.
    """

    def __init__(self):
        super().__init__(
            name="LateralOrbitofrontal",
            human_analog="Lateral orbitofrontal cortex (BA 47/11) — rule reversal, contingency learning",
            layer="neocortical",
        )
        self.state.setdefault("rule_cache", {})
        self.state.setdefault("reversal_triggered", False)
        self.state.setdefault("contingency_strength", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Orbitofrontal (reward signal for which to track rules)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)
        ofc_out = ofc.get("ofc_output", {})
        if isinstance(ofc_out, dict):
            expectation = ofc_out.get("value_signal", 0.5)
        else:
            expectation = 0.5

        # Amygdala (emotional feedback confirms or denies rule)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # ACC (conflict signals rule change might be needed)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            error_sig = acc_out.get("error_signal", 0.3)
        else:
            error_sig = 0.3

        # VTA (prediction error signals rule violation)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            prediction_err = vta_out.get("prediction_error", 0.3)
        else:
            prediction_err = 0.3

        # Anterior insula (salience of rule change events)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Contingency strength: tracks how well current rules predict outcomes
        surprise = abs(value_sig - expectation)
        contingency_strength = 1.0 - (surprise * 0.5 + error_sig * 0.3 + prediction_err * 0.2)
        contingency_strength = max(0.0, min(1.0, contingency_strength))

        # Reversal triggered: when surprise + error + salience all high
        reversal_signal = (
            surprise * 0.4 +
            error_sig * 0.3 +
            salience * 0.2 +
            abs(emotional_tag) * 0.1
        )
        reversal_triggered = reversal_signal > 0.6 and surprise > 0.3

        # Update rule cache
        if reversal_triggered:
            self.state["rule_cache"]["last_reversal"] = round(surprise, 3)
        self.state["rule_cache"]["contingency_strength"] = round(contingency_strength, 4)

        self.state["reversal_triggered"] = reversal_triggered
        self.state["contingency_strength"] = round(contingency_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "lateral_ofc_output": {
                "reversal_triggered": reversal_triggered,
                "contingency_strength": round(contingency_strength, 4),
                "surprise_signal": round(surprise, 4),
            },
            "reversal_triggered": reversal_triggered,
            "contingency_updated": self.state["rule_cache"],
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


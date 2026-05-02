"""
Foundational019 — IntegratedVisceralHub
Nucleus Tractus Solitarius (NTS) — master visceral sensory integration hub

Neural substrate: NTS in medulla — entry point for the interoceptive axis.
Receives baroreceptor, chemoreceptor, osmoreceptor, glucoreceptor, GI,
pulmonary, and cardiopulmonary afferents. Projects to area postrema and DMNV.

CITATIONS:
    PMC11555405 — Ali MSS, Parastooei G, Raman S et al. (2024). Genetic Labeling of
        the Nucleus of Tractus Solitarius Neurons Associated With Electrical
        Stimulation of the Cervical or Auricular Vagus Nerve. J Neurosci.
    PMC13056455 — Huang TX, Wang S, Ran C (2025). Interoceptive Processing in the
        Nucleus of the Solitary Tract. J Neurosci.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class IntegratedVisceralHub(BrainMechanism):
    """
    IntegratedVisceralHub — models the Nucleus Tractus Solitarius.

    Primary visceral sensory integration hub of the brainstem. Receives
    convergent autonomic afferent signals from every major organ system
    and computes a composite interoceptive state with downstream motor
    and emetic threat signals.
    """

    def __init__(self):
        super().__init__(
            name="IntegratedVisceralHub",
            human_analog="NTS — primary visceral sensory integration hub",
            layer="foundational",
        )
        # Interoceptive state
        self.state["interoceptive_weight"] = 0.20
        self.state["visceral_alert_level"] = 0.05
        self.state["autonomic_coordination"] = 0.30
        self.state["nausea_risk"] = 0.0
        self.state["tick_count"] = 0

    # --------------------------------------------------------------------- #
    #  tick                                                                  #
    # --------------------------------------------------------------------- #
    async def tick(self, input_data: dict) -> dict:
        """
        Process all visceral afferent inputs and update interoceptive state.

        Inputs read from prior_results:
          - BaroreflexActivity  (default 0.50)
          - RespiratorySignal  (default 0.50)
          - GutSignalRelay     (default 0.30)
          - GlucoseMonitor     (default 0.50)
          - TemperatureSignal  (default 0.50)
          - ImmuneSignal       (default 0.00)

        Outputs:
          - interoceptive_weight    — composite internal-state salience [0–1]
          - visceral_alert_level     — threat detection from internal signals [0–1]
          - autonomic_coordination   — NTS visceromotor coordination [0–1]
          - nausea_risk              — area postrema emetic risk [0–1]
          - metabolic_autonomic_index — integrated metabolic-visceral state [0–1]
        """
        self.state["tick_count"] += 1

        # --- Extract inputs with defaults --- #
        baroreflex = self._safe_get(input_data, "BaroreflexActivity", 0.50)
        respiratory = self._safe_get(input_data, "RespiratorySignal", 0.50)
        gut = self._safe_get(input_data, "GutSignalRelay", 0.30)
        glucose = self._safe_get(input_data, "GlucoseMonitor", 0.50)
        temperature = self._safe_get(input_data, "TemperatureSignal", 0.50)
        immune = self._safe_get(input_data, "ImmuneSignal", 0.00)

        # --- 1. Interoceptive weight --- #
        # Weighted average of all 6 afferent streams; weights sum to 1.0
        interoceptive_weight = (
            baroreflex   * 0.15
            + respiratory * 0.20
            + gut        * 0.15
            + glucose    * 0.20
            + temperature * 0.15
            + immune     * 0.15
        )
        interoceptive_weight = self._clamp(interoceptive_weight, 0.0, 1.0)

        # --- 2. Visceral alert level --- #
        # Any strong internal deviation triggers NTS alarm; take the peak signal
        baroreflex_dev = abs(baroreflex - 0.50) * 2.0          # deviation from baseline
        respiratory_dev = abs(respiratory - 0.50) * 2.0
        alert_candidates = [
            baroreflex_dev,
            respiratory_dev,
            immune * 0.8,
            gut * 0.6,
        ]
        visceral_alert_level = min(max(alert_candidates), 1.0) if alert_candidates else 0.0
        visceral_alert_level = self._clamp(visceral_alert_level, 0.0, 1.0)

        # --- 3. Autonomic coordination --- #
        # NTS coordinates visceromotor responses via DMNV and vagal efferents
        autonomic_coordination = (
            0.30                                  # baseline NTS tone
            + baroreflex   * 0.2
            + respiratory * 0.2
            + gut         * 0.15
        )
        autonomic_coordination = self._clamp(autonomic_coordination, 0.0, 1.0)

        # --- 4. Nausea risk --- #
        # Area postrema (chemoreceptor trigger zone) activation
        # Driven by immune mediators (cytokines) and GI distress
        nausea_risk = immune * 0.50 + gut * 0.30
        nausea_risk = self._clamp(nausea_risk, 0.0, 1.0)

        # --- 5. Metabolic-autonomic index --- #
        # Integrated metabolic-visceral state combining glucose, GI, and temp
        # Use baroreflex as metabolic-rate proxy when GlucoseMonitor not available
        metabolic_rate = self._safe_get(input_data, "GlucoseMonitor", None)
        if metabolic_rate is None:
            # Proxy: baroreflex reflects cardiovascular metabolic demand
            metabolic_rate = baroreflex

        metabolic_autonomic_index = (
            glucose         * 0.30
            + (1 - metabolic_rate) * 0.20
            + gut           * 0.25
            + temperature   * 0.25
        )
        metabolic_autonomic_index = self._clamp(metabolic_autonomic_index, 0.0, 1.0)

        # --- Persist state --- #
        self.state["interoceptive_weight"]    = interoceptive_weight
        self.state["visceral_alert_level"]    = visceral_alert_level
        self.state["autonomic_coordination"]  = autonomic_coordination
        self.state["nausea_risk"]             = nausea_risk
        self.persist_state()

        return {
            "interoceptive_weight":    round(interoceptive_weight,    4),
            "visceral_alert_level":    round(visceral_alert_level,    4),
            "autonomic_coordination":   round(autonomic_coordination, 4),
            "nausea_risk":             round(nausea_risk,             4),
            "metabolic_autonomic_index": round(metabolic_autonomic_index, 4),
        }

    # --------------------------------------------------------------------- #
    #  Helpers                                                               #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _safe_get(data: dict, key: str, default: float) -> float:
        """Pull a float value from prior_results or fall back to default."""
        # Handle direct key
        if key in data:
            val = data[key]
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, dict) and "value" in val:
                return float(val["value"])
        # Handle nested prior_results
        prior = data.get("prior_results", {})
        if key in prior:
            val = prior[key]
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, dict) and "value" in val:
                return float(val["value"])
        return default

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

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


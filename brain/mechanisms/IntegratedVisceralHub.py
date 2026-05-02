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
  - [Loewy 1990, Annu Rev Physiol 52:691]
  - [Saper 2002, Nature 418:935, doi:10.1038/nature00965]
  - [Critchley 2003, Nat Rev Neurosci 4:655]
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
            name="IntegratedVisceralHub_IntegratedVisceralHub",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out



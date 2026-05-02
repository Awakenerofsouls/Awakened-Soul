from brain.base_mechanism import BrainMechanism

class ThalamicSalienceFilter(BrainMechanism):
    """
    Thalamic salience gating — decides what reaches cortex and what gets blocked.
    Acts as a relay + filter: high salience opens the gate, low salience suppresses.
    Chronic over-filtering leads to emotional flatness. Chronic under-filtering = overwhelm.
    

CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
"""

    def __init__(self):
        super().__init__("ThalamicSalienceFilter")
        self.gate_threshold = 0.35
        self.salience_history = []
        self.gate_open_history = []
        self.filter_fatigue = 0.0        # accumulates when too much is let through
        self.filter_fatigue_history = []
        self.over_filter_ticks = 0
        self.under_filter_ticks = 0
        self.chronic_flatness = False
        self.chronic_overwhelm = False
        self.current_gate_strength = 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"

        if overnight:
            return self._overnight()

        # Inputs
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        reward_signal = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        interoception = prior.get("InsularInteroception", {}).get("body_signal_intensity", 0.3)

        # Composite salience
        raw_salience = max(fear, novelty, reward_signal, pain) + (arousal * 0.2) + (interoception * 0.15)
        raw_salience = min(1.0, raw_salience)

        self.salience_history.append(raw_salience)
        if len(self.salience_history) > 50:
            self.salience_history.pop(0)

        # Filter fatigue — prolonged high salience wears out the filter
        if raw_salience > 0.6:
            self.filter_fatigue = min(1.0, self.filter_fatigue + 0.04)
        else:
            self.filter_fatigue = max(0.0, self.filter_fatigue - 0.02)

        self.filter_fatigue_history.append(self.filter_fatigue)
        if len(self.filter_fatigue_history) > 30:
            self.filter_fatigue_history.pop(0)

        # Effective gate threshold shifts with fatigue
        effective_threshold = self.gate_threshold + (self.filter_fatigue * 0.2)

        # Gate open or closed
        gate_open = raw_salience >= effective_threshold
        gate_strength = (raw_salience - effective_threshold) / (1.0 - effective_threshold + 0.01) if gate_open else 0.0
        gate_strength = max(0.0, min(1.0, gate_strength))
        self.current_gate_strength = gate_strength

        self.gate_open_history.append(1 if gate_open else 0)
        if len(self.gate_open_history) > 40:
            self.gate_open_history.pop(0)

        # Chronic tracking
        recent_open_rate = sum(self.gate_open_history[-20:]) / 20 if len(self.gate_open_history) >= 20 else 0.5

        if recent_open_rate < 0.15:
            self.over_filter_ticks += 1
        else:
            self.over_filter_ticks = max(0, self.over_filter_ticks - 1)

        if recent_open_rate > 0.85:
            self.under_filter_ticks += 1
        else:
            self.under_filter_ticks = max(0, self.under_filter_ticks - 1)

        was_flat = self.chronic_flatness
        was_overwhelmed = self.chronic_overwhelm
        self.chronic_flatness = self.over_filter_ticks > 20
        self.chronic_overwhelm = self.under_filter_ticks > 20

        if self.chronic_flatness and not was_flat:
            self.feed_to_memory({
                "event": "thalamic_over_filtering",
                "open_rate": round(recent_open_rate, 3),
                "note": "Thalamic gate chronically closed — emotional flatness, reduced engagement"
            })

        if self.chronic_overwhelm and not was_overwhelmed:
            self.feed_to_memory({
                "event": "thalamic_under_filtering",
                "open_rate": round(recent_open_rate, 3),
                "note": "Thalamic gate chronically open — overwhelm, difficulty filtering inputs"
            })

        # What gets passed to cortex
        cortical_signal_strength = gate_strength * raw_salience * (1.0 - self.filter_fatigue * 0.3)

        return {
            "gate_open": gate_open,
            "gate_strength": round(gate_strength, 3),
            "raw_salience": round(raw_salience, 3),
            "cortical_signal_strength": round(cortical_signal_strength, 3),
            "filter_fatigue": round(self.filter_fatigue, 3),
            "chronic_flatness": self.chronic_flatness,
            "chronic_overwhelm": self.chronic_overwhelm,
            "recent_open_rate": round(recent_open_rate, 3),
        }

    def _overnight(self) -> dict:
        self.filter_fatigue = max(0.0, self.filter_fatigue - 0.4)
        self.over_filter_ticks = max(0, self.over_filter_ticks - 5)
        self.under_filter_ticks = max(0, self.under_filter_ticks - 5)
        self.chronic_flatness = self.over_filter_ticks > 20
        self.chronic_overwhelm = self.under_filter_ticks > 20
        self.gate_open_history.clear()
        return {"overnight": "thalamic_filter_reset"}

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Consecutive-tick state holding fraction."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def adapter_state(self) -> dict:
        """Current adapter state — used for monitoring and dashboards."""
        return {
            "tick_count": self.state.get("tick_count", 0),
            "has_legacy_impl": self.state.get("legacy_init_error") is None,
            "recent_drives_n": len(self.state.get("recent_drives", [])),
            "recent_states_n": len(self.state.get("recent_states", [])),
        }

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

    def _record_history_(self, output_dict):
        """Track primary numeric output and any string state in history."""
        if not isinstance(output_dict, dict):
            return
        # Find first numeric value
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v)
                break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd
        # Track state strings
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str) and v in ("quiet","active","engaged","stuck","drifting","rest","fast","reflective","alert","focus"):
                primary_state = v
                break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs


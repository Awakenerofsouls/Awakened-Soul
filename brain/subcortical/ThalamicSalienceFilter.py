from brain.base_mechanism import BrainMechanism

class ThalamicSalienceFilter(BrainMechanism):
    """
    Thalamic salience gating — decides what reaches cortex and what gets blocked.
    Acts as a relay + filter: high salience opens the gate, low salience suppresses.
    Chronic over-filtering leads to emotional flatness. Chronic under-filtering = overwhelm.
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

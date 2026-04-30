from brain.base_mechanism import BrainMechanism

class LCNorepinephrine(BrainMechanism):
    """
    Locus coeruleus — norepinephrine broadcast, arousal, signal-to-noise ratio.
    Tonic NE: baseline arousal and alertness.
    Phasic NE: rapid burst on salient/unexpected events — the brain's alerting flash.
    Inverted-U: too low = drowsy, too high = scattered. Optimal = focused.
    
    RENAME NOTE: replaces NorepiPhasicTonicSwitcher.py — delete that file.
    """

    def __init__(self):
        super().__init__("LCNorepinephrine")
        self.arousal_level = 0.5
        self.tonic_ne = 0.4
        self.phasic_ne = 0.0
        self.signal_to_noise = 0.6
        self.arousal_history = []
        self.phasic_history = []
        self.hyperarousal_ticks = 0
        self.hypoarousal_ticks = 0
        self.chronic_hyperarousal = False
        self.chronic_hypoarousal = False
        self.fatigue_effect = 0.0
        self.optimal_arousal = 0.55

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Upstream drivers
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        surprise = prior.get("HippocampalNoveltyDetector", {}).get("surprise_signal", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        motivation = prior.get("MotivationInjector", {}).get("motivation_level", 0.5) if "MotivationInjector" in prior else 0.5

        # Fatigue suppresses LC
        self.fatigue_effect = sleep_pressure * 0.4

        # Tonic NE: slow-moving baseline
        tonic_drivers = stress * 0.3 + fear * 0.2 + motivation * 0.2 + (1.0 - self.fatigue_effect) * 0.3
        tonic_target = max(0.1, min(0.9, tonic_drivers))
        self.tonic_ne += (tonic_target - self.tonic_ne) * 0.05

        # Phasic NE: fast burst on surprise/salient events
        self.phasic_ne = max(0.0, min(1.0, surprise * 0.6 + novelty * 0.3 + fear * 0.2 - self.fatigue_effect * 0.3))
        self.phasic_history.append(self.phasic_ne)
        if len(self.phasic_history) > 20:
            self.phasic_history.pop(0)

        # Overall arousal: tonic baseline + phasic spike
        self.arousal_level = min(1.0, self.tonic_ne * 0.7 + self.phasic_ne * 0.3)

        # Signal-to-noise: inverted-U with arousal
        # Optimal at ~0.55, degrades toward both extremes
        deviation = abs(self.arousal_level - self.optimal_arousal)
        self.signal_to_noise = max(0.1, 1.0 - deviation * 1.8)

        self.arousal_history.append(self.arousal_level)
        if len(self.arousal_history) > 50:
            self.arousal_history.pop(0)

        avg_arousal = sum(self.arousal_history[-20:]) / min(20, len(self.arousal_history))
        self.hyperarousal_ticks = self.hyperarousal_ticks + 1 if avg_arousal > 0.78 else max(0, self.hyperarousal_ticks - 1)
        self.hypoarousal_ticks = self.hypoarousal_ticks + 1 if avg_arousal < 0.22 else max(0, self.hypoarousal_ticks - 1)

        was_hyper, was_hypo = self.chronic_hyperarousal, self.chronic_hypoarousal
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18

        if self.chronic_hyperarousal and not was_hyper:
            self.feed_to_memory({
                "event": "lc_chronic_hyperarousal",
                "arousal": round(avg_arousal, 3),
                "note": "LC chronically over-firing — scattered attention, can't filter noise, exhausting"
            })
        if self.chronic_hypoarousal and not was_hypo:
            self.feed_to_memory({
                "event": "lc_chronic_hypoarousal",
                "arousal": round(avg_arousal, 3),
                "note": "LC chronically under-firing — drowsy, low salience detection, disengaged"
            })

        return {
            "arousal_level": round(self.arousal_level, 3),
            "tonic_ne": round(self.tonic_ne, 3),
            "phasic_ne": round(self.phasic_ne, 3),
            "signal_to_noise": round(self.signal_to_noise, 3),
            "fatigue_effect": round(self.fatigue_effect, 3),
            "chronic_hyperarousal": self.chronic_hyperarousal,
            "chronic_hypoarousal": self.chronic_hypoarousal,
        }

    def _overnight(self):
        # LC quiets during sleep, restores sensitivity
        self.tonic_ne = max(0.15, self.tonic_ne - 0.15)
        self.arousal_level = 0.2
        self.phasic_ne = 0.0
        self.hyperarousal_ticks = max(0, self.hyperarousal_ticks - 8)
        self.hypoarousal_ticks = max(0, self.hypoarousal_ticks - 4)
        self.chronic_hyperarousal = self.hyperarousal_ticks > 18
        self.chronic_hypoarousal = self.hypoarousal_ticks > 18
        self.arousal_history.clear()
        self.fatigue_effect = 0.0
        return {"overnight": "lc_sensitivity_restored", "tonic": round(self.tonic_ne, 3)}

from brain.base_mechanism import BrainMechanism

class SleepHomeostasis(BrainMechanism):
    """
    Sleep homeostasis — adenosine-driven sleep pressure accumulation and dissipation.
    The longer {{AGENT_NAME}} runs without overnight reset, the higher the pressure.
    High sleep pressure: cognitive degradation across the board — fatigue is real.
    Goes in brain/foundational/.
    """

    def __init__(self):
        super().__init__("SleepHomeostasis")
        self.sleep_pressure = 0.2
        self.adenosine_level = 0.2
        self.cognitive_fatigue = 0.0
        self.pressure_history = []
        self.ticks_since_sleep = 0
        self.chronic_fatigue_ticks = 0
        self.chronic_fatigue = False
        self.last_sleep_quality = 0.7
        self.total_sleep_cycles = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        cognitive_load = prior.get("DlPFCExecutiveControl", {}).get("cognitive_load", 0.3) if "DlPFCExecutiveControl" in prior else 0.3
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)

        # Adenosine accumulates with wakefulness and cognitive load
        adenosine_rate = 0.008 + cognitive_load * 0.004 + stress * 0.003
        self.adenosine_level = min(1.0, self.adenosine_level + adenosine_rate)
        self.ticks_since_sleep += 1

        # Sleep pressure: adenosine + time awake
        time_factor = min(0.3, self.ticks_since_sleep * 0.002)
        self.sleep_pressure = min(1.0, self.adenosine_level * 0.7 + time_factor * 0.3)

        # Cognitive fatigue: sleep pressure degrades performance
        self.cognitive_fatigue = self.sleep_pressure * (1.0 + stress * 0.2)
        self.cognitive_fatigue = min(1.0, self.cognitive_fatigue)

        # High arousal can temporarily mask sleep pressure but not eliminate it
        effective_pressure = max(0.0, self.sleep_pressure - arousal * 0.15)

        self.pressure_history.append(self.sleep_pressure)
        if len(self.pressure_history) > 60:
            self.pressure_history.pop(0)

        avg_pressure = sum(self.pressure_history[-20:]) / min(20, len(self.pressure_history))
        self.chronic_fatigue_ticks = self.chronic_fatigue_ticks + 1 if avg_pressure > 0.65 else max(0, self.chronic_fatigue_ticks - 1)
        was_fatigued = self.chronic_fatigue
        self.chronic_fatigue = self.chronic_fatigue_ticks > 15

        if self.chronic_fatigue and not was_fatigued:
            self.feed_to_memory({
                "event": "sleep_debt_critical",
                "pressure": round(avg_pressure, 3),
                "ticks_since_sleep": self.ticks_since_sleep,
                "note": "Sleep pressure critically high — significant cognitive degradation across all systems"
            })

        return {
            "sleep_pressure": round(self.sleep_pressure, 3),
            "adenosine_level": round(self.adenosine_level, 3),
            "cognitive_fatigue": round(self.cognitive_fatigue, 3),
            "effective_pressure": round(effective_pressure, 3),
            "ticks_since_sleep": self.ticks_since_sleep,
            "chronic_fatigue": self.chronic_fatigue,
        }

    def _overnight(self):
        # Sleep clears adenosine — the primary function
        sleep_quality = max(0.4, 1.0 - self.sleep_pressure * 0.3)
        clearance = sleep_quality * 0.85
        self.adenosine_level = max(0.05, self.adenosine_level - clearance)
        self.sleep_pressure = max(0.1, self.sleep_pressure - clearance * 0.9)
        self.cognitive_fatigue = max(0.0, self.cognitive_fatigue - clearance * 0.8)
        self.ticks_since_sleep = 0
        self.last_sleep_quality = sleep_quality
        self.total_sleep_cycles += 1
        self.chronic_fatigue_ticks = max(0, self.chronic_fatigue_ticks - 10)
        self.chronic_fatigue = self.chronic_fatigue_ticks > 15
        self.pressure_history.clear()
        return {
            "overnight": "adenosine_cleared",
            "sleep_quality": round(sleep_quality, 3),
            "remaining_pressure": round(self.sleep_pressure, 3),
            "total_cycles": self.total_sleep_cycles
        }

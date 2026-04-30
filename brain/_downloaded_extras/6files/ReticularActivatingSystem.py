from brain.base_mechanism import BrainMechanism

class ReticularActivatingSystem(BrainMechanism):
    """
    Reticular activating system — brainstem arousal broadcast, wake/sleep gating.
    The master on/off switch for cortical activation. Without it nothing wakes up.
    activation_level feeds IntralaminarArousalFeed which feeds everything else.
    Goes in brain/foundational/.
    """

    def __init__(self):
        super().__init__("ReticularActivatingSystem")
        self.activation_level = 0.5
        self.wake_drive = 0.6
        self.sleep_pressure_resistance = 0.5
        self.activation_history = []
        self.crash_ticks = 0
        self.overdrive_ticks = 0
        self.chronic_crash = False
        self.chronic_overdrive = False
        self.current_state = "awake"

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        sleep_pressure = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.2)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        autonomic = prior.get("HypothalamicAutonomicRegulator", {}).get("sympathetic_tone", 0.3)

        # Wake drive: stress/threat override sleep pressure
        threat_override = max(fear, pain, stress * 0.5)
        self.wake_drive = max(0.1, min(1.0, 0.5 + threat_override * 0.4 - sleep_pressure * 0.3))

        # Sleep pressure resistance: how hard the RAS fights sleep pressure
        self.sleep_pressure_resistance = self.wake_drive * autonomic

        # Activation level: net arousal broadcast
        self.activation_level = max(0.05, min(1.0, self.wake_drive - sleep_pressure * 0.4 + autonomic * 0.2))

        # State
        if self.activation_level > 0.6:
            self.current_state = "alert"
        elif self.activation_level > 0.35:
            self.current_state = "awake"
        elif self.activation_level > 0.15:
            self.current_state = "drowsy"
        else:
            self.current_state = "near_sleep"

        self.activation_history.append(self.activation_level)
        if len(self.activation_history) > 50:
            self.activation_history.pop(0)

        avg_activation = sum(self.activation_history[-20:]) / min(20, len(self.activation_history))
        self.crash_ticks = self.crash_ticks + 1 if avg_activation < 0.2 else max(0, self.crash_ticks - 1)
        self.overdrive_ticks = self.overdrive_ticks + 1 if avg_activation > 0.82 else max(0, self.overdrive_ticks - 1)

        was_crashed, was_overdrive = self.chronic_crash, self.chronic_overdrive
        self.chronic_crash = self.crash_ticks > 18
        self.chronic_overdrive = self.overdrive_ticks > 18

        if self.chronic_crash and not was_crashed:
            self.feed_to_memory({"event": "ras_crash", "activation": round(avg_activation, 3),
                                  "note": "RAS chronically under-activating — severe fatigue, near-shutdown state"})
        if self.chronic_overdrive and not was_overdrive:
            self.feed_to_memory({"event": "ras_overdrive", "activation": round(avg_activation, 3),
                                  "note": "RAS chronically over-activating — can't wind down, hyperarousal sustained"})

        return {
            "activation_level": round(self.activation_level, 3),
            "wake_drive": round(self.wake_drive, 3),
            "sleep_pressure_resistance": round(self.sleep_pressure_resistance, 3),
            "current_state": self.current_state,
            "chronic_crash": self.chronic_crash,
            "chronic_overdrive": self.chronic_overdrive,
        }

    def _overnight(self):
        self.activation_level = 0.15
        self.wake_drive = 0.2
        self.current_state = "sleeping"
        self.crash_ticks = max(0, self.crash_ticks - 8)
        self.overdrive_ticks = max(0, self.overdrive_ticks - 6)
        self.chronic_crash = self.crash_ticks > 18
        self.chronic_overdrive = self.overdrive_ticks > 18
        self.activation_history.clear()
        return {"overnight": "ras_sleep_state"}

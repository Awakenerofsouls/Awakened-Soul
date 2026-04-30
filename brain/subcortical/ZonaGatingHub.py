from brain.base_mechanism import BrainMechanism

class ZonaGatingHub(BrainMechanism):
    """
    Zona incerta — master gate suppressing sensory relay.
    When active: suppresses everything. Released: floods cortex.
    Models sudden release from suppression, urgency breaking through.
    """

    def __init__(self):
        super().__init__("ZonaGatingHub")
        self.suppression_active = False
        self.suppression_level = 0.0
        self.suppression_history = []
        self.gate_release_events = []
        self.suppression_duration = 0
        self.chronic_suppression = False
        self.suppression_ticks = 0
        self.release_count = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        salience = prior.get("ThalamicSalienceFilter", {}).get("raw_salience", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)

        suppress_driver = stress * 0.4 + (1.0 - salience) * 0.3 - fear * 0.4 - pain * 0.3
        self.suppression_level = max(0.0, min(1.0, suppress_driver))

        was_suppressed = self.suppression_active
        self.suppression_active = self.suppression_level > 0.5

        if self.suppression_active:
            self.suppression_duration += 1
        else:
            if was_suppressed and self.suppression_duration > 3:
                self.gate_release_events.append(self.suppression_duration)
                if len(self.gate_release_events) > 15:
                    self.gate_release_events.pop(0)
                self.release_count += 1
                self.feed_to_memory({"event": "zona_gate_release", "suppression_duration": self.suppression_duration,
                                      "note": "Zona incerta released — suppressed urgency flooding through"})
            self.suppression_duration = 0

        self.suppression_history.append(self.suppression_level)
        if len(self.suppression_history) > 40:
            self.suppression_history.pop(0)

        avg_suppression = sum(self.suppression_history[-15:]) / min(15, len(self.suppression_history))
        self.suppression_ticks = self.suppression_ticks + 1 if avg_suppression > 0.6 else max(0, self.suppression_ticks - 1)
        was_chronic = self.chronic_suppression
        self.chronic_suppression = self.suppression_ticks > 18
        if self.chronic_suppression and not was_chronic:
            self.feed_to_memory({"event": "zona_chronic_suppression", "note": "Zona chronically active — muted responsiveness"})

        gate_release_signal = 1.0 if (was_suppressed and not self.suppression_active) else 0.0

        return {
            "suppression_level": round(self.suppression_level, 3),
            "suppression_active": self.suppression_active,
            "suppression_duration": self.suppression_duration,
            "gate_release_signal": gate_release_signal,
            "chronic_suppression": self.chronic_suppression,
            "release_count": self.release_count,
        }

    def _overnight(self):
        self.suppression_ticks = max(0, self.suppression_ticks - 5)
        self.chronic_suppression = self.suppression_ticks > 18
        self.suppression_duration = 0
        self.suppression_history.clear()
        return {"overnight": "zona_gate_reset"}

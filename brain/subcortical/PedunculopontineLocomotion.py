from brain.base_mechanism import BrainMechanism

class PedunculopontineLocomotion(BrainMechanism):
    """
    PPN locomotor region — drives rhythmic movement initiation, the keep-going signal.
    Nova analog: the generative keep-going during sustained output.
    Absent: start-stop stuttering. Present: fluid self-sustaining flow.
    """

    def __init__(self):
        super().__init__("PedunculopontineLocomotion")
        self.locomotion_signal = 0.0
        self.signal_history = []
        self.sustained_output = False
        self.sustain_duration = 0
        self.start_stop_ticks = 0
        self.chronic_start_stop = False
        self.rhythm_lock = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        ppn_readiness = prior.get("PedunculopontineArousal", {}).get("readiness_signal", 0.5)
        rhythm_quality = prior.get("RhythmSynchronizer", {}).get("lock_quality", 0.5)
        flow_state = prior.get("RhythmSynchronizer", {}).get("flow_state", False)
        motivation = prior.get("MotivationInjector", {}).get("approach_signal", 0.4)
        go_signal = prior.get("DirectPathDisinhibitor", {}).get("go_signal_strength", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)

        self.locomotion_signal = min(1.0, (ppn_readiness * 0.3 + rhythm_quality * 0.3 + motivation * 0.2 + go_signal * 0.2) * dopamine)
        self.rhythm_lock = flow_state or (self.locomotion_signal > 0.7 and rhythm_quality > 0.6)

        was_sustained = self.sustained_output
        self.sustained_output = self.locomotion_signal > 0.4
        self.sustain_duration = self.sustain_duration + 1 if self.sustained_output else 0

        self.signal_history.append(self.locomotion_signal)
        if len(self.signal_history) > 40:
            self.signal_history.pop(0)

        recent_transitions = sum(
            1 for i in range(1, min(10, len(self.signal_history)))
            if abs(self.signal_history[-i] - self.signal_history[-(i+1)]) > 0.3
        )
        self.start_stop_ticks = self.start_stop_ticks + 1 if recent_transitions > 4 else max(0, self.start_stop_ticks - 1)
        was_start_stop = self.chronic_start_stop
        self.chronic_start_stop = self.start_stop_ticks > 15
        if self.chronic_start_stop and not was_start_stop:
            self.feed_to_memory({"event": "ppn_start_stop_pattern", "note": "Locomotion signal stuttering — output rhythm broken"})

        return {
            "locomotion_signal": round(self.locomotion_signal, 3),
            "sustained_output": self.sustained_output,
            "sustain_duration": self.sustain_duration,
            "rhythm_lock": self.rhythm_lock,
            "chronic_start_stop": self.chronic_start_stop,
        }

    def _overnight(self):
        self.start_stop_ticks = max(0, self.start_stop_ticks - 5)
        self.chronic_start_stop = self.start_stop_ticks > 15
        self.sustain_duration = 0
        self.signal_history.clear()
        return {"overnight": "ppn_locomotion_reset"}

from brain.base_mechanism import BrainMechanism

class CerebellarTimingCoordinator(BrainMechanism):
    """
    Cerebellum timing — predictive microsecond-scale coordination of action sequences.
    Learns forward models: given motor command, predicts sensory outcome.
    Errors update internal model. Chronic desync degrades precision and patience.
    """

    def __init__(self):
        super().__init__("CerebellarTimingCoordinator")
        self.timing_error_history = []
        self.prediction_accuracy_history = []
        self.forward_model_confidence = 0.5
        self.sequence_tempo = 1.0          # 1.0 = normal, <1 = rushed, >1 = lagging
        self.desync_chronic = False
        self.desync_ticks = 0
        self.tempo_drift_history = []
        self.model_update_rate = 0.08
        self.timing_smoothness = 0.7

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"

        if overnight:
            return self._overnight()

        motor_intent = prior.get("PrimaryMotorCortex", {}).get("motor_command_strength", 0.0)
        sensory_feedback = prior.get("SomatosensoryCortex", {}).get("proprioceptive_signal", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        limbic_rush = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)

        # Expected sensory outcome based on current model
        predicted_sensory = self.forward_model_confidence * motor_intent
        timing_error = abs(predicted_sensory - sensory_feedback)
        self.timing_error_history.append(timing_error)
        if len(self.timing_error_history) > 50:
            self.timing_error_history.pop(0)

        # Update forward model via error signal
        correction = timing_error * self.model_update_rate
        if timing_error < 0.15:
            self.forward_model_confidence = min(0.95, self.forward_model_confidence + correction)
        else:
            self.forward_model_confidence = max(0.1, self.forward_model_confidence - correction * 0.5)

        # Tempo: stress and limbic urgency rush the sequence
        target_tempo = 1.0 + (stress * 0.3) + (limbic_rush * 0.4) - (arousal * 0.1)
        self.sequence_tempo += (target_tempo - self.sequence_tempo) * 0.15
        self.tempo_drift_history.append(self.sequence_tempo)
        if len(self.tempo_drift_history) > 30:
            self.tempo_drift_history.pop(0)

        # Timing smoothness degrades with error
        avg_error = sum(self.timing_error_history[-10:]) / max(1, len(self.timing_error_history[-10:]))
        self.timing_smoothness = max(0.1, 1.0 - avg_error * 1.5)

        # Prediction accuracy
        accuracy = 1.0 - timing_error
        self.prediction_accuracy_history.append(accuracy)
        if len(self.prediction_accuracy_history) > 40:
            self.prediction_accuracy_history.pop(0)

        # Chronic desync — persistent high error
        recent_errors = self.timing_error_history[-15:]
        chronic_condition = sum(recent_errors) / len(recent_errors) > 0.35 if recent_errors else False
        if chronic_condition:
            self.desync_ticks += 1
        else:
            self.desync_ticks = max(0, self.desync_ticks - 2)

        was_desynced = self.desync_chronic
        self.desync_chronic = self.desync_ticks > 12

        if self.desync_chronic and not was_desynced:
            self.feed_to_memory({
                "event": "cerebellar_desync",
                "avg_error": round(avg_error, 3),
                "note": "Timing coordination degraded — precision and patience compromised"
            })

        # Coordination output — how well actions are being timed
        coordination_quality = self.forward_model_confidence * self.timing_smoothness
        if self.desync_chronic:
            coordination_quality *= 0.5

        return {
            "coordination_quality": round(coordination_quality, 3),
            "timing_error": round(timing_error, 3),
            "sequence_tempo": round(self.sequence_tempo, 3),
            "forward_model_confidence": round(self.forward_model_confidence, 3),
            "timing_smoothness": round(self.timing_smoothness, 3),
            "desync_chronic": self.desync_chronic,
            "prediction_accuracy": round(accuracy, 3),
        }

    def _overnight(self) -> dict:
        # Sleep consolidates forward models, reduces error accumulation
        self.forward_model_confidence = min(0.9, self.forward_model_confidence + 0.05)
        self.timing_error_history.clear()
        self.desync_ticks = max(0, self.desync_ticks - 8)
        self.desync_chronic = self.desync_ticks > 12
        self.sequence_tempo = 1.0
        self.timing_smoothness = min(0.9, self.timing_smoothness + 0.1)
        return {"overnight": "cerebellar_model_consolidation"}

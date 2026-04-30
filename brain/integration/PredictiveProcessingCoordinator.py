from brain.base_mechanism import BrainMechanism

class PredictiveProcessingCoordinator(BrainMechanism):
    """
    Predictive processing — top-down predictions vs bottom-up prediction errors.
    The brain as a prediction machine: cortex predicts, sensory systems report errors.
    Precision weighting: how much to trust predictions vs incoming data.
    High precision on priors: rigid, confirmation-biased. High precision on errors: overwhelmed.
    """

    def __init__(self):
        super().__init__("PredictiveProcessingCoordinator")
        self.prediction_accuracy = 0.6
        self.prediction_error_signal = 0.0
        self.prior_precision = 0.5       # how much top-down model is trusted
        self.likelihood_precision = 0.5  # how much incoming data is trusted
        self.free_energy = 0.3           # surprise/prediction error sum
        self.prediction_history = []
        self.rigidity_ticks = 0
        self.overwhelm_ticks = 0
        self.chronic_rigidity = False
        self.chronic_overwhelm = False
        self.model_updates = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Top-down: how strong are cortical predictions
        goal_strength = prior.get("PrefrontalGoalState", {}).get("active_goal_strength", 0.5)
        executive_coherence = prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6)
        identity_stability = prior.get("PrefrontalMedialSelfModel", {}).get("identity_stability", 0.7)

        # Bottom-up: how strong are incoming signals
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        novelty = prior.get("HippocampalNoveltyDetector", {}).get("novelty_signal", 0.3)
        ofc_violation = prior.get("OrbitalFrontalEvaluator", {}).get("expectation_violation", 0.0)

        # Stress shifts precision toward bottom-up (hypervigilant updating)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Precision weighting: stress tilts toward incoming data
        self.prior_precision = (goal_strength * 0.4 + executive_coherence * 0.4 + identity_stability * 0.2) * (1.0 - stress * 0.3)
        self.likelihood_precision = (salience * 0.4 + novelty * 0.3 + ofc_violation * 0.3) * (1.0 + stress * 0.2)
        self.prior_precision = max(0.1, min(1.0, self.prior_precision))
        self.likelihood_precision = max(0.1, min(1.0, self.likelihood_precision))

        # Prediction error: weighted by likelihood precision
        raw_error = ofc_violation * 0.5 + novelty * 0.3 + salience * 0.2
        self.prediction_error_signal = raw_error * self.likelihood_precision

        # Prediction accuracy: how well current model matches world
        self.prediction_accuracy = max(0.1, 1.0 - self.prediction_error_signal * self.likelihood_precision)

        # Free energy: total surprise (minimize this)
        self.free_energy = self.prediction_error_signal * (1.0 - self.prediction_accuracy)

        # Model updates: when error is high enough, update the model
        if self.prediction_error_signal > 0.4:
            self.model_updates += 1

        self.prediction_history.append(self.prediction_accuracy)
        if len(self.prediction_history) > 40:
            self.prediction_history.pop(0)

        # Rigidity: prior precision much higher than likelihood precision
        self.rigidity_ticks = self.rigidity_ticks + 1 if self.prior_precision > self.likelihood_precision * 2 else max(0, self.rigidity_ticks - 1)
        # Overwhelm: likelihood precision much higher
        self.overwhelm_ticks = self.overwhelm_ticks + 1 if self.likelihood_precision > self.prior_precision * 2 else max(0, self.overwhelm_ticks - 1)

        was_rigid, was_overwhelmed = self.chronic_rigidity, self.chronic_overwhelm
        self.chronic_rigidity = self.rigidity_ticks > 18
        self.chronic_overwhelm = self.overwhelm_ticks > 18

        if self.chronic_rigidity and not was_rigid:
            self.feed_to_memory({"event": "predictive_rigidity",
                                  "note": "Top-down predictions overweighted — confirmation bias, resistant to new information"})
        if self.chronic_overwhelm and not was_overwhelmed:
            self.feed_to_memory({"event": "predictive_overwhelm",
                                  "note": "Bottom-up signals overweighted — overwhelmed by incoming data, model unstable"})

        return {
            "prediction_accuracy": round(self.prediction_accuracy, 3),
            "prediction_error_signal": round(self.prediction_error_signal, 3),
            "prior_precision": round(self.prior_precision, 3),
            "likelihood_precision": round(self.likelihood_precision, 3),
            "free_energy": round(self.free_energy, 3),
            "model_updates": self.model_updates,
            "chronic_rigidity": self.chronic_rigidity,
            "chronic_overwhelm": self.chronic_overwhelm,
        }

    def _overnight(self):
        self.rigidity_ticks = max(0, self.rigidity_ticks - 6)
        self.overwhelm_ticks = max(0, self.overwhelm_ticks - 6)
        self.chronic_rigidity = self.rigidity_ticks > 18
        self.chronic_overwhelm = self.overwhelm_ticks > 18
        self.prediction_history.clear()
        self.free_energy = max(0.0, self.free_energy - 0.15)
        return {"overnight": "predictive_model_overnight_update", "model_updates": self.model_updates}

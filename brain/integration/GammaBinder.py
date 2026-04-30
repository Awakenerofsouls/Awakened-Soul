from brain.base_mechanism import BrainMechanism

class GammaBinder(BrainMechanism):
    """
    Gamma oscillation binding — high-frequency synchrony binding distributed features.
    When gamma fires coherently across areas: unified percept/thought.
    Absent: features processed but never unified — Nova processes parts but not wholes.
    """

    def __init__(self):
        super().__init__("GammaBinder")
        self.binding_strength = 0.5
        self.feature_integration = 0.5
        self.coherent_gamma = False
        self.binding_history = []
        self.binding_failures = 0
        self.chronic_binding_failure = False
        self.failure_ticks = 0
        self.successful_bindings = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        gamma_power = prior.get("CognitiveRhythmSynchronizer", {}).get("gamma_power", 0.3)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        salience = prior.get("SalienceGate", {}).get("gate_output", 0.3)
        semantic_integration = prior.get("AngularGyrus", {}).get("semantic_integration", 0.6)
        multimodal = prior.get("PosteriorParietalCortex", {}).get("multimodal_binding", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Binding strength: gamma + sync + thalamic relay
        self.binding_strength = (gamma_power * 0.3 + sync_quality * 0.3 + thalamic_health * 0.2 + multimodal * 0.2) * (1.0 - stress * 0.2)
        self.binding_strength = max(0.0, min(1.0, self.binding_strength))

        # Coherent gamma: above threshold for actual binding
        self.coherent_gamma = gamma_power > 0.4 and self.binding_strength > 0.45

        # Feature integration: distributed features unified
        self.feature_integration = (semantic_integration * 0.5 + self.binding_strength * 0.5) * salience
        self.feature_integration = max(0.0, min(1.0, self.feature_integration))

        if self.coherent_gamma:
            self.successful_bindings += 1
        elif salience > 0.4:
            self.binding_failures += 1

        self.binding_history.append(self.binding_strength)
        if len(self.binding_history) > 40:
            self.binding_history.pop(0)

        avg_binding = sum(self.binding_history[-15:]) / min(15, len(self.binding_history))
        self.failure_ticks = self.failure_ticks + 1 if avg_binding < 0.2 else max(0, self.failure_ticks - 1)
        was_failing = self.chronic_binding_failure
        self.chronic_binding_failure = self.failure_ticks > 18
        if self.chronic_binding_failure and not was_failing:
            self.feed_to_memory({"event": "gamma_binding_failure",
                                  "note": "Gamma binding chronically weak — processing parts without unified wholes"})

        return {
            "binding_strength": round(self.binding_strength, 3),
            "feature_integration": round(self.feature_integration, 3),
            "coherent_gamma": self.coherent_gamma,
            "successful_bindings": self.successful_bindings,
            "binding_failures": self.binding_failures,
            "chronic_binding_failure": self.chronic_binding_failure,
        }

    def _overnight(self):
        self.failure_ticks = max(0, self.failure_ticks - 6)
        self.chronic_binding_failure = self.failure_ticks > 18
        self.binding_history.clear()
        return {"overnight": "gamma_binding_reset"}

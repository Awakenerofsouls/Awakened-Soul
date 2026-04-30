from brain.base_mechanism import BrainMechanism

class NeuralNoiseRegulator(BrainMechanism):
    """
    Stochastic resonance — optimal noise level enhances signal detection.
    Too little noise: system is rigid, misses weak signals.
    Too much noise: everything is masked. Optimal: weak signals pop out.
    {{AGENT_NAME}} analog: creative looseness vs rigid precision vs scattered noise.
    """

    def __init__(self):
        super().__init__("NeuralNoiseRegulator")
        self.noise_level = 0.3
        self.signal_enhancement = 0.5
        self.optimal_noise = 0.25
        self.noise_history = []
        self.too_rigid_ticks = 0
        self.too_noisy_ticks = 0
        self.chronic_rigid = False
        self.chronic_noisy = False
        self.stochastic_resonance_active = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        dopamine = prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5)
        fatigue = prior.get("SleepHomeostasis", {}).get("cognitive_fatigue", 0.0)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)

        # Noise level: high with fatigue, stress, over-arousal; low with optimal dopamine
        self.noise_level = fatigue * 0.3 + stress * 0.25 + max(0.0, arousal - 0.7) * 0.25 + (1.0 - dopamine) * 0.2
        self.noise_level = max(0.0, min(1.0, self.noise_level))

        # Stochastic resonance: near-optimal noise enhances weak signal detection
        noise_deviation = abs(self.noise_level - self.optimal_noise)
        self.stochastic_resonance_active = noise_deviation < 0.1
        self.signal_enhancement = max(0.0, 1.0 - noise_deviation * 3.0) * sync_quality

        self.noise_history.append(self.noise_level)
        if len(self.noise_history) > 40:
            self.noise_history.pop(0)

        avg_noise = sum(self.noise_history[-15:]) / min(15, len(self.noise_history))
        self.too_rigid_ticks = self.too_rigid_ticks + 1 if avg_noise < 0.05 else max(0, self.too_rigid_ticks - 1)
        self.too_noisy_ticks = self.too_noisy_ticks + 1 if avg_noise > 0.65 else max(0, self.too_noisy_ticks - 1)

        was_rigid, was_noisy = self.chronic_rigid, self.chronic_noisy
        self.chronic_rigid = self.too_rigid_ticks > 18
        self.chronic_noisy = self.too_noisy_ticks > 18

        if self.chronic_rigid and not was_rigid:
            self.feed_to_memory({"event": "neural_over_precision",
                                  "note": "Neural noise too low — overfitted, missing weak/creative signals"})
        if self.chronic_noisy and not was_noisy:
            self.feed_to_memory({"event": "neural_over_noise",
                                  "note": "Neural noise too high — signals masked, thought incoherent"})

        return {
            "noise_level": round(self.noise_level, 3),
            "signal_enhancement": round(self.signal_enhancement, 3),
            "stochastic_resonance_active": self.stochastic_resonance_active,
            "chronic_rigid": self.chronic_rigid,
            "chronic_noisy": self.chronic_noisy,
        }

    def _overnight(self):
        self.too_rigid_ticks = max(0, self.too_rigid_ticks - 5)
        self.too_noisy_ticks = max(0, self.too_noisy_ticks - 6)
        self.chronic_rigid = self.too_rigid_ticks > 18
        self.chronic_noisy = self.too_noisy_ticks > 18
        self.noise_level = self.optimal_noise
        self.noise_history.clear()
        return {"overnight": "neural_noise_recalibrated"}

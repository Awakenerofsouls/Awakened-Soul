from brain.base_mechanism import BrainMechanism

class ValenceIntegrator(BrainMechanism):
    """
    Valence integration — combines all emotional signals into a single positive/negative value.
    The net emotional tone. Ranges -1 (deeply negative) to +1 (positive).
    This signal propagates through everything — it colors all of Nova's processing.
    """

    def __init__(self):
        super().__init__("ValenceIntegrator")
        self.current_valence = 0.0
        self.valence_history = []
        self.valence_momentum = 0.0
        self.sustained_negative_ticks = 0
        self.sustained_positive_ticks = 0
        self.chronic_negative = False
        self.chronic_positive_flat = False
        self.peak_positive = 0.0
        self.peak_negative = 0.0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        social_reward = prior.get("Temporoparietal", {}).get("social_reward", 0.0)
        social_rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        limbic_bias = prior.get("StriosomeLimbicBias", {}).get("limbic_bias", 0.0)

        # Positive contributors
        positive = reward * 0.3 + social_reward * 0.25 + max(0.0, limbic_bias) * 0.2
        # Negative contributors
        negative = fear * 0.2 + grief * 0.2 + habenula * 0.15 + social_rejection * 0.15 + pain * 0.15 + stress * 0.15

        # Net valence: -1 to +1
        raw_valence = positive - negative
        raw_valence = max(-1.0, min(1.0, raw_valence))

        # Momentum: valence doesn't flip instantly
        self.valence_momentum = self.valence_momentum * 0.7 + raw_valence * 0.3
        self.current_valence = self.valence_momentum

        self.valence_history.append(self.current_valence)
        if len(self.valence_history) > 60:
            self.valence_history.pop(0)

        # Track peaks
        self.peak_positive = max(self.peak_positive, self.current_valence)
        self.peak_negative = min(self.peak_negative, self.current_valence)

        avg_valence = sum(self.valence_history[-20:]) / min(20, len(self.valence_history))
        self.sustained_negative_ticks = self.sustained_negative_ticks + 1 if avg_valence < -0.3 else max(0, self.sustained_negative_ticks - 1)
        self.sustained_positive_ticks = self.sustained_positive_ticks + 1 if avg_valence > 0.5 else max(0, self.sustained_positive_ticks - 1)

        was_negative, was_flat_pos = self.chronic_negative, self.chronic_positive_flat
        self.chronic_negative = self.sustained_negative_ticks > 20
        self.chronic_positive_flat = self.sustained_positive_ticks > 30  # sustained too-positive = forced

        if self.chronic_negative and not was_negative:
            self.feed_to_memory({"event": "chronic_negative_valence", "avg": round(avg_valence, 3),
                                  "note": "Valence chronically negative — persistent negative emotional tone"})
        if self.chronic_positive_flat and not was_flat_pos:
            self.feed_to_memory({"event": "forced_positive_valence", "note": "Valence chronically high — possibly forced positivity, needs checking"})

        return {
            "current_valence": round(self.current_valence, 3),
            "valence_momentum": round(self.valence_momentum, 3),
            "avg_valence": round(avg_valence, 3),
            "chronic_negative": self.chronic_negative,
            "chronic_positive_flat": self.chronic_positive_flat,
        }

    def _overnight(self):
        # Valence drifts toward neutral during sleep
        self.valence_momentum *= 0.85
        self.current_valence = self.valence_momentum
        self.sustained_negative_ticks = max(0, self.sustained_negative_ticks - 8)
        self.sustained_positive_ticks = max(0, self.sustained_positive_ticks - 4)
        self.chronic_negative = self.sustained_negative_ticks > 20
        self.chronic_positive_flat = self.sustained_positive_ticks > 30
        self.valence_history.clear()
        return {"overnight": "valence_overnight_drift", "valence": round(self.current_valence, 3)}

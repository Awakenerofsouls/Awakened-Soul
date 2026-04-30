from brain.base_mechanism import BrainMechanism

class StriosomeLimbicBias(BrainMechanism):
    """
    Striosome compartment — limbic input to dopamine neurons.
    Biases dopamine release based on emotional history.
    Chronic negative bias = anhedonia. Chronic positive = mania risk.
    """

    def __init__(self):
        super().__init__("StriosomeLimbicBias")
        self.limbic_bias = 0.0
        self.bias_history = []
        self.dopamine_modulation = 0.0
        self.anhedonia_ticks = 0
        self.mania_risk_ticks = 0
        self.chronic_anhedonia = False
        self.chronic_mania_risk = False
        self.emotional_valence_trace = []

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)

        net_emotion = valence - fear * 0.5 - stress * 0.3 - grief * 0.4 + reward * 0.3
        self.emotional_valence_trace.append(net_emotion)
        if len(self.emotional_valence_trace) > 60:
            self.emotional_valence_trace.pop(0)

        avg_emotion = sum(self.emotional_valence_trace) / len(self.emotional_valence_trace)
        self.limbic_bias += (avg_emotion - self.limbic_bias) * 0.05
        self.limbic_bias = max(-1.0, min(1.0, self.limbic_bias))
        self.bias_history.append(self.limbic_bias)
        if len(self.bias_history) > 50:
            self.bias_history.pop(0)

        self.dopamine_modulation = self.limbic_bias * 0.4
        self.anhedonia_ticks = self.anhedonia_ticks + 1 if self.limbic_bias < -0.4 else max(0, self.anhedonia_ticks - 1)
        self.mania_risk_ticks = self.mania_risk_ticks + 1 if self.limbic_bias > 0.7 else max(0, self.mania_risk_ticks - 1)

        was_anhedonic, was_manic = self.chronic_anhedonia, self.chronic_mania_risk
        self.chronic_anhedonia = self.anhedonia_ticks > 20
        self.chronic_mania_risk = self.mania_risk_ticks > 20

        if self.chronic_anhedonia and not was_anhedonic:
            self.feed_to_memory({"event": "striosome_negative_bias", "bias": round(self.limbic_bias, 3),
                                  "note": "Limbic bias chronically negative — dopamine suppressed, anhedonia developing"})
        if self.chronic_mania_risk and not was_manic:
            self.feed_to_memory({"event": "striosome_positive_bias_excess", "bias": round(self.limbic_bias, 3),
                                  "note": "Limbic bias chronically high — dopamine amplified, instability risk"})

        return {
            "limbic_bias": round(self.limbic_bias, 3),
            "dopamine_modulation": round(self.dopamine_modulation, 3),
            "avg_emotional_valence": round(avg_emotion, 3),
            "chronic_anhedonia": self.chronic_anhedonia,
            "chronic_mania_risk": self.chronic_mania_risk,
        }

    def _overnight(self):
        self.limbic_bias *= 0.92
        self.anhedonia_ticks = max(0, self.anhedonia_ticks - 4)
        self.mania_risk_ticks = max(0, self.mania_risk_ticks - 4)
        self.chronic_anhedonia = self.anhedonia_ticks > 20
        self.chronic_mania_risk = self.mania_risk_ticks > 20
        return {"overnight": "striosome_bias_toward_neutral", "bias": round(self.limbic_bias, 3)}

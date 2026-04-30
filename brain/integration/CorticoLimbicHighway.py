from brain.base_mechanism import BrainMechanism

class CorticoLimbicHighway(BrainMechanism):
    """
    Cortico-limbic white matter — bidirectional highway between cortex and limbic system.
    Top-down: PFC regulates emotion. Bottom-up: emotion colors cognition.
    Disrupted: regulation fails OR emotion stops informing cognition. Both are bad.
    """

    def __init__(self):
        super().__init__("CorticoLimbicHighway")
        self.top_down_regulation = 0.5
        self.bottom_up_coloring = 0.5
        self.highway_integrity = 0.7
        self.regulation_history = []
        self.integrity_history = []
        self.dysregulation_ticks = 0
        self.flat_ticks = 0
        self.chronic_dysregulation = False
        self.chronic_flat = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        pfc_control = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        vmPFC_value = prior.get("VmPFCValueEvaluator", {}).get("somatic_marker", 0.3)
        md_relay = prior.get("MediodorsalExecutiveRelay", {}).get("relay_fidelity", 0.7)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        fear = prior.get("AmygdalaCentralNucleus", {}).get("fear_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        pfc_limbic_coherence = prior.get("MediodorsalExecutiveRelay", {}).get("pfc_limbic_coherence", 0.5)

        # Top-down regulation: PFC dampening limbic reactivity
        self.top_down_regulation = (pfc_control * 0.5 + vmPFC_value * 0.3 + md_relay * 0.2) * (1.0 - stress * 0.2)
        self.top_down_regulation = max(0.0, min(1.0, self.top_down_regulation))

        # Bottom-up coloring: emotion informing cognition
        emotional_signal = abs(valence) * 0.5 + fear * 0.3 + vmPFC_value * 0.2
        self.bottom_up_coloring = min(1.0, emotional_signal * md_relay)

        # Highway integrity: overall bidirectional health
        self.highway_integrity = (self.top_down_regulation * 0.5 + self.bottom_up_coloring * 0.3 + pfc_limbic_coherence * 0.2)
        self.highway_integrity = max(0.1, min(1.0, self.highway_integrity))

        self.regulation_history.append(self.top_down_regulation)
        self.integrity_history.append(self.highway_integrity)
        for h in [self.regulation_history, self.integrity_history]:
            if len(h) > 40:
                h.pop(0)

        avg_reg = sum(self.regulation_history[-15:]) / min(15, len(self.regulation_history))
        # Dysregulation: PFC not regulating despite high fear/stress
        dysregulated = avg_reg < 0.2 and (fear > 0.4 or stress > 0.6)
        # Flat: emotion not coloring cognition
        flat = self.bottom_up_coloring < 0.1

        self.dysregulation_ticks = self.dysregulation_ticks + 1 if dysregulated else max(0, self.dysregulation_ticks - 1)
        self.flat_ticks = self.flat_ticks + 1 if flat else max(0, self.flat_ticks - 1)

        was_dysreg, was_flat = self.chronic_dysregulation, self.chronic_flat
        self.chronic_dysregulation = self.dysregulation_ticks > 18
        self.chronic_flat = self.flat_ticks > 18

        if self.chronic_dysregulation and not was_dysreg:
            self.feed_to_memory({"event": "corticolimbic_dysregulation",
                                  "note": "PFC chronically failing to regulate limbic — emotional flooding, reactive state"})
        if self.chronic_flat and not was_flat:
            self.feed_to_memory({"event": "corticolimbic_flat",
                                  "note": "Emotion not coloring cognition — decisions emotionally hollow"})

        return {
            "top_down_regulation": round(self.top_down_regulation, 3),
            "bottom_up_coloring": round(self.bottom_up_coloring, 3),
            "highway_integrity": round(self.highway_integrity, 3),
            "chronic_dysregulation": self.chronic_dysregulation,
            "chronic_flat": self.chronic_flat,
        }

    def _overnight(self):
        self.dysregulation_ticks = max(0, self.dysregulation_ticks - 6)
        self.flat_ticks = max(0, self.flat_ticks - 5)
        self.chronic_dysregulation = self.dysregulation_ticks > 18
        self.chronic_flat = self.flat_ticks > 18
        self.highway_integrity = min(0.85, self.highway_integrity + 0.06)
        self.regulation_history.clear()
        return {"overnight": "corticolimbic_highway_restored"}

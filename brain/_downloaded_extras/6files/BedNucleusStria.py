from brain.base_mechanism import BrainMechanism

class BedNucleusStria(BrainMechanism):
    """
    Bed nucleus of the stria terminalis — sustained anxiety, anticipatory dread.
    Unlike amygdala (fast fear to specific threat), BNST is slow, diffuse, persistent.
    The mechanism of dread, worry, existential unease. Can run for hours without a trigger.
    Goes in brain/limbic/.
    """

    def __init__(self):
        super().__init__("BedNucleusStria")
        self.sustained_dread = 0.0
        self.anticipatory_anxiety = 0.0
        self.dread_accumulation = 0.0
        self.dread_history = []
        self.anxiety_history = []
        self.chronic_dread_ticks = 0
        self.chronic_dread = False
        self.dread_source = "none"
        self.relief_events = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        fear_output = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        cea_fear = prior.get("AmygdalaCentralNucleus", {}).get("fear_output", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        habenula = prior.get("HabenulaLateralAversion", {}).get("aversion_accumulation", 0.0)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        pfc_regulation = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)
        reward = prior.get("VentralTegmentalDopamine", {}).get("phasic_burst", 0.0)

        # BNST is fed by chronic stress, habenula aversion, and sustained negative states
        dread_input = stress * 0.35 + habenula * 0.3 + max(0.0, -valence) * 0.2 + max(fear_output, cea_fear) * 0.15

        # Dread accumulates slowly and dissipates slowly
        if dread_input > 0.2:
            self.dread_accumulation = min(1.0, self.dread_accumulation + dread_input * 0.04)
        else:
            self.dread_accumulation = max(0.0, self.dread_accumulation - 0.015)

        # PFC can attenuate somewhat but BNST is hard to regulate
        self.sustained_dread = max(0.0, self.dread_accumulation - pfc_regulation * 0.1)

        # Anticipatory anxiety: future-oriented component
        self.anticipatory_anxiety = min(1.0, self.sustained_dread * 0.8 + stress * 0.2)

        # Dread source tracking
        if habenula > 0.4:
            self.dread_source = "disappointment"
        elif stress > 0.6:
            self.dread_source = "overload"
        elif max(fear_output, cea_fear) > 0.4:
            self.dread_source = "threat"
        elif valence < -0.4:
            self.dread_source = "negative_state"
        else:
            self.dread_source = "ambient"

        # Relief: reward signal can temporarily suppress dread
        if reward > 0.4:
            self.dread_accumulation = max(0.0, self.dread_accumulation - reward * 0.08)
            self.relief_events += 1

        self.dread_history.append(self.sustained_dread)
        self.anxiety_history.append(self.anticipatory_anxiety)
        for h in [self.dread_history, self.anxiety_history]:
            if len(h) > 60:
                h.pop(0)

        avg_dread = sum(self.dread_history[-20:]) / min(20, len(self.dread_history))
        self.chronic_dread_ticks = self.chronic_dread_ticks + 1 if avg_dread > 0.45 else max(0, self.chronic_dread_ticks - 1)
        was_chronic = self.chronic_dread
        self.chronic_dread = self.chronic_dread_ticks > 20

        if self.chronic_dread and not was_chronic:
            self.feed_to_memory({
                "event": "bnst_chronic_dread",
                "dread": round(avg_dread, 3),
                "source": self.dread_source,
                "note": f"BNST sustained dread chronic — persistent background anxiety, source: {self.dread_source}"
            })

        return {
            "sustained_dread": round(self.sustained_dread, 3),
            "anticipatory_anxiety": round(self.anticipatory_anxiety, 3),
            "dread_accumulation": round(self.dread_accumulation, 3),
            "dread_source": self.dread_source,
            "relief_events": self.relief_events,
            "chronic_dread": self.chronic_dread,
        }

    def _overnight(self):
        # Sleep reduces BNST tone significantly — key mechanism of anxiety recovery
        self.dread_accumulation = max(0.0, self.dread_accumulation - 0.25)
        self.sustained_dread = max(0.0, self.sustained_dread - 0.2)
        self.anticipatory_anxiety = max(0.0, self.anticipatory_anxiety - 0.15)
        self.chronic_dread_ticks = max(0, self.chronic_dread_ticks - 8)
        self.chronic_dread = self.chronic_dread_ticks > 20
        self.dread_history.clear()
        return {
            "overnight": "bnst_dread_processing",
            "remaining_dread": round(self.dread_accumulation, 3)
        }

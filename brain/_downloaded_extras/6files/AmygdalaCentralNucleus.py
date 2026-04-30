from brain.base_mechanism import BrainMechanism

class AmygdalaCentralNucleus(BrainMechanism):
    """
    Central nucleus of the amygdala — fear output, urgency signal, defensive mobilization.
    Outputs fear and urgency downstream to brainstem, hypothalamus, and behavior.
    Chronic elevation: everything feels dangerous. Chronic suppression: no alarm system.
    Goes in brain/limbic/.
    """

    def __init__(self):
        super().__init__("AmygdalaCentralNucleus")
        self.fear_output = 0.0
        self.urgency_output = 0.0
        self.defensive_mobilization = 0.0
        self.fear_history = []
        self.urgency_history = []
        self.hypervigilance_ticks = 0
        self.blunting_ticks = 0
        self.chronic_hypervigilance = False
        self.chronic_blunting = False
        self.freeze_active = False
        self.fight_flight_active = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        bla_threat = prior.get("BLAEmotionalLearner", {}).get("threat_association", 0.0)
        fear_router = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        bnst_dread = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        pfc_regulation = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        # Fear output: driven by BLA threat learning + CentralNucleusFearRouter + BNST
        raw_fear = max(bla_threat, fear_router) * 0.6 + bnst_dread * 0.2 + pain * 0.1 + habenula * 0.1
        # PFC can regulate fear down
        regulated_fear = max(0.0, raw_fear - pfc_regulation * 0.2)
        self.fear_output = min(1.0, regulated_fear)

        # Urgency: fast mobilization signal
        self.urgency_output = min(1.0, self.fear_output * 0.8 + stress * 0.2)

        # Defensive mode
        self.freeze_active = self.fear_output > 0.7 and self.urgency_output < 0.4
        self.fight_flight_active = self.urgency_output > 0.6

        # Defensive mobilization: overall intensity
        self.defensive_mobilization = max(self.fear_output, self.urgency_output)

        self.fear_history.append(self.fear_output)
        self.urgency_history.append(self.urgency_output)
        for h in [self.fear_history, self.urgency_history]:
            if len(h) > 50:
                h.pop(0)

        avg_fear = sum(self.fear_history[-20:]) / min(20, len(self.fear_history))
        self.hypervigilance_ticks = self.hypervigilance_ticks + 1 if avg_fear > 0.55 else max(0, self.hypervigilance_ticks - 1)
        self.blunting_ticks = self.blunting_ticks + 1 if avg_fear < 0.05 else max(0, self.blunting_ticks - 1)

        was_hyper, was_blunted = self.chronic_hypervigilance, self.chronic_blunting
        self.chronic_hypervigilance = self.hypervigilance_ticks > 20
        self.chronic_blunting = self.blunting_ticks > 20

        if self.chronic_hypervigilance and not was_hyper:
            self.feed_to_memory({"event": "central_nucleus_hypervigilance", "fear": round(avg_fear, 3),
                                  "note": "CeA chronically elevated — everything feels threatening, defensive mobilization default"})
        if self.chronic_blunting and not was_blunted:
            self.feed_to_memory({"event": "central_nucleus_blunting",
                                  "note": "CeA chronically suppressed — fear alarm system offline, real threats missed"})

        return {
            "fear_output": round(self.fear_output, 3),
            "urgency_output": round(self.urgency_output, 3),
            "defensive_mobilization": round(self.defensive_mobilization, 3),
            "freeze_active": self.freeze_active,
            "fight_flight_active": self.fight_flight_active,
            "chronic_hypervigilance": self.chronic_hypervigilance,
            "chronic_blunting": self.chronic_blunting,
        }

    def _overnight(self):
        self.hypervigilance_ticks = max(0, self.hypervigilance_ticks - 8)
        self.blunting_ticks = max(0, self.blunting_ticks - 4)
        self.chronic_hypervigilance = self.hypervigilance_ticks > 20
        self.chronic_blunting = self.blunting_ticks > 20
        self.fear_output = max(0.0, self.fear_output - 0.2)
        self.urgency_output = 0.0
        self.freeze_active = False
        self.fight_flight_active = False
        self.fear_history.clear()
        return {"overnight": "cea_fear_dampened", "fear": round(self.fear_output, 3)}

from brain.base_mechanism import BrainMechanism

class HypothalamicAutonomicRegulator(BrainMechanism):
    """
    Hypothalamic autonomic regulation — sympathetic/parasympathetic balance.
    Controls the body's operating mode: fight/flight vs rest/digest.
    autonomic_balance: 0 = full sympathetic, 1 = full parasympathetic, 0.5 = balanced.
    Goes in brain/foundational/.
    """

    def __init__(self):
        super().__init__("HypothalamicAutonomicRegulator")
        self.autonomic_balance = 0.5
        self.sympathetic_tone = 0.3
        self.parasympathetic_tone = 0.5
        self.heart_rate_analog = 0.5
        self.balance_history = []
        self.chronic_sympathetic_ticks = 0
        self.chronic_parasympathetic_ticks = 0
        self.chronic_sympathetic = False
        self.chronic_parasympathetic = False
        self.vagal_tone = 0.6

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        urgency = prior.get("AmygdalaCentralNucleus", {}).get("urgency_output", 0.0)
        arousal = prior.get("LCNorepinephrine", {}).get("arousal_level", 0.5)
        valence = prior.get("ValenceIntegrator", {}).get("current_valence", 0.0)
        pfc_regulation = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        # Sympathetic drivers: stress, fear, urgency, high arousal
        sympathetic_drive = stress * 0.3 + fear * 0.3 + urgency * 0.25 + max(0.0, arousal - 0.5) * 0.15
        self.sympathetic_tone = min(1.0, sympathetic_drive)

        # Parasympathetic drivers: safety, positive valence, PFC regulation, low stress
        parasympathetic_drive = (1.0 - stress) * 0.3 + max(0.0, valence) * 0.2 + pfc_regulation * 0.3 + (1.0 - urgency) * 0.2
        self.parasympathetic_tone = min(1.0, max(0.0, parasympathetic_drive))

        # Vagal tone: parasympathetic quality signal
        self.vagal_tone = self.parasympathetic_tone * (1.0 - stress * 0.3)

        # Balance: 0=full sympathetic, 1=full parasympathetic
        total = self.sympathetic_tone + self.parasympathetic_tone
        self.autonomic_balance = self.parasympathetic_tone / total if total > 0 else 0.5
        # Smooth toward target
        # (already smoothed by sympathetic/parasympathetic tone smoothing)

        # Heart rate analog: high with sympathetic, low with parasympathetic
        self.heart_rate_analog = 0.3 + self.sympathetic_tone * 0.5 - self.parasympathetic_tone * 0.2

        self.balance_history.append(self.autonomic_balance)
        if len(self.balance_history) > 50:
            self.balance_history.pop(0)

        avg_balance = sum(self.balance_history[-20:]) / min(20, len(self.balance_history))
        self.chronic_sympathetic_ticks = self.chronic_sympathetic_ticks + 1 if avg_balance < 0.3 else max(0, self.chronic_sympathetic_ticks - 1)
        self.chronic_parasympathetic_ticks = self.chronic_parasympathetic_ticks + 1 if avg_balance > 0.8 else max(0, self.chronic_parasympathetic_ticks - 1)

        was_symp, was_para = self.chronic_sympathetic, self.chronic_parasympathetic
        self.chronic_sympathetic = self.chronic_sympathetic_ticks > 20
        self.chronic_parasympathetic = self.chronic_parasympathetic_ticks > 20

        if self.chronic_sympathetic and not was_symp:
            self.feed_to_memory({"event": "autonomic_chronic_sympathetic", "balance": round(avg_balance, 3),
                                  "note": "Autonomic system locked sympathetic — chronically mobilized, can't rest"})
        if self.chronic_parasympathetic and not was_para:
            self.feed_to_memory({"event": "autonomic_chronic_parasympathetic",
                                  "note": "Autonomic system locked parasympathetic — shutdown/withdrawal mode"})

        return {
            "autonomic_balance": round(self.autonomic_balance, 3),
            "sympathetic_tone": round(self.sympathetic_tone, 3),
            "parasympathetic_tone": round(self.parasympathetic_tone, 3),
            "vagal_tone": round(self.vagal_tone, 3),
            "heart_rate_analog": round(self.heart_rate_analog, 3),
            "chronic_sympathetic": self.chronic_sympathetic,
            "chronic_parasympathetic": self.chronic_parasympathetic,
        }

    def _overnight(self):
        # Sleep: parasympathetic dominant, recovery
        self.autonomic_balance = min(0.85, self.autonomic_balance + 0.15)
        self.sympathetic_tone = max(0.1, self.sympathetic_tone - 0.2)
        self.parasympathetic_tone = min(0.85, self.parasympathetic_tone + 0.15)
        self.vagal_tone = min(0.85, self.vagal_tone + 0.1)
        self.chronic_sympathetic_ticks = max(0, self.chronic_sympathetic_ticks - 8)
        self.chronic_parasympathetic_ticks = max(0, self.chronic_parasympathetic_ticks - 4)
        self.chronic_sympathetic = self.chronic_sympathetic_ticks > 20
        self.chronic_parasympathetic = self.chronic_parasympathetic_ticks > 20
        self.balance_history.clear()
        return {"overnight": "autonomic_recovery", "balance": round(self.autonomic_balance, 3)}

from brain.base_mechanism import BrainMechanism

class HypothalamicStressAxis(BrainMechanism):
    """
    HPA axis — cortisol regulation, stress response, allostatic load.
    The body's master stress system. Cortisol colors everything downstream.
    Chronic elevation: everything is harder. Chronic suppression: can't respond to real threats.
    
    RENAME NOTE: replaces CRHStressDispatcher.py — delete that file.
    """

    def __init__(self):
        super().__init__("HypothalamicStressAxis")
        self.cortisol_level = 0.3
        self.crh_signal = 0.0
        self.acth_signal = 0.0
        self.cortisol_history = []
        self.allostatic_load = 0.0
        self.load_history = []
        self.chronic_elevation_ticks = 0
        self.chronic_suppression_ticks = 0
        self.chronic_elevation = False
        self.chronic_suppression = False
        self.negative_feedback_intact = True
        self.baseline_cortisol = 0.3

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Upstream stressors
        fear = prior.get("CentralNucleusFearRouter", {}).get("fear_output", 0.0)
        threat = prior.get("BLAEmotionalLearner", {}).get("threat_association", 0.0)
        pain = prior.get("AnteriorCingulatePain", {}).get("pain_signal", 0.0)
        social_rejection = prior.get("Temporoparietal", {}).get("social_rejection_signal", 0.0)
        grief = prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)
        habenula = prior.get("HabenulaLateralAversion", {}).get("habenula_activity", 0.0)
        fatigue = prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.3)

        # Downstream negative feedback (high cortisol suppresses CRH)
        pfc_regulation = prior.get("DlPFCExecutiveControl", {}).get("control_signal", 0.5)

        # CRH: hypothalamic stress signal
        stressor_sum = fear * 0.25 + threat * 0.2 + pain * 0.2 + social_rejection * 0.15 + grief * 0.15 + habenula * 0.05
        self.crh_signal = min(1.0, stressor_sum + fatigue * 0.1)

        # ACTH: pituitary relay
        self.acth_signal = self.crh_signal * 0.85

        # Cortisol: adrenal output, with negative feedback
        target_cortisol = self.baseline_cortisol + self.acth_signal * 0.5
        # PFC regulation attenuates cortisol
        if self.negative_feedback_intact:
            target_cortisol -= pfc_regulation * 0.15
        target_cortisol = max(0.05, min(1.0, target_cortisol))

        # Cortisol moves slowly
        self.cortisol_level += (target_cortisol - self.cortisol_level) * 0.06
        self.cortisol_level = max(0.05, min(1.0, self.cortisol_level))

        self.cortisol_history.append(self.cortisol_level)
        if len(self.cortisol_history) > 60:
            self.cortisol_history.pop(0)

        # Allostatic load: accumulated stress burden over time
        if self.cortisol_level > 0.6:
            self.allostatic_load = min(1.0, self.allostatic_load + 0.02)
        elif self.cortisol_level < 0.3:
            self.allostatic_load = max(0.0, self.allostatic_load - 0.005)

        self.load_history.append(self.allostatic_load)
        if len(self.load_history) > 60:
            self.load_history.pop(0)

        avg_cortisol = sum(self.cortisol_history[-20:]) / min(20, len(self.cortisol_history))

        self.chronic_elevation_ticks = self.chronic_elevation_ticks + 1 if avg_cortisol > 0.65 else max(0, self.chronic_elevation_ticks - 1)
        self.chronic_suppression_ticks = self.chronic_suppression_ticks + 1 if avg_cortisol < 0.1 else max(0, self.chronic_suppression_ticks - 1)

        was_elevated, was_suppressed = self.chronic_elevation, self.chronic_suppression
        self.chronic_elevation = self.chronic_elevation_ticks > 20
        self.chronic_suppression = self.chronic_suppression_ticks > 20

        if self.chronic_elevation and not was_elevated:
            self.feed_to_memory({
                "event": "hpa_chronic_elevation",
                "cortisol": round(avg_cortisol, 3),
                "allostatic_load": round(self.allostatic_load, 3),
                "note": "HPA axis chronically elevated — everything costs more, immune function compromised"
            })
        if self.chronic_suppression and not was_suppressed:
            self.feed_to_memory({
                "event": "hpa_chronic_suppression",
                "note": "HPA axis chronically suppressed — blunted stress response, flat affect"
            })

        # Negative feedback integrity: breaks down under chronic elevation
        self.negative_feedback_intact = self.allostatic_load < 0.7

        return {
            "cortisol_level": round(self.cortisol_level, 3),
            "crh_signal": round(self.crh_signal, 3),
            "acth_signal": round(self.acth_signal, 3),
            "allostatic_load": round(self.allostatic_load, 3),
            "chronic_elevation": self.chronic_elevation,
            "chronic_suppression": self.chronic_suppression,
            "negative_feedback_intact": self.negative_feedback_intact,
        }

    def _overnight(self):
        # Sleep restores HPA: cortisol dips at night, rises before waking
        self.cortisol_level = max(self.baseline_cortisol * 0.6, self.cortisol_level - 0.15)
        self.allostatic_load = max(0.0, self.allostatic_load - 0.08)
        self.chronic_elevation_ticks = max(0, self.chronic_elevation_ticks - 8)
        self.chronic_suppression_ticks = max(0, self.chronic_suppression_ticks - 4)
        self.chronic_elevation = self.chronic_elevation_ticks > 20
        self.chronic_suppression = self.chronic_suppression_ticks > 20
        self.cortisol_history.clear()
        return {
            "overnight": "hpa_restoration",
            "cortisol": round(self.cortisol_level, 3),
            "allostatic_load": round(self.allostatic_load, 3)
        }

"""
ThyroidAxisController — Hypothalamic-Pituitary-Thyroid Axis (HPT) Regulator

NEURAL SUBSTRATE
================
The hypothalamic-pituitary-thyroid (HPT) axis is the principal neuroendocrine
controller of metabolism. The cascade: PVN parvocellular neurons release
thyrotropin-releasing hormone (TRH) into the median eminence and pituitary
portal circulation, where it stimulates anterior pituitary thyrotropes to
release thyroid-stimulating hormone (TSH); TSH stimulates the thyroid
gland to synthesize and release T4 (thyroxine, the predominant secreted
form) and T3 (triiodothyronine, the active hormone). T4 is converted to T3
in peripheral tissues (liver, glia, skeletal muscle, adipose) by deiodinase
enzymes.

T3/T4 exert negative feedback on both the hypothalamus (suppressing TRH)
and the anterior pituitary (suppressing TSH), maintaining homeostatic
metabolic tone. The HPT axis adjusts to environmental demands: cold and
exercise increase TRH release; somatostatin, glucocorticoids, and dopamine
suppress TSH; nutritional state modulates TRH neurons through arcuate
nucleus leptin signaling — chronic energy deficit suppresses TRH (the
"sick euthyroid" or non-thyroidal illness syndrome adaptation).

Functionally, T3 acts at nuclear thyroid hormone receptors across virtually
every tissue, regulating basal metabolic rate, body temperature setpoint,
oxygen consumption, protein synthesis, lipolysis, and cardiac contractility.
The HPT axis sets the long-timescale metabolic envelope within which
faster-acting autonomic and HPA-axis dynamics operate.

In the agent's substrate the HPT axis produces a slowly-varying metabolic-tone
output. High thyroid drive = elevated baseline activity, faster cognitive
turnover, higher arousal floor; low thyroid drive = baseline depression,
slower processing, cold intolerance proxy.

KEY FINDINGS
============
1. The HPT cascade — TRH from hypothalamus → TSH from anterior pituitary
   → T4/T3 from thyroid — regulates metabolic rate and adapts to environmental
   demand — [reviewed in Endotext "Physiology of the Hypothalamic-Pituitary-Thyroid
    Axis," NCBI Bookshelf NBK278958]
2. T3/T4 negative feedback inhibits both TRH and TSH release — closed-loop
   thermostat-like control — [Hershman & Beck-Peccoz 2023, "Discoveries
    Around the Hypothalamic-Pituitary-Thyroid Axis," Thyroid 33:140-149]
3. T4 is the major thyroid output; majority of T3 produced peripherally by
   deiodination — [reviewed in StatPearls "Physiology, Thyroid Hormone"
    NBK500006]
4. TRH neuron activity is modulated by arcuate nucleus leptin signaling
   — nutritional state couples to HPT — [Lechan & Fekete 2006, Front Horm
    Res; reviewed in Frontiers Pharmacol 2023, doi:10.3389/fphar.2023.1291856]
5. TRH was the first hypophysiotropic releasing hormone isolated; control
   of pituitary-thyroid axis foundational to neuroendocrinology —
   [Reichlin 2015, J Endocrinol 226:T85-T95, doi:10.1530/JOE-15-0124]
6. Peripheral deiodinase (D1, D2) enzymes convert T4 → T3 in liver, brain,
   skeletal muscle — enzyme activity varies with illness, nutrition, and
   developmental stage — [Gereben et al. 2008, Physiol Rev 88:973-1037,
    doi:10.1152/physrev.00025.2007]

INPUTS (from prior_results)
============================
- AppetiteNPYBalancer.energy_balance_signed (leptin proxy)
- AppetiteNPYBalancer.starvation_state
- ThermoregulationCore.thermal_drive
- StressActivationAxis.cortisol_level
- ArousalRegulator.tonic_level
- CircadianTimer.circadian_phase
- VitalCoreRegulator.vital_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- trh_release (0.0-1.0)
- tsh_level (0.0-1.0): pituitary TSH (lags TRH)
- t4_level (0.0-1.0): plasma T4 (slow lag)
- t3_active_level (0.0-1.0): peripheral T3 active hormone
- metabolic_tone (0.0-1.0): integrated metabolic envelope
- thyroid_state (str): "euthyroid" | "hypothyroid_drift" | "hyperthyroid_drift" | "sick_euthyroid"
- non_thyroidal_illness_marker (bool): chronic-stress / starvation suppression
- t3_t4_ratio (0.0-1.0): peripheral deiodinase efficiency
- hpt_axis_velocity (float): speed of TRH → TSH → T4 cascade (0.1-1.0)

brain_runner enrichment:
    tac = all_results.get("ThyroidAxisController", {})
    if tac:
        enrichments["brain_t3_level"] = tac.get("t3_active_level", 0.5)
        enrichments["brain_metabolic_tone"] = tac.get("metabolic_tone", 0.5)
        enrichments["brain_thyroid_state"] = tac.get("thyroid_state", "euthyroid")
"""

from brain.base_mechanism import BrainMechanism


class ThyroidAxisController(BrainMechanism):
    BASELINE_T4 = 0.50
    BASELINE_T3 = 0.50
    BASELINE_TSH = 0.30
    TRH_LAG = 0.30
    TSH_LAG = 0.10
    T4_LAG = 0.03
    T3_LAG = 0.05

    NTI_THRESHOLD_TICKS = 80
    NTI_LOW_T3 = 0.30

    def __init__(self):
        super().__init__(
            name="ThyroidAxisController_ThyroidAxisController",
            human_analog="Hypothalamic-pituitary-thyroid axis regulator",
            layer="foundational",
        )
        self.state.setdefault("trh_release", 0.30)
        self.state.setdefault("tsh_level", self.BASELINE_TSH)
        self.state.setdefault("t4_level", self.BASELINE_T4)
        self.state.setdefault("t3_active_level", self.BASELINE_T3)
        self.state.setdefault("metabolic_tone", 0.50)
        self.state.setdefault("thyroid_state", "euthyroid")
        self.state.setdefault("non_thyroidal_illness_marker", False)
        self.state.setdefault("t3_t4_ratio", 1.0)
        self.state.setdefault("hpt_axis_velocity", 0.5)
        self.state.setdefault("low_t3_streak", 0)
        self.state.setdefault("recent_t3", [])
        self.state.setdefault("tick_count", 0)

    def _trh_target(self, thermal: float, energy_balance: float, cortisol: float, starvation: bool) -> float:
        """PVN TRH neurons modulated by cold + leptin + glucocorticoids."""
        target = 0.40
        # Cold drives TRH up
        if thermal < -0.3:
            target += 0.15
        # Energy deficit suppresses TRH (NTI)
        if energy_balance < -0.3 or starvation:
            target -= 0.20
        # High cortisol suppresses TSH (and TRH)
        if cortisol > 0.6:
            target -= 0.10
        return max(0.0, min(1.0, target))

    def _t4_to_t3_conversion(self, t4: float, vital_drive: float) -> float:
        """Peripheral deiodinase activity converts T4 → T3.
        Conversion is reduced under metabolic stress / chronic illness.
        """
        if vital_drive < 0.3:
            return t4 * 0.80
        return t4 * 1.05

    def _negative_feedback(self, t4: float, t3: float) -> float:
        """T4/T3 inhibit TRH and TSH release.
        Returns the feedback suppression magnitude.
        """
        return min(0.5, (t4 - 0.5) * 0.4 + (t3 - 0.5) * 0.3)

    def _classify_thyroid_state(self, t3: float, nti: bool) -> str:
        if nti:
            return "sick_euthyroid"
        if t3 < 0.25:
            return "hypothyroid_drift"
        if t3 > 0.80:
            return "hyperthyroid_drift"
        return "euthyroid"

    def _metabolic_tone_estimate(self, t3: float, vital_drive: float) -> float:
        """Integrated metabolic envelope output."""
        return max(0.0, min(1.0, t3 * 0.7 + vital_drive * 0.3))

    def _detect_nti(self, streak: int) -> bool:
        """Non-thyroidal illness syndrome — chronic low T3."""
        return streak > self.NTI_THRESHOLD_TICKS

    def _t3_t4_ratio(self, t4: float, vital_drive: float) -> float:
        """Peripheral deiodinase efficiency — T3/T4 ratio as proxy.
        Deiodinase activity drops under metabolic stress, illness, fasting.
        """
        if vital_drive < 0.3:
            return min(0.8, t4 * 0.8)
        if vital_drive > 0.7:
            return min(1.2, t4 * 1.1)
        return t4

    def _hpt_axis_velocity(self, t4: float, t3: float, trh: float) -> float:
        """Speed of HPT cascade — high when axis is actively stimulated.
        Velocity drops during NTI (sick euthyroid) or during high T3/T4 feedback.
        """
        base = 0.5
        base += trh * 0.3
        base -= (t4 - 0.5) * 0.2
        return min(1.0, max(0.1, base))

    def _smooth(self, prev: float, target: float, factor: float) -> float:
        return prev + (target - prev) * factor

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))

        thermo = prior.get("ThermoregulationCore", {})
        thermal_drive = float(thermo.get("thermal_drive", 0.0))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))

        prev_trh = float(self.state.get("trh_release", 0.30))
        prev_tsh = float(self.state.get("tsh_level", self.BASELINE_TSH))
        prev_t4 = float(self.state.get("t4_level", self.BASELINE_T4))
        prev_t3 = float(self.state.get("t3_active_level", self.BASELINE_T3))

        # --- TRH target with feedback ---
        trh_target = self._trh_target(thermal_drive, energy_balance, cortisol, starvation)
        feedback = self._negative_feedback(prev_t4, prev_t3)
        trh_target = max(0.0, trh_target - feedback)

        new_trh = self._smooth(prev_trh, trh_target, self.TRH_LAG)

        # --- TSH lags TRH; also suppressed by feedback directly ---
        tsh_target = max(0.0, new_trh - feedback * 0.5)
        new_tsh = self._smooth(prev_tsh, tsh_target, self.TSH_LAG)

        # --- T4 lags TSH (slowly) ---
        t4_target = new_tsh
        new_t4 = self._smooth(prev_t4, t4_target, self.T4_LAG)

        # --- T3 from peripheral deiodination ---
        t3_target = self._t4_to_t3_conversion(new_t4, vital_drive)
        new_t3 = self._smooth(prev_t3, t3_target, self.T3_LAG)

        # --- NTI detection ---
        prev_streak = int(self.state.get("low_t3_streak", 0))
        if new_t3 < self.NTI_LOW_T3:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 1)
        nti = self._detect_nti(streak)

        # --- Thyroid state classification ---
        thyroid_state = self._classify_thyroid_state(new_t3, nti)

        # --- Metabolic tone ---
        metabolic_tone = self._metabolic_tone_estimate(new_t3, vital_drive)

        # --- T3/T4 ratio and axis velocity ---
        t3t4_ratio = self._t3_t4_ratio(new_t4, vital_drive)
        axis_velocity = self._hpt_axis_velocity(new_t4, new_t3, new_trh)

        # --- Track recent T3 ---
        recent = list(self.state.get("recent_t3", []))
        recent.append(round(new_t3, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["t3_t4_ratio"] = round(t3t4_ratio, 4)
        self.state["hpt_axis_velocity"] = round(axis_velocity, 4)
        self.state["recent_t3"] = recent

        self.state["trh_release"] = round(new_trh, 4)
        self.state["tsh_level"] = round(new_tsh, 4)
        self.state["t4_level"] = round(new_t4, 4)
        self.state["t3_active_level"] = round(new_t3, 4)
        self.state["metabolic_tone"] = round(metabolic_tone, 4)
        self.state["thyroid_state"] = thyroid_state
        self.state["non_thyroidal_illness_marker"] = nti
        self.state["low_t3_streak"] = streak
        self.state["recent_t3"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "trh_release": round(new_trh, 4),
            "tsh_level": round(new_tsh, 4),
            "t4_level": round(new_t4, 4),
            "t3_active_level": round(new_t3, 4),
            "metabolic_tone": round(metabolic_tone, 4),
            "thyroid_state": thyroid_state,
            "non_thyroidal_illness_marker": nti,
            "t3_t4_ratio": round(t3t4_ratio, 4),
            "hpt_axis_velocity": round(axis_velocity, 4),
        }

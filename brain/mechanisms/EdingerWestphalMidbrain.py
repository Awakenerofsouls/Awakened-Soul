"""
EdingerWestphalMidbrain — Edinger-Westphal Nucleus (Pupillary + Centrally Projecting)

NEURAL SUBSTRATE
================
The Edinger-Westphal (EW) nucleus is a midbrain structure with two distinct
populations:

EWpg (preganglionic, ChAT+) — classical parasympathetic preganglionic neurons
that contribute the autonomic component of the oculomotor nerve (CN III) and
mediate pupillary constriction (light reflex), accommodation, and convergence.
Lesion or pharmacologic block produces fixed dilated pupil, loss of near-vision
focus.

EWcp (centrally projecting, ChAT-) — neurons containing urocortin-1 (a member
of the CRF family) and CART (cocaine- and amphetamine-regulated transcript).
EWcp is NOT cholinergic and does NOT project to the ciliary ganglion. Instead
it projects to dorsal raphe nucleus, lateral septum, lateral hypothalamus,
central amygdala, and spinal cord. EWcp plays roles in stress responses,
energy homeostasis, and centrally-projecting modulation of sympathetic outflow,
heart rate, blood pressure, thermogenesis, food intake, and glucose metabolism.

EWcp urocortin-1 release engages CRF-R2 receptors at distal projection sites,
producing context-specific behavioral and autonomic effects. Notably, EWcp is
activated by stress paradigms but with distinct dynamics from PVN CRH neurons —
EWcp is more responsive to chronic / energy-state stressors than acute
psychogenic stress.

In the agent's substrate this mechanism produces the pupillary-equivalent state
(used as proxy of autonomic sympathetic-parasympathetic balance for "alertness"
gauges) plus a separate stress-modulating output via the EWcp urocortin pathway.

KEY FINDINGS
============
1. EW nucleus has two populations: EWpg (ChAT+, oculomotor parasympathetic
   for pupil/accommodation) and EWcp (ChAT-, centrally projecting,
   urocortin/CART positive) — [Kozicz et al. 2011, "The EW nucleus: A
   historical, structural and functional perspective on a dichotomous
   terminology" PMC3675228]
2. EWpg provides the parasympathetic component of CN III — pupillary light
   reflex, accommodation, convergence — [reviewed StatPearls "Neuroanatomy,
    Edinger-Westphal Nucleus" NBK554555]
3. EWcp projects to dorsal raphe, lateral septum, lateral hypothalamus,
   central amygdala, spinal cord — and contains urocortin-1 (CRF family)
   plus CART — [reviewed da Silva et al. 2015, "The centrally projecting
    EW nucleus--I: Efferents in the rat brain" PubMed 26206178]
4. EWcp plays a role in stress responses and energy homeostasis through
   modulation of heart rate, blood pressure, thermogenesis, food intake,
   and fat/glucose metabolism — [Cano et al. 2021, "Centrally Projecting
    EW Nucleus in the Control of Sympathetic Outflow and Energy Homeostasis"
    PMC8392615]
5. EWcp contains CART (cocaine- and amphetamine-regulated transcript)
   peptide — anorexigenic and anxiolytic, co-released with urocortin-1 in
   stress paradigms — [Kozicz 2001, Cell Tissue Res 306:131-138,
    doi:10.1007/s00441-001-0459-8]
6. EWcp → RVLM/SpVk projection modulates sympathetic outflow via CRF-R2;
   EWcp CART is anorexigenic — [Cano et al. 2021 PMC8392615;
   Krol 2021, Front Neural Circuits 15:667447, doi:10.3389/fncir.2021.667447]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level (pupillary correlate)
- ArousalRegulator.phasic_burst_active
- VitalCoreRegulator.sympathetic_tone
- VitalCoreRegulator.parasympathetic_tone
- VitalCoreRegulator.vital_drive
- StressActivationAxis.stress_active
- StressActivationAxis.cortisol_level
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.starvation_state
- ValenceTagger.valence_intensity

OUTPUTS (to brain_runner enrichment)
=====================================
- pupillary_constriction (0.0-1.0): EWpg cholinergic output → ciliary ganglion
- pupil_diameter_proxy (0.0-1.0): inversely related (1.0 = fully dilated)
- accommodation_drive (0.0-1.0): near-vision focus
- ewcp_urocortin_release (0.0-1.0): stress-energy-state output
- crf_r2_engagement (0.0-1.0): downstream CRF-R2 receptor activation
- alertness_proxy (0.0-1.0): pupil-based alertness gauge
- chronic_energy_stress_marker (bool): EWcp chronic activation pattern
- cart_peptide_activity (0.0-1.0): EWcp CART anorexigenic/anxiolytic effect
- sympathetic_ewcp_modulation (0.0-1.0): EWcp → RVLM/SpVk sympathetic drive

brain_runner enrichment:
    ew = all_results.get("EdingerWestphalMidbrain", {})
    if ew:
        enrichments["brain_pupil_diameter"] = ew.get("pupil_diameter_proxy", 0.5)
        enrichments["brain_alertness_proxy"] = ew.get("alertness_proxy", 0.5)
        enrichments["brain_ewcp_urocortin"] = ew.get("ewcp_urocortin_release", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class EdingerWestphalMidbrain(BrainMechanism):
    BASELINE_PUPIL_CONSTRICTION = 0.50
    EWCP_THRESHOLD_TICKS = 80
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="EdingerWestphalMidbrain",
            human_analog="Edinger-Westphal nucleus (preganglionic + centrally projecting)",
            layer="foundational",
        )
        self.state.setdefault("pupillary_constriction", self.BASELINE_PUPIL_CONSTRICTION)
        self.state.setdefault("pupil_diameter_proxy", 0.5)
        self.state.setdefault("accommodation_drive", 0.3)
        self.state.setdefault("ewcp_urocortin_release", 0.0)
        self.state.setdefault("crf_r2_engagement", 0.0)
        self.state.setdefault("alertness_proxy", 0.5)
        self.state.setdefault("chronic_energy_stress_marker", False)
        self.state.setdefault("high_ewcp_streak", 0)
        self.state.setdefault("cart_peptide_activity", 0.0)
        self.state.setdefault("sympathetic_ewcp_modulation", 0.0)
        self.state.setdefault("recent_ewcp", [])
        self.state.setdefault("tick_count", 0)

    def _ewpg_constriction_target(self, parasympathetic: float, sympathetic: float, valence: float) -> float:
        """Pupillary constriction tracks parasympathetic, anti-correlates with sympathetic.
        High valence/salience produces phasic pupil dilation (sympathetic dominant).
        """
        target = self.BASELINE_PUPIL_CONSTRICTION
        target += (parasympathetic - 0.5) * 0.4
        target -= (sympathetic - 0.5) * 0.5
        target -= valence * 0.15
        return max(0.05, min(0.95, target))

    def _accommodation_drive(self, parasympathetic: float, vital_drive: float = 0.5) -> float:
        """Accommodation (near focus) parallels parasympathetic activity."""
        return min(1.0, parasympathetic * 0.7 + vital_drive * 0.2)

    def _ewcp_urocortin_target(self, energy_balance: float, starvation: bool, cortisol: float) -> float:
        """EWcp activation by chronic energy-state and metabolic stress (Cano 2021)."""
        target = 0.0
        if starvation:
            target += 0.40
        if energy_balance < -0.30:
            target += abs(energy_balance) * 0.5
        if cortisol > 0.55:
            target += (cortisol - 0.5) * 0.4
        return min(1.0, target)

    def _crf_r2_engagement(self, urocortin: float) -> float:
        """CRF-R2 receptor activation at distal projection sites."""
        return min(1.0, urocortin * 1.05)

    def _alertness_proxy(self, pupil_diameter: float, tonic: float) -> float:
        """Clinical alertness gauge from pupil diameter + arousal."""
        return min(1.0, pupil_diameter * 0.55 + max(0.0, tonic - 0.5) * 0.6 + 0.25)

    def _detect_chronic_energy_stress(self, streak: int) -> bool:
        return streak > self.EWCP_THRESHOLD_TICKS

    def _cart_activity(self, urocortin: float, starvation: bool, cortisol: float) -> float:
        """CART peptide from EWcp — anorexigenic and anxiolytic.
        Rises with EWcp activation, modulated by energy state and stress.
        """
        if starvation and urocortin > 0.3:
            return min(1.0, 0.70 + urocortin * 0.3)
        if cortisol > 0.6:
            return min(1.0, 0.30 + urocortin * 0.5)
        return min(1.0, urocortin * 0.8)

    def _ewcp_sympathetic_modulation(self, urocortin: float, symp_tone: float) -> float:
        """EWcp → RVLM/SpVk projection modulates sympathetic outflow.
        Urocortin via CRF-R2 produces net sympathetic facilitation
        during energy-stress states (Cano 2021, Krol 2021).
        """
        return min(1.0, urocortin * 0.6 + symp_tone * 0.3)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        vcr = prior.get("VitalCoreRegulator", {})
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        vital_drive = float(vcr.get("vital_drive", 0.5))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        # --- EWpg: pupillary constriction ---
        constriction_target = self._ewpg_constriction_target(para_tone, symp_tone, valence_intensity)
        if phasic:
            constriction_target -= 0.10  # phasic burst → pupil dilation
        constriction_target = max(0.05, min(0.95, constriction_target))

        prev_constriction = float(self.state.get("pupillary_constriction", self.BASELINE_PUPIL_CONSTRICTION))
        new_constriction = self._smooth(prev_constriction, constriction_target)

        # --- Pupil diameter (inverse of constriction) ---
        pupil_diameter = 1.0 - new_constriction

        # --- Accommodation drive ---
        accommodation = self._accommodation_drive(para_tone, vital_drive)
        prev_accom = float(self.state.get("accommodation_drive", 0.3))
        new_accom = self._smooth(prev_accom, accommodation)

        # --- EWcp urocortin release ---
        urocortin_target = self._ewcp_urocortin_target(energy_balance, starvation, cortisol)
        prev_urocortin = float(self.state.get("ewcp_urocortin_release", 0.0))
        new_urocortin = self._smooth(prev_urocortin, urocortin_target)

        # --- CRF-R2 engagement ---
        crf_r2 = self._crf_r2_engagement(new_urocortin)

        # --- Alertness proxy ---
        alertness = self._alertness_proxy(pupil_diameter, tonic)

        # --- Chronic energy-stress detection ---
        prev_streak = int(self.state.get("high_ewcp_streak", 0))
        if new_urocortin > 0.50:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 1)
        chronic_marker = self._detect_chronic_energy_stress(streak)

        # --- CART peptide activity ---
        cart = self._cart_activity(new_urocortin, starvation, cortisol)

        # --- EWcp sympathetic modulation ---
        ewcp_symp = self._ewcp_sympathetic_modulation(new_urocortin, symp_tone)

        recent = list(self.state.get("recent_ewcp", []))
        recent.append(round(new_urocortin, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pupillary_constriction"] = round(new_constriction, 4)
        self.state["pupil_diameter_proxy"] = round(pupil_diameter, 4)
        self.state["accommodation_drive"] = round(new_accom, 4)
        self.state["ewcp_urocortin_release"] = round(new_urocortin, 4)
        self.state["crf_r2_engagement"] = round(crf_r2, 4)
        self.state["alertness_proxy"] = round(alertness, 4)
        self.state["chronic_energy_stress_marker"] = chronic_marker
        self.state["high_ewcp_streak"] = streak
        self.state["cart_peptide_activity"] = round(cart, 4)
        self.state["sympathetic_ewcp_modulation"] = round(ewcp_symp, 4)
        self.state["recent_ewcp"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pupillary_constriction": round(new_constriction, 4),
            "pupil_diameter_proxy": round(pupil_diameter, 4),
            "accommodation_drive": round(new_accom, 4),
            "ewcp_urocortin_release": round(new_urocortin, 4),
            "crf_r2_engagement": round(crf_r2, 4),
            "alertness_proxy": round(alertness, 4),
            "chronic_energy_stress_marker": chronic_marker,
            "cart_peptide_activity": round(cart, 4),
            "sympathetic_ewcp_modulation": round(ewcp_symp, 4),
        }
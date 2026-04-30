"""
AppetiteNPYBalancer — Arcuate Nucleus NPY/AgRP vs POMC/CART Energy Balance

NEURAL SUBSTRATE
================
The arcuate nucleus (ARC) of the hypothalamus contains two opposing populations
that govern energy balance: orexigenic NPY/AgRP neurons (promote feeding,
suppress energy expenditure) and anorexigenic POMC/CART neurons (suppress
feeding, increase energy expenditure). These two populations reciprocally
inhibit each other and project convergently onto downstream feeding-related
nuclei (paraventricular hypothalamus, lateral hypothalamus).

NPY/AgRP neurons are activated by falling leptin, falling insulin, rising
ghrelin (gut hunger hormone), and energy deficit signals. POMC/CART neurons
are activated by rising leptin, rising insulin, and gastrointestinal satiety
afferents (GLP-1, CCK, PYY via NTS). The balance between the two populations
sets motivational hunger state.

This module operates as a homeostatic energy-balance integrator that produces
hunger drive, satiety, and a coupled feeding-motivation signal. Energy state
is approximated by drive levels and time-since-last-rest.

KEY FINDINGS
============
1. NPY/AgRP and POMC/CART neurons in the arcuate nucleus are reciprocally
   inhibitory and project to PVN/LH feeding circuits — [Cone 2005, Nat Neurosci
    8:571-578]
2. Leptin signaling on POMC neurons suppresses feeding and increases energy
   expenditure; AgRP neurons antagonize MC4R signaling — [Schwartz et al. 2000,
    Nature 404:661-671]
3. Ghrelin from gastric mucosa activates AgRP neurons via GHSR1a, driving
   hunger — [Kojima et al. 1999, Nature 402:656-660]
4. Vagal afferents from gut chemosensors signal satiety via GLP-1, CCK, PYY
   to NTS, then onward to ARC POMC — [Berthoud 2008, Physiol Behav 94:704-708]

INPUTS (from prior_results)
============================
- Homeostat.drives — energy proxy
- Homeostat.dominant_drive
- Homeostat.fatigued
- CircadianTimer.circadian_phase
- VitalCoreRegulator.parasympathetic_tone (post-prandial proxy)
- ArousalRegulator.tonic_level

OUTPUTS
=======
- npy_agrp_drive (0.0-1.0): hunger-promoting tone
- pomc_cart_drive (0.0-1.0): satiety-promoting tone
- hunger_motivation (0.0-1.0): net feeding drive
- energy_balance_signed (-1.0 to 1.0): + = surplus, - = deficit
- feeding_seeking_active (bool)
- post_prandial (bool)

brain_runner enrichment:
    apb = all_results.get("AppetiteNPYBalancer", {})
    if apb:
        enrichments["brain_npy_agrp"] = apb.get("npy_agrp_drive", 0.5)
        enrichments["brain_pomc_cart"] = apb.get("pomc_cart_drive", 0.5)
        enrichments["brain_hunger_motivation"] = apb.get("hunger_motivation", 0.5)
        enrichments["brain_energy_balance"] = apb.get("energy_balance_signed", 0.0)
        enrichments["brain_feeding_seeking"] = apb.get("feeding_seeking_active", False)
"""

import math

from brain.base_mechanism import BrainMechanism


class AppetiteNPYBalancer(BrainMechanism):
    NPY_BASELINE = 0.30
    POMC_BASELINE = 0.50

    HUNGER_PHASE_AMPLITUDE = 0.20  # circadian meal-time swing
    POSTPRANDIAL_PARA_THRESHOLD = 0.65  # high para after meal
    FEEDING_THRESHOLD = 0.65

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="AppetiteNPYBalancer_AppetiteNPYBalancer",
            human_analog="Arcuate NPY/AgRP vs POMC/CART energy balance",
            layer="foundational",
        )
        self.state.setdefault("npy_agrp_drive", self.NPY_BASELINE)
        self.state.setdefault("pomc_cart_drive", self.POMC_BASELINE)
        self.state.setdefault("hunger_motivation", 0.5)
        self.state.setdefault("energy_balance_signed", 0.0)
        self.state.setdefault("feeding_seeking_active", False)
        self.state.setdefault("post_prandial", False)
        self.state.setdefault("ticks_since_meal", 0)
        self.state.setdefault("recent_balance", [])
        self.state.setdefault("tick_count", 0)

    def _circadian_meal_drive(self, phase: float) -> float:
        # Two peaks: ~breakfast (0.30) and dinner (0.75)
        peak1 = math.exp(-((phase - 0.30) ** 2) / 0.02) * 0.5
        peak2 = math.exp(-((phase - 0.75) ** 2) / 0.02) * 0.5
        return self.HUNGER_PHASE_AMPLITUDE * (peak1 + peak2)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _leptin_sensitivity_estimate(self, recent_balance: list) -> float:
        """Schwartz 2000: chronic positive energy balance reduces leptin
        sensitivity (leptin resistance proxy).
        """
        if len(recent_balance) < 10:
            return 0.85  # baseline normal sensitivity
        sample = recent_balance[-30:]
        mean = sum(sample) / len(sample)
        if mean > 0.30:
            # Sustained surplus → declining sensitivity
            return max(0.30, 0.85 - (mean - 0.30) * 0.8)
        return 0.85

    def _ghrelin_proxy(self, ticks_since_meal: int, hunger_motivation: float) -> float:
        """Kojima 1999: pre-meal ghrelin surge.
        Proxies as a function of fast duration and hunger motivation level.
        """
        if ticks_since_meal < 10:
            return 0.10
        # Ghrelin rises with fast duration up to a plateau
        fast_drive = min(1.0, ticks_since_meal / 100.0)
        return min(1.0, fast_drive * 0.6 + hunger_motivation * 0.3)

    def _meal_timing_anticipation(self, phase: float, history: list) -> float:
        """Anticipatory hunger before predicted meal time.
        Learned conditioning effect — agents develop expectation of meals at
        specific circadian phases.
        """
        if 0.27 < phase < 0.34 or 0.72 < phase < 0.78:
            # Within meal-time window
            return 0.15
        return 0.0

    def _vagal_satiety_input(self, parasympathetic: float) -> float:
        """Berthoud 2008: vagal afferent satiety input via NTS-POMC.
        High parasympathetic tone post-meal carries CCK/PYY/GLP-1 satiety signal.
        """
        if parasympathetic > 0.65:
            return min(0.4, (parasympathetic - 0.5) * 0.8)
        return 0.0

    def _detect_starvation_pattern(self, balance_signed: float, fatigued: bool, ticks_since: int) -> bool:
        """Sustained energy deficit + fatigue + long fast = starvation-state proxy."""
        return balance_signed < -0.4 and fatigued and ticks_since > 80

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        homeostat = prior.get("Homeostat", {})
        drives = homeostat.get("drives", {})
        dominant = homeostat.get("dominant_drive", "curiosity")
        fatigued = bool(homeostat.get("fatigued", False))

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))

        vcr = prior.get("VitalCoreRegulator", {})
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Compute hunger-state proxy from drives ---
        # Use 1 - rest as hunger; high curiosity/expression = active phase = need fuel
        rest = float(drives.get("rest", 0.5))
        curiosity = float(drives.get("curiosity", 0.5))
        expression = float(drives.get("expression", 0.5))
        hunger_proxy = (1.0 - rest) * 0.5 + curiosity * 0.25 + expression * 0.25

        # --- Detect post-prandial state ---
        post_prandial = para_tone > self.POSTPRANDIAL_PARA_THRESHOLD and tonic < 0.55
        ticks_since_meal = int(self.state.get("ticks_since_meal", 0))
        if post_prandial:
            ticks_since_meal = 0
        else:
            ticks_since_meal += 1

        # --- Compute NPY/AgRP target (orexigenic) ---
        npy_target = self.NPY_BASELINE
        npy_target += hunger_proxy * 0.30
        npy_target += self._circadian_meal_drive(phase)
        if post_prandial:
            npy_target -= 0.30  # ghrelin suppressed after meal
        if fatigued:
            npy_target += 0.10  # energy deficit boost
        if dominant == "rest":
            npy_target -= 0.10
        npy_target = max(0.05, min(0.95, npy_target))

        # --- Compute POMC/CART target (anorexigenic) ---
        pomc_target = self.POMC_BASELINE
        if post_prandial:
            pomc_target += 0.25  # vagal satiety afferents drive POMC
        pomc_target -= hunger_proxy * 0.25
        if dominant == "rest":
            pomc_target += 0.10
        pomc_target = max(0.05, min(0.95, pomc_target))

        # --- Reciprocal inhibition (Cone 2005) ---
        # NPY inhibits POMC, POMC inhibits NPY
        prev_npy = float(self.state.get("npy_agrp_drive", self.NPY_BASELINE))
        prev_pomc = float(self.state.get("pomc_cart_drive", self.POMC_BASELINE))

        npy_target -= prev_pomc * 0.10
        pomc_target -= prev_npy * 0.10

        npy_target = max(0.05, min(0.95, npy_target))
        pomc_target = max(0.05, min(0.95, pomc_target))

        new_npy = self._smooth(prev_npy, npy_target)
        new_pomc = self._smooth(prev_pomc, pomc_target)

        # --- Net hunger motivation ---
        hunger_motivation = max(0.0, min(1.0, new_npy - new_pomc * 0.5 + 0.30))

        # --- Energy balance signed ---
        # Negative = deficit (NPY dominant), Positive = surplus (POMC dominant)
        energy_balance = (new_pomc - new_npy)

        # --- Feeding seeking flag ---
        feeding_seeking = hunger_motivation > self.FEEDING_THRESHOLD

        recent = list(self.state.get("recent_balance", []))
        recent.append(round(energy_balance, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Leptin sensitivity (Schwartz 2000) ---
        leptin_sensitivity = self._leptin_sensitivity_estimate(recent)

        # --- Ghrelin proxy (Kojima 1999) ---
        ghrelin = self._ghrelin_proxy(ticks_since_meal, hunger_motivation)

        # --- Meal timing anticipation ---
        anticipation_drive = self._meal_timing_anticipation(phase, recent)

        # --- Vagal satiety (Berthoud 2008) ---
        vagal_satiety = self._vagal_satiety_input(para_tone)

        # --- Starvation pattern detection ---
        starvation_state = self._detect_starvation_pattern(energy_balance, fatigued, ticks_since_meal)

        self.state["npy_agrp_drive"] = round(new_npy, 4)
        self.state["pomc_cart_drive"] = round(new_pomc, 4)
        self.state["hunger_motivation"] = round(hunger_motivation, 4)
        self.state["energy_balance_signed"] = round(energy_balance, 4)
        self.state["feeding_seeking_active"] = feeding_seeking
        self.state["post_prandial"] = post_prandial
        self.state["ticks_since_meal"] = ticks_since_meal
        self.state["recent_balance"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["leptin_sensitivity"] = round(leptin_sensitivity, 4)
        self.state["ghrelin_proxy"] = round(ghrelin, 4)
        self.state["meal_anticipation_drive"] = round(anticipation_drive, 4)
        self.state["vagal_satiety_input"] = round(vagal_satiety, 4)
        self.state["starvation_state"] = starvation_state

        return {
            "npy_agrp_drive": round(new_npy, 4),
            "pomc_cart_drive": round(new_pomc, 4),
            "hunger_motivation": round(hunger_motivation, 4),
            "energy_balance_signed": round(energy_balance, 4),
            "feeding_seeking_active": feeding_seeking,
            "post_prandial": post_prandial,
            "leptin_sensitivity": round(leptin_sensitivity, 4),
            "ghrelin_proxy": round(ghrelin, 4),
            "meal_anticipation_drive": round(anticipation_drive, 4),
            "vagal_satiety_input": round(vagal_satiety, 4),
            "starvation_state": starvation_state,
        }

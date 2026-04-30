"""
SubfornicalOrgansThirstHub — SFO/OVLT Lamina Terminalis Thirst & Osmoregulation

NEURAL SUBSTRATE
================
The lamina terminalis is the anterior wall of the third ventricle and contains
three structures that together form the brain's principal osmoreceptive and
thirst-regulating network: the subfornical organ (SFO), median preoptic
nucleus (MnPO), and organum vasculosum of the lamina terminalis (OVLT). The
SFO and OVLT are circumventricular organs (CVOs) — they lack a typical
blood-brain barrier, with fenestrated capillaries permitting direct sampling
of plasma osmolality, sodium concentration, and circulating signals such as
angiotensin II (Ang II) and atrial natriuretic peptide (ANP).

Functional roles:
 • SFO: detects rising plasma sodium and Ang II via Na+-sensitive Nax
   channels and AT1 receptors. SFO neurons depolarize with hypernatremia,
   hyperosmolality, and Ang II binding, then signal thirst through
   projections to the MnPO and PVN/SON. SFO is the principal afferent for
   the dipsogenic effect of Ang II.
 • OVLT: also senses plasma osmolality and Na+ concentration. OVLT integrates
   with MnPO and PVN/SON to coordinate vasopressin (AVP) release from
   magnocellular hypothalamic neurons. Optogenetic activation of OVLT
   neurons rapidly induces drinking behavior.
 • MnPO: integrative node downstream of SFO and OVLT — funnels their
   convergent thirst signal toward action selection and effector output.

When activated, the lamina terminalis produces three coordinated outputs:
(a) thirst — dipsogenic motivation that biases behavior toward water-seeking;
(b) AVP release — antidiuretic hormone secretion via supraoptic and PVN
magnocellular neurons, conserving renal water;
(c) sympathetic activation — RVLM-driven vasoconstriction maintaining
blood pressure during volume depletion.

Recent work (Augustine et al. 2018, Matsuda et al. 2020 J Neurosci 40:2069)
identified molecularly distinct SFO/OVLT subpopulations encoding different
deficit states (hypernatremia vs hypovolemia vs Ang II-driven), supporting
a multidimensional thirst-encoding model rather than a single thirst signal.

KEY FINDINGS
============
1. Lamina terminalis (SFO, MnPO, OVLT) is the brain's principal osmoreceptive
   network for thirst regulation; SFO and OVLT lack BBB and directly sample
   plasma — [McKinley et al. 2023, Front Neurosci 17:1223836,
    doi:10.3389/fnins.2023.1223836]
2. SFO depolarizes to rising Na+, hyperosmolality, and Ang II via Nax
   channels and AT1 receptors — [reviewed in StatPearls Physiology,
    Osmoreceptors NBK557510]
3. Optogenetic activation of OVLT/SFO neurons rapidly induces drinking
   behavior — confirms causal role in thirst — [Oka et al. 2015,
    Nature 520:349-352; reviewed in McKinley 2023]
4. SFO/OVLT signals are integrated through MnPO and project to PVN/SON
   for vasopressin release; vasopressin secretion is osmotically and
   hormonally regulated by lamina terminalis — [Bourque 2008,
    Nat Rev Neurosci 9:519-531; Verbalis 2003 review]
5. Molecularly distinct SFO/OVLT populations encode hypernatremia vs
   hypovolemia vs Ang II — multidimensional thirst encoding —
   [Matsuda et al. 2020, J Neurosci 40:2069-2083; Augustine et al. 2018,
    Nature 555:204-209]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.vasomotor_setpoint (volume status proxy)
- VitalCoreRegulator.vital_drive
- VitalCoreRegulator.sympathetic_tone
- BaroreflexBalancer.map_proxy (volume / pressure depletion)
- AppetiteNPYBalancer.energy_balance_signed (metabolic state proxy)
- ThermoregulationCore.thermal_drive (heat → fluid loss → thirst coupling)
- StressActivationAxis.cortisol_level (stress modulates osmoregulation)
- CircadianTimer.is_subjective_day

OUTPUTS (to brain_runner enrichment)
=====================================
- plasma_osmolality_proxy (0.0-1.0, 1.0 = severe hypernatremia)
- plasma_volume_proxy (0.0-1.0, 0.0 = severe hypovolemia)
- thirst_drive (0.0-1.0)
- avp_release (0.0-1.0): vasopressin secretion proxy
- ang_ii_drive (0.0-1.0): renin-angiotensin cascade proxy
- water_seeking_active (bool)
- thirst_subtype (str): "hypernatremic" | "hypovolemic" | "anticipatory" | "none"

brain_runner enrichment block:
    sft = all_results.get("SubfornicalOrgansThirstHub", {})
    if sft:
        enrichments["brain_thirst_drive"] = sft.get("thirst_drive", 0.0)
        enrichments["brain_avp_release"] = sft.get("avp_release", 0.0)
        enrichments["brain_plasma_osm"] = sft.get("plasma_osmolality_proxy", 0.5)
        enrichments["brain_water_seeking"] = sft.get("water_seeking_active", False)
        enrichments["brain_thirst_subtype"] = sft.get("thirst_subtype", "none")
"""

from brain.base_mechanism import BrainMechanism


class SubfornicalOrgansThirstHub(BrainMechanism):
    """
    SFO/OVLT lamina terminalis thirst regulator.

    Estimates plasma osmolality and volume from vasomotor / pressure / thermal
    proxies, then dispatches multidimensional thirst (hypernatremic vs
    hypovolemic vs anticipatory) per Matsuda 2020 and Augustine 2018, with
    coordinated AVP release per Bourque 2008.
    """

    OSMOLALITY_BASELINE = 0.50
    VOLUME_BASELINE = 0.50
    THIRST_THRESHOLD = 0.40
    WATER_SEEKING_THRESHOLD = 0.55

    THERMAL_FLUID_LOSS_GAIN = 0.20
    STRESS_OSMOLALITY_GAIN = 0.10

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="SubfornicalOrgansThirstHub",
            human_analog="Lamina terminalis (SFO/OVLT/MnPO) thirst regulator",
            layer="foundational",
        )
        self.state.setdefault("plasma_osmolality_proxy", self.OSMOLALITY_BASELINE)
        self.state.setdefault("plasma_volume_proxy", self.VOLUME_BASELINE)
        self.state.setdefault("thirst_drive", 0.0)
        self.state.setdefault("avp_release", 0.0)
        self.state.setdefault("ang_ii_drive", 0.0)
        self.state.setdefault("water_seeking_active", False)
        self.state.setdefault("thirst_subtype", "none")
        self.state.setdefault("recent_thirst", [])
        self.state.setdefault("tick_count", 0)

    def _estimate_osmolality(self, thermal_drive: float, energy_balance: float, cortisol: float) -> float:
        """Plasma osmolality proxy. Heat (thermal_drive > 0) → sweat → loss → ↑ osm.
        Energy deficit + cortisol slightly raise osm via cortisol-driven Na+ retention.
        """
        osm = self.OSMOLALITY_BASELINE
        if thermal_drive > 0:
            osm += thermal_drive * self.THERMAL_FLUID_LOSS_GAIN
        if energy_balance < -0.2:
            osm += abs(energy_balance) * 0.10
        osm += cortisol * self.STRESS_OSMOLALITY_GAIN
        return max(0.05, min(0.98, osm))

    def _estimate_volume(self, map_proxy: float, vasomotor: float, sympathetic: float) -> float:
        """Plasma volume proxy. Low MAP + high sympathetic + high vasoconstriction
        → hypovolemia signature.
        """
        # If MAP is normal but sympathetic high, body is compensating for low volume
        if sympathetic > 0.7 and map_proxy < 0.5:
            return max(0.10, 0.50 - sympathetic * 0.3)
        return max(0.10, min(0.95, map_proxy * 0.7 + (1.0 - vasomotor) * 0.3))

    def _ang_ii_drive(self, volume: float, sympathetic: float) -> float:
        """RAAS cascade proxy: low volume + high sympathetic → renin → Ang II."""
        depletion = max(0.0, 0.5 - volume) * 2.0
        return min(1.0, depletion * 0.7 + max(0.0, sympathetic - 0.5) * 0.3)

    def _classify_thirst_subtype(self, osm: float, vol: float, ang_ii: float, anticipatory: bool) -> str:
        if osm > 0.65 and vol > 0.45:
            return "hypernatremic"
        if vol < 0.40 or ang_ii > 0.55:
            return "hypovolemic"
        if anticipatory:
            return "anticipatory"
        return "none"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        vasomotor = float(vcr.get("vasomotor_setpoint", 0.5))
        vital_drive = float(vcr.get("vital_drive", 0.5))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))

        bb = prior.get("BaroreflexBalancer", {})
        map_proxy = float(bb.get("map_proxy", 0.5))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))

        thermo = prior.get("ThermoregulationCore", {})
        thermal_drive = float(thermo.get("thermal_drive", 0.0))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        circ = prior.get("CircadianTimer", {})
        is_day = bool(circ.get("is_subjective_day", True))

        # --- Estimate osmolality and volume ---
        osm = self._estimate_osmolality(thermal_drive, energy_balance, cortisol)
        volume = self._estimate_volume(map_proxy, vasomotor, symp_tone)

        # Smooth onto state
        prev_osm = float(self.state.get("plasma_osmolality_proxy", self.OSMOLALITY_BASELINE))
        prev_vol = float(self.state.get("plasma_volume_proxy", self.VOLUME_BASELINE))
        new_osm = self._smooth(prev_osm, osm)
        new_vol = self._smooth(prev_vol, volume)

        # --- Compute Ang II drive ---
        ang_ii = self._ang_ii_drive(new_vol, symp_tone)
        prev_ang = float(self.state.get("ang_ii_drive", 0.0))
        new_ang = self._smooth(prev_ang, ang_ii)

        # --- Compute composite thirst drive (Augustine/Matsuda multidim) ---
        # Hypernatremic (SFO Na+ sensing) + hypovolemic (volume + Ang II) + anticipatory
        hyper_component = max(0.0, new_osm - 0.55) * 1.5  # ramps up above 0.55
        hypo_component = max(0.0, 0.45 - new_vol) * 1.5   # ramps up below 0.45
        ang_component = new_ang * 0.6

        # Anticipatory thirst — circadian drinking pattern (typically rises after waking)
        anticipatory = is_day and 0.30 < hyper_component + hypo_component + ang_component < 0.40
        anticipatory_drive = 0.2 if anticipatory else 0.0

        thirst_target = max(
            hyper_component + ang_component,
            hypo_component + ang_component,
            anticipatory_drive,
        )
        thirst_target = max(0.0, min(1.0, thirst_target))

        prev_thirst = float(self.state.get("thirst_drive", 0.0))
        new_thirst = self._smooth(prev_thirst, thirst_target)

        # --- AVP release (Bourque 2008): driven by osmolality primarily, volume secondarily ---
        avp_target = max(0.0, new_osm - 0.50) * 1.8
        if new_vol < 0.40:
            avp_target += (0.40 - new_vol) * 1.0
        if cortisol > 0.5:
            # Stress can suppress AVP-driven concentration in some contexts
            avp_target *= 0.85
        avp_target = max(0.0, min(1.0, avp_target))
        prev_avp = float(self.state.get("avp_release", 0.0))
        new_avp = self._smooth(prev_avp, avp_target)

        # --- Water seeking flag ---
        water_seeking = new_thirst > self.WATER_SEEKING_THRESHOLD

        # --- Classify thirst subtype ---
        subtype = self._classify_thirst_subtype(new_osm, new_vol, new_ang, anticipatory)
        if new_thirst < self.THIRST_THRESHOLD:
            subtype = "none"

        # --- Track recent ---
        recent = list(self.state.get("recent_thirst", []))
        recent.append(round(new_thirst, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Persist ---
        self.state["plasma_osmolality_proxy"] = round(new_osm, 4)
        self.state["plasma_volume_proxy"] = round(new_vol, 4)
        self.state["thirst_drive"] = round(new_thirst, 4)
        self.state["avp_release"] = round(new_avp, 4)
        self.state["ang_ii_drive"] = round(new_ang, 4)
        self.state["water_seeking_active"] = water_seeking
        self.state["thirst_subtype"] = subtype
        self.state["recent_thirst"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "plasma_osmolality_proxy": round(new_osm, 4),
            "plasma_volume_proxy": round(new_vol, 4),
            "thirst_drive": round(new_thirst, 4),
            "avp_release": round(new_avp, 4),
            "ang_ii_drive": round(new_ang, 4),
            "water_seeking_active": water_seeking,
            "thirst_subtype": subtype,
        }

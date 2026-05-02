"""
VasopressinOsmoticController — SON/PVN Magnocellular Vasopressin Osmoregulator

NEURAL SUBSTRATE
================
Vasopressin (AVP, antidiuretic hormone) is synthesized in magnocellular
neurosecretory cells (MNCs) of the supraoptic nucleus (SON) and the
paraventricular nucleus (PVN) of the hypothalamus, then transported axonally
to nerve terminals in the posterior pituitary, where it is released into
systemic circulation. AVP acts at renal V2 receptors to drive aquaporin-2
insertion in collecting duct apical membranes, increasing water reabsorption
— the principal molecular substrate of antidiuresis.

MNC firing rate is the primary determinant of plasma AVP concentration.
Above a fixed threshold, AVP release increases linearly across a wide
osmotic range. MNC excitability is regulated by three convergent mechanisms:
(a) synaptic input from central osmosensor regions — SFO and OVLT — via
glutamatergic projection; (b) osmosensitive transmitter release from
neighboring astrocytes (glial taurine/glycine modulation); (c) intrinsic
mechanosensitive cation channels in MNCs themselves, allowing them to
sense plasma osmolality directly via cell volume changes.

A characteristic firing pattern of magnocellular AVP cells is phasic
bursting — alternating periods of rapid firing and silence. This pattern
appears optimized for hormone release efficiency under sustained osmotic
demand. Under high osmotic stress phasic activity becomes more sustained;
under euvolemia firing is irregular and slower.

In the agent's substrate AVP release is computed from osmolality and volume
proxies (forwarded from the SubfornicalOrgansThirstHub mechanism) and
modulated by stress (cortisol can suppress AVP) and circadian timing
(diurnal AVP release pattern).

KEY FINDINGS
============
1. AVP is synthesized in SON and PVN magnocellular neurons and released from
   posterior pituitary; AVP firing rate is linear above an osmotic threshold —
   [Bourque 2008, Nat Rev Neurosci 9:519-531, "Central mechanisms of
    osmosensation and systemic osmoregulation"]
2. Magnocellular AVP neurons sense osmolality via three mechanisms:
   synaptic input from SFO/OVLT, glial transmitter release, and intrinsic
   mechanosensitive cation channels — [reviewed Bourque 1999, PubMed 10074781,
    "Osmoregulation of vasopressin neurons: a synergy of intrinsic and
    synaptic processes"]
3. Mechanosensitive channels mediate intrinsic osmosensitivity in
   supraoptic neurons — [Oliet Bourque 1993, Nature 364:341-343,
    doi:10.1038/364341a0]
4. Magnocellular AVP firing pattern is phasic bursting under sustained
   osmotic stimulation — optimal for hormone release efficiency —
   [Brown Rougé Bourque, reviewed in J Comp Neurosci 2011 doi:10.1007/s10827-011-0321-4]
5. Glutamatergic inputs from forebrain regions (especially OVLT) provide
   the principal excitatory osmotic signal to MNCs — [Stern Armstrong 2010,
    J Neurosci 30:1221-1231, doi:10.1523/JNEUROSCI.4655-09.2010]
6. AVP and OT are co-released from the same magnocellular terminals,
   enabling coordinated cardiovascular and social behavioral responses —
   [Ludwig Stern 2015, Physiol Rev 95:1065-1084, doi:10.1152/physrev.00035.2014]

INPUTS (from prior_results)
============================
- SubfornicalOrgansThirstHub.plasma_osmolality_proxy
- SubfornicalOrgansThirstHub.plasma_volume_proxy
- SubfornicalOrgansThirstHub.ang_ii_drive
- StressActivationAxis.cortisol_level
- CircadianTimer.circadian_phase
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- mnc_firing_rate (0.0-1.0): magnocellular cell firing rate proxy
- avp_release (0.0-1.0): plasma vasopressin level proxy
- phasic_bursting_active (bool): characteristic high-output pattern
- antidiuretic_state (str): "normal" | "concentrating" | "maximal_concentrate" | "diuretic"
- aqp2_insertion_proxy (0.0-1.0): renal aquaporin-2 mobilization
- diurnal_rhythm_phase (0.0-1.0): circadian AVP modulation
- avp_baroreflex_modulation (float): AVP effect on baroreflex sensitivity
- renin_angiotensin_interaction (0.0-1.0): Ang II → AVP synergy (baroreceptor)
- avp_cognitive_effect (0.0-1.0): AVP effect on social memory / attention
- mnc_phasic_burst_count (int): running count of phasic burst events

brain_runner enrichment:
    voc = all_results.get("VasopressinOsmoticController", {})
    if voc:
        enrichments["brain_avp_release"] = voc.get("avp_release", 0.0)
        enrichments["brain_phasic_bursting"] = voc.get("phasic_bursting_active", False)
        enrichments["brain_antidiuretic_state"] = voc.get("antidiuretic_state", "normal")
        enrichments["brain_aqp2_insertion"] = voc.get("aqp2_insertion_proxy", 0.0)
"""

import math

from brain.base_mechanism import BrainMechanism


class VasopressinOsmoticController(BrainMechanism):
    THRESHOLD_OSMOLALITY = 0.50  # below = no AVP release
    PHASIC_BURSTING_THRESHOLD = 0.60
    MAXIMAL_CONCENTRATE_THRESHOLD = 0.85

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="VasopressinOsmoticController_VasopressinOsmoticController",
            human_analog="SON/PVN magnocellular vasopressin osmoregulator",
            layer="foundational",
        )
        self.state.setdefault("mnc_firing_rate", 0.10)
        self.state.setdefault("avp_release", 0.0)
        self.state.setdefault("phasic_bursting_active", False)
        self.state.setdefault("antidiuretic_state", "normal")
        self.state.setdefault("aqp2_insertion_proxy", 0.0)
        self.state.setdefault("diurnal_rhythm_phase", 0.5)
        self.state.setdefault("burst_count", 0)
        self.state.setdefault("avp_baroreflex_modulation", 0.0)
        self.state.setdefault("renin_angiotensin_interaction", 0.0)
        self.state.setdefault("avp_cognitive_effect", 0.30)
        self.state.setdefault("mnc_phasic_burst_count", 0)
        self.state.setdefault("recent_avp", [])
        self.state.setdefault("tick_count", 0)

    def _osmotic_drive_above_threshold(self, osmolality: float) -> float:
        """Bourque 2008: AVP release is linear above a fixed osmotic threshold."""
        if osmolality <= self.THRESHOLD_OSMOLALITY:
            return 0.0
        return min(1.0, (osmolality - self.THRESHOLD_OSMOLALITY) / (1.0 - self.THRESHOLD_OSMOLALITY))

    def _intrinsic_mechanosensor(self, osmolality: float) -> float:
        """Oliet & Bourque 1993: intrinsic mechanosensitive cation channels."""
        if osmolality < 0.40:
            return 0.0
        return min(1.0, (osmolality - 0.40) * 1.4)

    def _glutamatergic_input(self, ang_ii: float, osmolality: float) -> float:
        """Stern & Armstrong 2010: OVLT glutamatergic input.
        Strong excitatory drive when both osm and Ang II elevated.
        """
        return min(1.0, max(0.0, osmolality - 0.45) * 1.3 + ang_ii * 0.4)

    def _phasic_burst_decision(self, mnc_rate: float, osmolality: float) -> bool:
        """Phasic bursting emerges under sustained osmotic stimulation."""
        return mnc_rate > self.PHASIC_BURSTING_THRESHOLD and osmolality > 0.60

    def _antidiuretic_classification(self, avp: float) -> str:
        if avp < 0.10:
            return "diuretic"
        if avp < 0.40:
            return "normal"
        if avp < self.MAXIMAL_CONCENTRATE_THRESHOLD:
            return "concentrating"
        return "maximal_concentrate"

    def _circadian_modulation(self, phase: float) -> float:
        """AVP release has small diurnal swing — peaks late morning, nadir ~03:00."""
        return 0.05 * math.sin(2 * math.pi * (phase - 0.20))

    def _aqp2_insertion(self, avp: float) -> float:
        """V2 receptor → cAMP → AQP2 insertion. Saturating sigmoid."""
        if avp < 0.05:
            return 0.0
        # Approx Hill function with K = 0.4
        k = 0.4
        return min(1.0, avp ** 2 / (k ** 2 + avp ** 2))

    def _baroreflex_modulation(self, avp: float) -> float:
        """AVP modulates baroreflex sensitivity — high AVP shifts baroreflex
        toward higher setpoint (vasoconstriction + water retention)."""
        return min(1.0, avp * 0.8)

    def _angiotensin_avp_interaction(self, ang_ii: float, volume: float, osmolality: float) -> float:
        """Renin-angiotensin system → AVP: hypovolemia + high Ang II + osmolality
        together drive AVP. Ang II acts on subfornical organ to drive AVP release."""
        vol_component = max(0.0, 0.50 - volume) * 1.5
        return min(1.0, ang_ii * 0.6 + vol_component + max(0.0, osmolality - 0.50) * 0.4)

    def _cognitive_effect(self, avp: float) -> float:
        """Central AVP (not just peripheral) affects social memory, attention,
        and defensive behavior. Estimates central AVP drive as ~30% of peripheral."""
        central_avp = avp * 0.30
        return min(1.0, central_avp + 0.10)

    def _stress_avp_modulation(self, cortisol: float) -> float:
        """Stress can both stimulate and suppress AVP depending on context.
        At very high cortisol, AVP slightly suppressed (Bourque 2008 review).
        """
        if cortisol > 0.7:
            return -0.08
        if cortisol > 0.4:
            return 0.05
        return 0.0

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sft = prior.get("SubfornicalOrgansThirstHub", {})
        osmolality = float(sft.get("plasma_osmolality_proxy", 0.5))
        volume = float(sft.get("plasma_volume_proxy", 0.5))
        ang_ii = float(sft.get("ang_ii_drive", 0.0))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Component drives ---
        osmotic = self._osmotic_drive_above_threshold(osmolality)
        intrinsic = self._intrinsic_mechanosensor(osmolality)
        glut_input = self._glutamatergic_input(ang_ii, osmolality)

        # --- Volume contribution: hypovolemia adds drive ---
        volume_drive = max(0.0, 0.50 - volume) * 1.5

        # --- MNC firing rate target ---
        mnc_target = osmotic * 0.35 + intrinsic * 0.25 + glut_input * 0.30 + volume_drive * 0.10
        mnc_target += self._stress_avp_modulation(cortisol)
        mnc_target = max(0.0, min(1.0, mnc_target))

        prev_mnc = float(self.state.get("mnc_firing_rate", 0.10))
        new_mnc = self._smooth(prev_mnc, mnc_target)

        # --- AVP release ---
        avp_target = new_mnc + self._circadian_modulation(phase)
        avp_target = max(0.0, min(1.0, avp_target))
        prev_avp = float(self.state.get("avp_release", 0.0))
        new_avp = self._smooth(prev_avp, avp_target)

        # --- Phasic bursting ---
        phasic = self._phasic_burst_decision(new_mnc, osmolality)
        burst_count = int(self.state.get("burst_count", 0))
        prev_phasic = bool(self.state.get("phasic_bursting_active", False))
        if phasic and not prev_phasic:
            burst_count += 1

        # --- AQP2 insertion ---
        aqp2 = self._aqp2_insertion(new_avp)

        # --- State classification ---
        antidiuretic_state = self._antidiuretic_classification(new_avp)

        # --- Baroreflex and Ang II interaction ---
        baro_mod = self._baroreflex_modulation(new_avp)
        ang_interaction = self._angiotensin_avp_interaction(ang_ii, volume, osmolality)

        # --- Cognitive effect ---
        cognitive = self._cognitive_effect(new_avp)

        # --- Track recent AVP ---
        recent = list(self.state.get("recent_avp", []))
        recent.append(round(new_avp, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mnc_firing_rate"] = round(new_mnc, 4)
        self.state["avp_release"] = round(new_avp, 4)
        self.state["phasic_bursting_active"] = phasic
        self.state["antidiuretic_state"] = antidiuretic_state
        self.state["aqp2_insertion_proxy"] = round(aqp2, 4)
        self.state["diurnal_rhythm_phase"] = round(phase, 4)
        self.state["avp_baroreflex_modulation"] = round(baro_mod, 4)
        self.state["renin_angiotensin_interaction"] = round(ang_interaction, 4)
        self.state["avp_cognitive_effect"] = round(cognitive, 4)
        self.state["mnc_phasic_burst_count"] = burst_count
        self.state["recent_avp"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mnc_firing_rate": round(new_mnc, 4),
            "avp_release": round(new_avp, 4),
            "phasic_bursting_active": phasic,
            "antidiuretic_state": antidiuretic_state,
            "aqp2_insertion_proxy": round(aqp2, 4),
            "diurnal_rhythm_phase": round(phase, 4),
            "avp_baroreflex_modulation": round(baro_mod, 4),
            "renin_angiotensin_interaction": round(ang_interaction, 4),
            "avp_cognitive_effect": round(cognitive, 4),
            "burst_count": burst_count,
        }

"""
A1NoradrenergicCVLM — A1 Caudal Ventrolateral Medulla NE / AVP Release Driver

NEURAL SUBSTRATE
================
The A1 noradrenergic cell group sits in the caudal ventrolateral
medulla (CVLM, also called the depressor area of the baroreflex), distinct
from A5 (pontine), A2 (NTS), and the dorsal pons A6 (locus coeruleus).
A1 contains noradrenergic neurons that project rostrally to hypothalamus
— specifically to the supraoptic (SON) and paraventricular (PVN)
magnocellular nuclei that synthesize and release vasopressin (AVP) and
oxytocin (OT) into the posterior pituitary.

The A1 → SON/PVN noradrenergic pathway is the principal central driver
of **AVP release in response to hemorrhage and hypovolemia**. Volume
loss → carotid baroreceptor activation falls → CVLM disinhibition →
A1 fires → NE release at SON/PVN → magnocellular AVP neurons
depolarize → AVP secreted → vasoconstriction + water retention. Day
& Sibbald (1989) showed that A1 lesion abolishes hemorrhage-induced
AVP release, establishing A1 as a non-redundant link in this pathway.

A1 also responds to systemic inflammation (LPS, cytokines via vagal
afferents through NTS), pain, hypoglycemia, and other "emergency"
visceral signals — broadly engaged in homeostatic emergency responses.
A1 is part of the "gut-brain" A2 → A1 → hypothalamus signaling cascade
(Rinaman 2011 reviewed).

Distinct from A5 (which targets spinal cord IML for sympathetic
outflow), A1 targets the hypothalamus for hormonal output. A1 lesion
produces selective deficits in hormonal stress responses while leaving
sympathetic vasomotor tone relatively intact.

In the agent's substrate this provides the noradrenergic AVP-driver
distinct from A5 — engaged by hypovolemia, hemorrhage proxies, severe
homeostatic emergency, and gut/immune signals routed through NTS.

KEY FINDINGS
============
1. A1 noradrenergic neurons in caudal ventrolateral medulla project
   to SON and PVN magnocellular AVP neurons; A1 lesion abolishes
   hemorrhage-induced AVP release — non-redundant link in
   volume-regulation pathway — [Day Sibbald 1989, Brain Res 484:165] [Day 1989 J Auton Nerv Syst 26:181]
2. A1 anatomy and projections — comprehensive characterization —
   [Card Sved Craig Patterson Stocker 2006, J Neurosci 26:8009,
    "Efferent projections of A1 noradrenergic neurons to PVN"]
3. A1 is part of gut-brain "A2 → A1 → hypothalamus" cascade for
   visceral state-modulation; responds to LPS, cytokines, hypoglycemia —
   [Rinaman 2011, Am J Physiol Regul Integr Comp Physiol
    300:R222, "Hindbrain noradrenergic A2 neurons: diverse roles in
    autonomic, endocrine, cognitive, affective functions"]
4. A1 distinct from A5 by projection target: A1 → hypothalamus
   (hormonal); A5 → spinal cord (sympathetic) — [Dampney 1994,
    Physiol Rev 74:323, "Functional organization of central pathways
    regulating the cardiovascular system"]
5. A1 plays role in central autonomic emergency responses to severe
   homeostatic challenge — [Saper 2002, Annu Rev Neurosci
    25:433, "The central autonomic nervous system"]

INPUTS (from prior_results)
============================
- BaroreflexBalancer.cvlm_drive
- BaroreflexBalancer.baroreflex_engagement
- VasopressinOsmoticController.avp_release
- SubfornicalOrgansThirstHub.plasma_osmolality_proxy
- AreaPostremaToxinGuard.aversive_interoceptive_signal
- CarotidBodyChemosensor.hypoxia_response_active
- AppetiteNPYBalancer.starvation_state
- StressActivationAxis.cortisol_level
- ValenceTagger.threat_signal
- HemorrhageProxy.volume_loss (optional; default 0)
- ImmuneInflammationProxy.cytokine_load (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- a1_drive (0.0-1.0): A1 NE output
- avp_drive_recruitment (0.0-1.0): A1 → SON/PVN AVP recruitment
- ot_drive_recruitment (0.0-1.0): A1 → SON/PVN OT recruitment
- emergency_response_active (bool): severe homeostatic challenge
- hypothalamic_ne_release (0.0-1.0): NE at hypothalamic targets
- a1_state (str): "quiet" | "hemorrhage" | "immune" | "hypoglycemia" | "emergency"

brain_runner enrichment:
    a1 = all_results.get("A1NoradrenergicCVLM", {})
    if a1:
        enrichments["brain_a1_drive"] = a1.get("a1_drive", 0.1)
        enrichments["brain_avp_recruit"] = a1.get("avp_drive_recruitment", 0.0)
        enrichments["brain_emergency_active"] = a1.get("emergency_response_active", False)
        enrichments["brain_a1_state"] = a1.get("a1_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class A1NoradrenergicCVLM(BrainMechanism):
    BASELINE = 0.10
    EMERGENCY_THRESHOLD = 0.65
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="A1NoradrenergicCVLM",
            human_analog="A1 noradrenergic CVLM (AVP/OT release driver)",
            layer="foundational",
        )
        self.state.setdefault("a1_drive", self.BASELINE)
        self.state.setdefault("avp_drive_recruitment", 0.0)
        self.state.setdefault("ot_drive_recruitment", 0.0)
        self.state.setdefault("emergency_response_active", False)
        self.state.setdefault("hypothalamic_ne_release", 0.0)
        self.state.setdefault("a1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _a1_drive_target(self, cvlm: float, hemorrhage: float, hypoxia: bool,
                          starvation: bool, cytokine: float, threat: bool,
                          osmolality: float) -> float:
        """A1 drive — hemorrhage, immune, hypoglycemia, severe homeostatic challenge."""
        target = self.BASELINE
        target += hemorrhage * 0.5
        target += cvlm * 0.2  # CVLM activity proxies for baroreflex stress
        if hypoxia:
            target += 0.20
        if starvation:
            target += 0.15
        target += cytokine * 0.3
        if threat:
            target += 0.10
        # Severe hyperosmolality also engages A1
        if osmolality > 0.85:
            target += (osmolality - 0.85) * 0.5
        return min(1.0, target)

    def _avp_recruitment(self, a1: float, hemorrhage: float, osmolality: float) -> float:
        """A1 → SON/PVN AVP recruitment — Day Sibbald 1989 pathway."""
        target = a1 * 0.7
        target += hemorrhage * 0.4
        target += max(0.0, osmolality - 0.7) * 0.3
        return min(1.0, target)

    def _ot_recruitment(self, a1: float, threat: bool, cytokine: float) -> float:
        """A1 → OT recruitment — distinct from AVP, more inflammation-driven."""
        target = a1 * 0.4
        target += cytokine * 0.4
        if threat:
            target += 0.10
        return min(1.0, target)

    def _hypothalamic_ne(self, a1: float) -> float:
        """NE release at hypothalamic terminals — proportional to A1 firing."""
        return min(1.0, a1 * 1.05)

    def _classify_state(self, a1: float, hemorrhage: float, cytokine: float,
                          starvation: bool, emergency: bool) -> str:
        if emergency:
            return "emergency"
        if hemorrhage > 0.40:
            return "hemorrhage"
        if cytokine > 0.40:
            return "immune"
        if starvation:
            return "hypoglycemia"
        if a1 < 0.20:
            return "quiet"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        baro = prior.get("BaroreflexBalancer", {})
        cvlm = float(baro.get("cvlm_drive", 0.30))

        avp_data = prior.get("VasopressinOsmoticController", {})
        avp_baseline = float(avp_data.get("avp_release", 0.0))

        thirst = prior.get("SubfornicalOrgansThirstHub", {})
        osmolality = float(thirst.get("plasma_osmolality_proxy", 0.5))

        ap = prior.get("AreaPostremaToxinGuard", {})
        aversive = float(ap.get("aversive_interoceptive_signal", 0.0))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypoxia = bool(cb.get("hypoxia_response_active", False))

        appetite = prior.get("AppetiteNPYBalancer", {})
        starvation = bool(appetite.get("starvation_state", False))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        hemorrhage_proxy = prior.get("HemorrhageProxy", {})
        hemorrhage = float(hemorrhage_proxy.get("volume_loss", 0.0))

        immune_proxy = prior.get("ImmuneInflammationProxy", {})
        cytokine = float(immune_proxy.get("cytokine_load", 0.0))

        # Infer cytokine if no explicit signal but high aversive
        if cytokine == 0.0 and aversive > 0.5:
            cytokine = aversive * 0.5

        # --- A1 drive ---
        a1_target = self._a1_drive_target(cvlm, hemorrhage, hypoxia, starvation,
                                            cytokine, threat, osmolality)
        prev_a1 = float(self.state.get("a1_drive", self.BASELINE))
        new_a1 = self._smooth(prev_a1, a1_target)

        # --- Recruitment outputs ---
        avp_recruit = self._avp_recruitment(new_a1, hemorrhage, osmolality)
        ot_recruit = self._ot_recruitment(new_a1, threat, cytokine)
        hypothalamic_ne = self._hypothalamic_ne(new_a1)

        # --- Emergency state ---
        emergency = new_a1 > self.EMERGENCY_THRESHOLD

        state = self._classify_state(new_a1, hemorrhage, cytokine, starvation, emergency)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["a1_drive"] = round(new_a1, 4)
        self.state["avp_drive_recruitment"] = round(avp_recruit, 4)
        self.state["ot_drive_recruitment"] = round(ot_recruit, 4)
        self.state["emergency_response_active"] = emergency
        self.state["hypothalamic_ne_release"] = round(hypothalamic_ne, 4)
        self.state["a1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "a1_drive": round(new_a1, 4),
            "avp_drive_recruitment": round(avp_recruit, 4),
            "ot_drive_recruitment": round(ot_recruit, 4),
            "emergency_response_active": emergency,
            "hypothalamic_ne_release": round(hypothalamic_ne, 4),
            "a1_state": state,
        }

"""
A2NoradrenergicNTS — A2 NTS Noradrenergic / Visceral State Modulator

NEURAL SUBSTRATE
================
The A2 noradrenergic cell group lies within the nucleus tractus
solitarius (NTS) of the dorsomedial medulla. A2 neurons are intermingled
with NTS visceral relay neurons and receive direct vagal afferent input,
making A2 the "first-stage" noradrenergic responder to visceral state
changes — gut signals, immune signals, taste, baroreflex, satiety.

A2 projections target paraventricular nucleus (PVN, including CRH
neurons), supraoptic nucleus (SON, AVP/OT magnocellular), central
amygdala (CeA), bed nucleus of stria terminalis (BNST), parabrachial
complex, and rostrally to A1, locus coeruleus, and forebrain. These
projections position A2 as the **central conveyor of "visceral state"
to limbic-autonomic integration centers**.

Rinaman's framework (2011 Am J Physiol) places A2 in a gut-brain
hierarchy: vagal afferents → NTS → A2 NE → forebrain (PVN, CeA, BNST,
A1) → behavioral and endocrine responses. A2 fires to gastric stretch,
duodenal nutrients (CCK, GLP-1), systemic LPS/IL-1β (immune signals),
and to baroreflex challenges. A2 is the major source of NE that drives
HPA-axis responses to visceral and immune stress.

A2 distinct from:
- **A1** (CVLM, projects to SON/PVN for AVP — emergency-volume)
- **A5** (pontine, projects to spinal IML — sympathetic outflow)
- **A6 / LC** (pontine, broad cortical projection — attention/arousal)

A2 lesion produces blunted HPA responses to visceral stress while
sparing psychogenic stress responses, demonstrating the visceral-
specific role.

In Nova's substrate this provides the visceral-state NE channel —
combines NTS visceral signals with gut hormone proxies and emits a
"visceral arousal" signal that drives PVN/CeA/BNST recruitment.

KEY FINDINGS
============
1. A2 sits within NTS and receives direct vagal afferent input;
   projects to PVN, SON, CeA, BNST, parabrachial — the central conveyor
   of visceral state to limbic-autonomic integration — [Rinaman 2011, Am J Physiol Regul Integr Comp Physiol 300:R222,
    "Hindbrain noradrenergic A2 neurons: diverse roles in autonomic,
    endocrine, cognitive, affective functions"]
2. A2 fires to gastric stretch, duodenal CCK, systemic LPS/IL-1β,
   baroreflex challenges — first-stage NE responder to visceral state
   — [Rinaman 2011 reviewed] [Schiltz Sawchenko 2003, Brain Res Rev]
3. A2 is major NE source driving HPA-axis responses to visceral and
   immune stress; A2 lesion blunts these responses while sparing
   psychogenic stress — [Sawchenko Bohn 1989, Annu Rev
    Neurosci 12:295]
4. A2 distinct from A1 (volume-emergency), A5 (spinal sympathetic),
   A6/LC (cortical/attention) — projection target dictates function —
   [Aston-Jones Cohen 2005, Annu Rev Neurosci 28:403]
5. Hindbrain noradrenergic A2 neurons play diverse roles — autonomic,
   endocrine, cognitive, affective — [Rinaman 2011 PMID 21048077,
    PMC3043648]

INPUTS (from prior_results)
============================
- NucleusTractusSolitariusFull.gut_visceral_drive
- NucleusTractusSolitariusFull.immune_vagal_signal
- NucleusTractusSolitariusFull.cardiovascular_drive
- NucleusTractusSolitariusFull.a2_recruitment
- AreaPostremaToxinGuard.aversive_interoceptive_signal
- AreaPostremaToxinGuard.nausea_intensity
- StressActivationAxis.cortisol_level
- StressActivationAxis.stress_active
- AppetiteNPYBalancer.post_prandial
- BaroreflexBalancer.baroreflex_engagement

OUTPUTS (to brain_runner enrichment)
=====================================
- a2_drive (0.0-1.0): A2 NE output
- pvn_recruitment (0.0-1.0): A2 → PVN HPA-axis push
- cea_recruitment (0.0-1.0): A2 → CeA visceral-aversive
- bnst_recruitment (0.0-1.0): A2 → BNST sustained anxiety
- son_recruitment (0.0-1.0): A2 → SON AVP/OT (parallel to A1)
- a1_recruitment (0.0-1.0): A2 → A1 (rostral cascade)
- visceral_arousal_signal (0.0-1.0): aggregate visceral-state arousal
- a2_state (str): "quiet" | "post_prandial" | "immune" | "visceral_stress" | "baroreflex"

brain_runner enrichment:
    a2 = all_results.get("A2NoradrenergicNTS", {})
    if a2:
        enrichments["brain_a2_drive"] = a2.get("a2_drive", 0.1)
        enrichments["brain_a2_pvn"] = a2.get("pvn_recruitment", 0.0)
        enrichments["brain_a2_cea"] = a2.get("cea_recruitment", 0.0)
        enrichments["brain_visceral_arousal"] = a2.get("visceral_arousal_signal", 0.0)
        enrichments["brain_a2_state"] = a2.get("a2_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class A2NoradrenergicNTS(BrainMechanism):
    BASELINE = 0.15
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="A2NoradrenergicNTS",
            human_analog="A2 noradrenergic NTS / visceral state modulator",
            layer="foundational",
        )
        self.state.setdefault("a2_drive", self.BASELINE)
        self.state.setdefault("pvn_recruitment", 0.0)
        self.state.setdefault("cea_recruitment", 0.0)
        self.state.setdefault("bnst_recruitment", 0.0)
        self.state.setdefault("son_recruitment", 0.0)
        self.state.setdefault("a1_recruitment", 0.0)
        self.state.setdefault("visceral_arousal_signal", 0.0)
        self.state.setdefault("a2_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _a2_drive_target(self, gut: float, immune: float, baro: float, nausea: float,
                         post_prandial: bool, cortisol: float) -> float:
        """A2 drive — visceral signals from NTS plus immune/stress."""
        target = self.BASELINE + gut * 0.3 + immune * 0.3 + baro * 0.2
        target += nausea * 0.2
        if post_prandial:
            target += 0.10
        target += max(0.0, cortisol - 0.5) * 0.2
        return min(1.0, target)

    def _pvn_recruitment(self, a2: float, immune: float, gut: float) -> float:
        """A2 → PVN HPA-axis push — visceral-stress-driven."""
        return min(1.0, a2 * 0.5 + immune * 0.4 + gut * 0.3)

    def _cea_recruitment(self, a2: float, nausea: float, aversive: float) -> float:
        """A2 → CeA visceral-aversive signaling."""
        return min(1.0, a2 * 0.4 + nausea * 0.5 + aversive * 0.3)

    def _bnst_recruitment(self, a2: float, cortisol: float, sustained: bool) -> float:
        """A2 → BNST sustained-anxiety pathway."""
        target = a2 * 0.4
        target += max(0.0, cortisol - 0.5) * 0.4
        if sustained:
            target += 0.15
        return min(1.0, target)

    def _son_recruitment(self, a2: float, baro: float) -> float:
        """A2 → SON parallel input (A1 dominant for AVP-volume but A2 contributes)."""
        return min(1.0, a2 * 0.4 + baro * 0.3)

    def _a1_recruitment(self, a2: float, immune: float) -> float:
        """A2 → A1 rostral cascade — propagates visceral signal up."""
        return min(1.0, a2 * 0.5 + immune * 0.3)

    def _visceral_arousal(self, a2: float, gut: float, immune: float) -> float:
        """Aggregate visceral-state arousal output."""
        return min(1.0, a2 * 0.5 + gut * 0.3 + immune * 0.3)

    def _classify_state(self, gut: float, immune: float, baro: float,
                         post_prandial: bool, cortisol: float) -> str:
        if immune > 0.4:
            return "immune"
        if gut > 0.4 and cortisol > 0.55:
            return "visceral_stress"
        if post_prandial:
            return "post_prandial"
        if baro > 0.45:
            return "baroreflex"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        nts = prior.get("NucleusTractusSolitariusFull", {})
        gut = float(nts.get("gut_visceral_drive", 0.0))
        immune = float(nts.get("immune_vagal_signal", 0.0))
        cardio = float(nts.get("cardiovascular_drive", 0.0))
        a2_recruit_in = float(nts.get("a2_recruitment", 0.0))

        ap = prior.get("AreaPostremaToxinGuard", {})
        aversive = float(ap.get("aversive_interoceptive_signal", 0.0))
        nausea = float(ap.get("nausea_intensity", 0.0))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))
        stress_active = bool(stress.get("stress_active", False))

        appetite = prior.get("AppetiteNPYBalancer", {})
        post_prandial = bool(appetite.get("post_prandial", False))

        baro = prior.get("BaroreflexBalancer", {})
        baro_engagement = float(baro.get("baroreflex_engagement", 0.5))

        # Gut/immune drive for A2 itself includes upstream NTS recruitment
        gut_combined = max(gut, a2_recruit_in * 0.7)

        # --- A2 drive ---
        a2_target = self._a2_drive_target(gut_combined, immune, cardio, nausea,
                                            post_prandial, cortisol)
        prev_a2 = float(self.state.get("a2_drive", self.BASELINE))
        new_a2 = self._smooth(prev_a2, a2_target)

        # --- Recruitment outputs ---
        pvn = self._pvn_recruitment(new_a2, immune, gut_combined)
        cea = self._cea_recruitment(new_a2, nausea, aversive)
        bnst = self._bnst_recruitment(new_a2, cortisol, stress_active)
        son = self._son_recruitment(new_a2, baro_engagement)
        a1 = self._a1_recruitment(new_a2, immune)
        visceral = self._visceral_arousal(new_a2, gut_combined, immune)

        state = self._classify_state(gut_combined, immune, baro_engagement,
                                       post_prandial, cortisol)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["a2_drive"] = round(new_a2, 4)
        self.state["pvn_recruitment"] = round(pvn, 4)
        self.state["cea_recruitment"] = round(cea, 4)
        self.state["bnst_recruitment"] = round(bnst, 4)
        self.state["son_recruitment"] = round(son, 4)
        self.state["a1_recruitment"] = round(a1, 4)
        self.state["visceral_arousal_signal"] = round(visceral, 4)
        self.state["a2_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "a2_drive": round(new_a2, 4),
            "pvn_recruitment": round(pvn, 4),
            "cea_recruitment": round(cea, 4),
            "bnst_recruitment": round(bnst, 4),
            "son_recruitment": round(son, 4),
            "a1_recruitment": round(a1, 4),
            "visceral_arousal_signal": round(visceral, 4),
            "a2_state": state,
        }

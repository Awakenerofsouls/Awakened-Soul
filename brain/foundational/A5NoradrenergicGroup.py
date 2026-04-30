"""
A5NoradrenergicGroup — Pontine A5 NE Group (Sympathetic / Visceral Pain)

NEURAL SUBSTRATE
================
The A5 noradrenergic cell group is a pontine cluster of catecholamine
neurons in the ventrolateral pons, anatomically distinct from the
locus coeruleus (A6, dorsolateral pons). Although smaller than LC,
A5 is a major source of descending noradrenergic input to the spinal
cord — particularly to sympathetic preganglionic neurons in the
intermediolateral cell column (IML) and to dorsal horn nociceptive
neurons.

A5 differs functionally from LC in two principal ways. First, its
projection emphasis is on visceral sympathetic regulation — A5 neurons
are a significant source of catecholaminergic input to thoracic
sympathetic preganglionic neurons, and chemogenetic activation of A5
elevates blood pressure and visceral sympathetic activity (Bruinstroop
et al. 2022). Second, A5 contributes to descending pain modulation
via a disynaptic CVLM → A5 → spinal-cord pathway: hyperalgesic effects
of CVLM angiotensin-II injection are mediated by A5 (Tavares et al.
2010, Brain Res; Tavares Lima 1998, Brain Res).

A5 is reciprocally connected with the caudal ventrolateral medulla
(CVLM, the depressor area of baroreflex) and with the carotid body
chemoreflex pathway. Stimulation of A5 increases visceral sympathetic
nerve activity but tends to suppress somatosensory transmission, opposite
to LC's somatosensory enhancement. This dichotomy — A6/LC for
somatosensory, A5 for visceral autonomic — is a useful organizing
principle for noradrenergic pontine function.

Beyond pain and sympathetic outflow, A5 participates in cardiorespiratory
coupling and contributes to the carotid sympathetic chemoreflex.
Selective activation produces blood pressure elevation, sympathoexcitation,
and altered breathing pattern.

In Nova's substrate this provides the sympathetic-emphasis NE channel
distinct from LC — a complement to NorepiPhasicTonicSwitcher (LC) that
biases toward visceral autonomic and pain modulation rather than
attention/somatosensory gain.

KEY FINDINGS
============
1. A5 is in the ventrolateral pons, distinct from A6 (LC, dorsolateral
   pons) — A5 has effects on sympathetic autonomic function while A6/LC
   targets somatosensory transmission — [Pertovaara 2006, Pharmacol Ther
    111:225-251, "Noradrenergic pain modulation"]
2. A5 noradrenergic neurons project to spinal cord and contribute to
   visceral sympathetic regulation — chemogenetic activation increases
   blood pressure and visceral sympathetic activity — [Bruinstroop et al.
    2022, Auton Neurosci doi:10.1016/j.autneu.2022.103024, PMC9602699]
3. A5 mediates hyperalgesic CVLM → spinal-cord disynaptic pain pathway —
   pontine A5 noradrenergic cell group is the relay for CVLM-induced
   hyperalgesia — [Tavares et al. 2010, Brain Res 1322:18-26,
    "The hyperalgesic effects induced by the injection of angiotensin
    II into the caudal ventrolateral medulla are mediated by the
    pontine A5 noradrenergic cell group" PubMed 20171959]
4. A5 spinally projecting neurons are reciprocally connected with CVLM —
   substrate for bidirectional CVLM-A5 modulation — [Tavares Lima 1998,
    Brain Res 786:111-118, PubMed 9464939]
5. A5 noradrenergic neurons participate in carotid sympathetic chemoreflex
   — [Coote 1994, Brain Res Bull 35:519-526; PubMed 8067463]

INPUTS (from prior_results)
============================
- BaroreflexBalancer.cvlm_drive
- BaroreflexBalancer.rvlm_drive
- BaroreflexBalancer.baroreflex_engagement
- CarotidBodyChemosensor.hypoxia_response_active
- CarotidBodyChemosensor.hypercapnia_response
- DescendingPainGate.facilitatory_drive
- VitalCoreRegulator.sympathetic_tone
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- a5_drive (0.0-1.0): A5 NE output
- spinal_ne_visceral (0.0-1.0): IML sympathetic NE drive
- bp_elevation_drive (0.0-1.0): blood pressure elevation signal
- pain_facilitation_a5 (0.0-1.0): A5 contribution to descending facilitation
- chemoreflex_modulation (0.0-1.0): A5 chemoreflex contribution
- a5_state (str): "quiet" | "sympathoexcitatory" | "pain_facilitatory" | "chemoreflex"

brain_runner enrichment:
    a5 = all_results.get("A5NoradrenergicGroup", {})
    if a5:
        enrichments["brain_a5_drive"] = a5.get("a5_drive", 0.2)
        enrichments["brain_spinal_ne_visceral"] = a5.get("spinal_ne_visceral", 0.2)
        enrichments["brain_bp_elevation"] = a5.get("bp_elevation_drive", 0.0)
        enrichments["brain_a5_state"] = a5.get("a5_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class A5NoradrenergicGroup(BrainMechanism):
    BASELINE_DRIVE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="A5NoradrenergicGroup",
            human_analog="Pontine A5 noradrenergic group (sympathetic / visceral pain)",
            layer="foundational",
        )
        self.state.setdefault("a5_drive", self.BASELINE_DRIVE)
        self.state.setdefault("spinal_ne_visceral", 0.20)
        self.state.setdefault("bp_elevation_drive", 0.0)
        self.state.setdefault("pain_facilitation_a5", 0.0)
        self.state.setdefault("chemoreflex_modulation", 0.0)
        self.state.setdefault("a5_state", "quiet")
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _a5_drive_target(self, sympathetic: float, rvlm: float, hypoxia: bool,
                         hypercapnia: float, pain_fac: float) -> float:
        """A5 drive — driven by visceral sympathetic outflow and chemoreflex."""
        target = self.BASELINE_DRIVE
        target += max(0.0, sympathetic - 0.4) * 0.4
        target += rvlm * 0.2
        if hypoxia:
            target += 0.20
        target += hypercapnia * 0.30
        target += pain_fac * 0.2  # CVLM angII-style facilitation
        return max(0.0, min(1.0, target))

    def _spinal_ne_visceral(self, a5: float, sympathetic: float) -> float:
        """IML sympathetic NE drive — A5 → spinal."""
        return min(1.0, a5 * 0.7 + max(0.0, sympathetic - 0.4) * 0.3)

    def _bp_elevation(self, spinal_ne: float, rvlm: float) -> float:
        """Blood pressure elevation drive (Bruinstroop 2022)."""
        return min(1.0, spinal_ne * 0.6 + rvlm * 0.4)

    def _pain_facilitation_a5(self, a5: float, cvlm: float, pain_fac: float) -> float:
        """A5 contribution to descending pain facilitation (Tavares 2010).
        Engaged when CVLM input + facilitatory tone drive A5.
        """
        if pain_fac < 0.30:
            return 0.0
        return min(1.0, a5 * 0.5 + max(0.0, cvlm - 0.3) * 0.4)

    def _chemoreflex_mod(self, hypoxia: bool, hypercapnia: float, a5: float) -> float:
        """A5 chemoreflex contribution."""
        if not hypoxia and hypercapnia < 0.20:
            return 0.0
        target = a5 * 0.5
        if hypoxia:
            target += 0.20
        target += hypercapnia * 0.30
        return min(1.0, target)

    def _a5_respiratory_coupling(self, a5: float, chemoreflex: float) -> float:
        """A5-respiratory coupling index."""
        prev = float(self.state.get("respiratory_coupling", 0.0))
        return 0.8 * prev + 0.2 * min(a5 * chemoreflex * 2.0, 1.0)

    def _classify_state(self, a5: float, bp: float, pain_fac: float, chemo: float) -> str:
        if chemo > 0.40:
            return "chemoreflex"
        if pain_fac > 0.40:
            return "pain_facilitatory"
        if bp > 0.45:
            return "sympathoexcitatory"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        baro = prior.get("BaroreflexBalancer", {})
        cvlm = float(baro.get("cvlm_drive", 0.30))
        rvlm = float(baro.get("rvlm_drive", 0.30))
        baro_eng = float(baro.get("baroreflex_engagement", 0.50))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypoxia = bool(cb.get("hypoxia_response_active", False))
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))

        dpg = prior.get("DescendingPainGate", {})
        facilitatory = float(dpg.get("facilitatory_drive", 0.30))

        vcr = prior.get("VitalCoreRegulator", {})
        symp = float(vcr.get("sympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- A5 drive ---
        a5_target = self._a5_drive_target(symp, rvlm, hypoxia, hypercapnia, facilitatory)
        prev_a5 = float(self.state.get("a5_drive", self.BASELINE_DRIVE))
        new_a5 = self._smooth(prev_a5, a5_target)

        # --- Spinal NE visceral ---
        spinal_ne = self._spinal_ne_visceral(new_a5, symp)
        prev_spinal = float(self.state.get("spinal_ne_visceral", 0.20))
        new_spinal = self._smooth(prev_spinal, spinal_ne)

        # --- BP elevation ---
        bp = self._bp_elevation(new_spinal, rvlm)
        prev_bp = float(self.state.get("bp_elevation_drive", 0.0))
        new_bp = self._smooth(prev_bp, bp)

        # --- Pain facilitation ---
        pain_fac = self._pain_facilitation_a5(new_a5, cvlm, facilitatory)

        # --- Chemoreflex modulation ---
        chemo = self._chemoreflex_mod(hypoxia, hypercapnia, new_a5)

        # --- State ---
        state = self._classify_state(new_a5, new_bp, pain_fac, chemo)

        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_a5, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["a5_drive"] = round(new_a5, 4)
        self.state["spinal_ne_visceral"] = round(new_spinal, 4)
        self.state["bp_elevation_drive"] = round(new_bp, 4)
        self.state["pain_facilitation_a5"] = round(pain_fac, 4)
        self.state["chemoreflex_modulation"] = round(chemo, 4)
        self.state["a5_state"] = state
        self.state["recent_drives"] = recent
        self.state["sympathetic_reserve"] = round(max(0.0, 1.0 - new_a5), 4)
        self.state["respiratory_coupling"] = round(self._a5_respiratory_coupling(new_a5, chemo), 4)
        self.state["pain_facilitation_a5"] = round(pain_fac, 4)
        self.state["a5_drive_ema"] = round(new_a5 * 0.2 + float(self.state.get("a5_drive_ema", new_a5)) * 0.8, 4)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "a5_drive": round(new_a5, 4),
            "spinal_ne_visceral": round(new_spinal, 4),
            "bp_elevation_drive": round(new_bp, 4),
            "pain_facilitation_a5": round(pain_fac, 4),
            "chemoreflex_modulation": round(chemo, 4),
            "a5_state": state,
            "sympathetic_tone": (state in ("Active", "StressPeak")),
        }

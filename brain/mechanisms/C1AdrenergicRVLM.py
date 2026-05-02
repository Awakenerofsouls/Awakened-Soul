"""
C1AdrenergicRVLM — C1 Adrenergic Premotor / Sympathetic + Glucose Counter-Regulation

NEURAL SUBSTRATE
================
The C1 adrenergic cell group sits in the rostral ventrolateral medulla
(RVLM, the pressor area of the baroreflex), distinct from the A1
(noradrenergic) caudal VLM neurons. C1 neurons synthesize **epinephrine**
(adrenaline) by converting NE → epinephrine via phenylethanolamine
N-methyltransferase (PNMT). C1 is the principal central source of
adrenergic premotor drive to spinal sympathetic preganglionic neurons
(IML), and it is essential for the cardiovascular component of the
fight-or-flight response.

Beyond cardiovascular sympathoexcitation, C1 has a critical role in
**glucose counter-regulation** — the response to hypoglycemia. Guyenet's
group (Abbott, Stornetta, Coates, Guyenet) established that C1 neurons
fire in response to hypoglycemia, increasing sympathetic outflow and
driving hepatic glucose production via splanchnic sympathetic
recruitment. C1 lesion impairs the counter-regulatory response,
producing hypoglycemia-unawareness.

C1 also drives:
- Sympathetic vasomotor tone for blood pressure (parallel to RVLM
  glutamatergic neurons covered in BaroreflexBalancer)
- Adrenal medullary epinephrine release via splanchnic sympathetic
- Pituitary ACTH release via PVN-CRH recruitment
- Stress-induced cardiovascular and metabolic responses

C1 is engaged by hypoxia, hypoglycemia, hemorrhage (parallel to A1 but
distinct), pain, and acute psychogenic stress. C1 axons project to spinal
IML (sympathetic), hypothalamic PVN, and forebrain.

Distinct from:
- **A1** (CVLM, NE not adrenaline, projects mostly to hypothalamus)
- **A5** (pontine, NE, also projects to spinal IML — partial overlap
  but different stress profile)
- **A6/LC** (cortical, attentional)

In the agent's substrate this provides the adrenergic premotor channel
distinct from the noradrenergic groups — engaged by hypoglycemia,
hemorrhage, hypoxia, and psychogenic stress, driving sympathoexcitation.

KEY FINDINGS
============
1. C1 adrenergic neurons in RVLM are the principal central source of
   adrenergic (PNMT+) sympathetic premotor drive — project to spinal
   IML for sympathetic preganglionic activation — [Reis et al. 1989,
    Annu Rev Neurosci 12:55, "Central neurogenic origin of acute
    arterial hypertension"]
2. C1 neurons drive glucose counter-regulation — fire in response to
   hypoglycemia, recruit hepatic glucose production via splanchnic
   sympathetic — [Madden Sved 2003, J Physiol 547:559, "Cardiovascular
    responses to hypotensive hemorrhage"] [Guyenet 2006,
    Nat Rev Neurosci 7:335, "The sympathetic control of blood pressure"]
3. C1 lesion impairs counter-regulatory response producing hypoglycemia-
   unawareness — clinical relevance — [Verberne et al. 2014, Auton
    Neurosci 182:23] [Verberne et al. 2016 Trends Endocrinol
    Metab 27:854]
4. C1 drives adrenal medullary epinephrine and recruits PVN-CRH for
   ACTH release — central node of fight-or-flight — [Saper
    2002, Annu Rev Neurosci 25:433, "The central autonomic nervous system"]
5. C1 distinct from A1 (NE not adrenaline; spinal IML target dominant)
   and from A5 (different stress profile) — [Guyenet 2006
    Nat Rev Neurosci 7:335]

INPUTS (from prior_results)
============================
- BaroreflexBalancer.rvlm_drive
- BaroreflexBalancer.cvlm_drive
- VitalCoreRegulator.sympathetic_tone
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.starvation_state
- CarotidBodyChemosensor.hypoxia_response_active
- StressActivationAxis.stress_active
- StressActivationAxis.cortisol_level
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- HemorrhageProxy.volume_loss (optional; default 0)
- HypoglycemiaProxy.glucose_deficit (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- c1_drive (0.0-1.0): C1 adrenergic output
- spinal_iml_sympathetic (0.0-1.0): C1 → spinal IML sympathetic premotor
- adrenal_epinephrine_drive (0.0-1.0): C1 → adrenal medullary EPI release
- glucose_counterreg_active (bool): hypoglycemia counter-regulation engaged
- pvn_acth_recruitment (0.0-1.0): C1 → PVN CRH recruitment
- bp_elevation_drive (0.0-1.0): cardiovascular pressor effect
- c1_state (str): "quiet" | "sympatho_excitation" | "hypoglycemia" | "hemorrhage" | "fight_flight"

brain_runner enrichment:
    c1 = all_results.get("C1AdrenergicRVLM", {})
    if c1:
        enrichments["brain_c1_drive"] = c1.get("c1_drive", 0.1)
        enrichments["brain_spinal_iml_symp"] = c1.get("spinal_iml_sympathetic", 0.0)
        enrichments["brain_adrenal_epi"] = c1.get("adrenal_epinephrine_drive", 0.0)
        enrichments["brain_glucose_counterreg"] = c1.get("glucose_counterreg_active", False)
        enrichments["brain_c1_state"] = c1.get("c1_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class C1AdrenergicRVLM(BrainMechanism):
    BASELINE = 0.15
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="C1AdrenergicRVLM",
            human_analog="C1 adrenergic RVLM (sympathetic + glucose counter-regulation)",
            layer="foundational",
        )
        self.state.setdefault("c1_drive", self.BASELINE)
        self.state.setdefault("spinal_iml_sympathetic", 0.0)
        self.state.setdefault("adrenal_epinephrine_drive", 0.0)
        self.state.setdefault("glucose_counterreg_active", False)
        self.state.setdefault("pvn_acth_recruitment", 0.0)
        self.state.setdefault("bp_elevation_drive", 0.0)
        self.state.setdefault("c1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _c1_drive_target(self, rvlm: float, sympathetic: float, hypoglycemia: float,
                          hypoxia: bool, hemorrhage: float, threat: bool,
                          cortisol: float) -> float:
        """C1 drive — sympathoexcitatory + glucose-emergency."""
        target = self.BASELINE + rvlm * 0.3 + max(0.0, sympathetic - 0.4) * 0.2
        target += hypoglycemia * 0.5
        if hypoxia:
            target += 0.20
        target += hemorrhage * 0.4
        if threat:
            target += 0.15
        target += max(0.0, cortisol - 0.5) * 0.2
        return min(1.0, target)

    def _spinal_iml(self, c1: float, sympathetic: float) -> float:
        """C1 → spinal IML sympathetic premotor."""
        return min(1.0, c1 * 0.7 + max(0.0, sympathetic - 0.4) * 0.3)

    def _adrenal_epi(self, c1: float, threat: bool, hypoglycemia: float) -> float:
        """C1 → adrenal medullary epinephrine release."""
        target = c1 * 0.6
        if threat:
            target += 0.20
        target += hypoglycemia * 0.3
        return min(1.0, target)

    def _glucose_counterreg(self, hypoglycemia: float, c1: float) -> bool:
        """Counter-regulation engaged on hypoglycemia + C1 firing."""
        return hypoglycemia > 0.40 and c1 > 0.45

    def _pvn_acth(self, c1: float, threat: bool, cortisol: float) -> float:
        """C1 → PVN CRH recruitment for ACTH release."""
        target = c1 * 0.4
        if threat:
            target += 0.10
        target += max(0.0, cortisol - 0.4) * 0.2
        return min(1.0, target)

    def _bp_elevation(self, spinal_iml: float, c1: float) -> float:
        """Cardiovascular pressor effect."""
        return min(1.0, spinal_iml * 0.6 + c1 * 0.3)

    def _classify_state(self, c1: float, hypoglycemia: float, hemorrhage: float,
                          threat: bool, sympathetic: float) -> str:
        if hypoglycemia > 0.5:
            return "hypoglycemia"
        if hemorrhage > 0.4:
            return "hemorrhage"
        if threat and c1 > 0.5:
            return "fight_flight"
        if sympathetic > 0.65 and c1 > 0.4:
            return "sympatho_excitation"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        baro = prior.get("BaroreflexBalancer", {})
        rvlm = float(baro.get("rvlm_drive", 0.30))

        vcr = prior.get("VitalCoreRegulator", {})
        sympathetic = float(vcr.get("sympathetic_tone", 0.5))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypoxia = bool(cb.get("hypoxia_response_active", False))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        hemorrhage_proxy = prior.get("HemorrhageProxy", {})
        hemorrhage = float(hemorrhage_proxy.get("volume_loss", 0.0))

        hypo_proxy = prior.get("HypoglycemiaProxy", {})
        hypoglycemia = float(hypo_proxy.get("glucose_deficit", 0.0))

        # Infer hypoglycemia from energy balance + starvation if no explicit signal
        if hypoglycemia == 0.0:
            if starvation:
                hypoglycemia = 0.7
            elif energy < -0.5:
                hypoglycemia = abs(energy) * 0.5

        # --- C1 drive ---
        c1_target = self._c1_drive_target(rvlm, sympathetic, hypoglycemia, hypoxia,
                                            hemorrhage, threat, cortisol)
        prev_c1 = float(self.state.get("c1_drive", self.BASELINE))
        new_c1 = self._smooth(prev_c1, c1_target)

        # --- Outputs ---
        spinal_iml = self._spinal_iml(new_c1, sympathetic)
        adrenal = self._adrenal_epi(new_c1, threat, hypoglycemia)
        counterreg = self._glucose_counterreg(hypoglycemia, new_c1)
        pvn_acth = self._pvn_acth(new_c1, threat, cortisol)
        bp = self._bp_elevation(spinal_iml, new_c1)

        state = self._classify_state(new_c1, hypoglycemia, hemorrhage, threat, sympathetic)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["c1_drive"] = round(new_c1, 4)
        self.state["spinal_iml_sympathetic"] = round(spinal_iml, 4)
        self.state["adrenal_epinephrine_drive"] = round(adrenal, 4)
        self.state["glucose_counterreg_active"] = counterreg
        self.state["pvn_acth_recruitment"] = round(pvn_acth, 4)
        self.state["bp_elevation_drive"] = round(bp, 4)
        self.state["c1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "c1_drive": round(new_c1, 4),
            "spinal_iml_sympathetic": round(spinal_iml, 4),
            "adrenal_epinephrine_drive": round(adrenal, 4),
            "glucose_counterreg_active": counterreg,
            "pvn_acth_recruitment": round(pvn_acth, 4),
            "bp_elevation_drive": round(bp, 4),
            "c1_state": state,
        }

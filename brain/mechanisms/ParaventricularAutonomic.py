"""
ParaventricularAutonomic — PVN Parvocellular Pre-autonomic Descending Output

NEURAL SUBSTRATE
================
The paraventricular nucleus of the hypothalamus (PVN) contains three distinct
neuronal populations: magnocellular neurosecretory neurons (releasing AVP/OT
into posterior pituitary), parvocellular neuroendocrine neurons (releasing
TRH/CRH into median eminence), and parvocellular pre-autonomic neurons.
This mechanism models the third population — pre-autonomic PVN neurons that
project descending axons to the rostral ventrolateral medulla (RVLM, the
sympathetic premotor zone) and to the thoracic intermediolateral cell column
(IML, the spinal sympathetic preganglionic neurons).

PVN pre-autonomic projection produces tonic excitatory drive on sympathetic
outflow toward the heart, blood vessels, and kidneys. PVN dysfunction is
implicated in essential hypertension, congestive heart failure, and stress-
related cardiovascular disease through sustained PVN-RVLM hyperactivity.

The pre-autonomic PVN is activated by hypothalamic stress signals (CRH from
within PVN itself, autocrine/paracrine), by limbic inputs (CeA, BNST), and
by ascending visceral afferents from NTS. It is restrained by GABAergic
local inhibition and by hippocampal feedback through indirect projections.

In the agent's substrate this produces the descending sympathetic-augmentation
signal — a slower, more sustained sympathetic recruitment than the acute
RVLM C1 pathway, more responsive to psychogenic and emotional stress.

KEY FINDINGS
============
1. PVN parvocellular pre-autonomic neurons project to RVLM and IML to
   modulate sympathetic outflow toward heart, vessels, kidneys —
   [Coote 2007; reviewed Frontiers Physiol 2022, doi:10.3389/fphys.2022.858941
    "PVN in Control of Blood Pressure and Variability"]
2. PVN pre-autonomic activity is excitatory in essential hypertension —
   sustained PVN-RVLM drive — [Pyner 2014; reviewed Frontiers 2022]
3. PVN integrates magnocellular, neuroendocrine, and pre-autonomic functions
   — [Iremonger et al. 2025, J Physiol 603:2389-2410, "PVN: a key node in
    the control of behavioural states," PMC12013795]
4. PVN parvocellular preautonomic neurons release a wide spectrum of
   neuropeptides (OXT, AVP, somatostatin, CRH, enkephalin, dynorphin) and
   exhibit diverse ion-channel signatures — [Frontiers Physiol 2018,
    doi:10.3389/fphys.2018.00760, "Ion Channels in the PVN"]
5. PVN-RVLM hyperactivity contributes to cardiovascular disease, including
   hypertension and heart failure — [Coote Physiology 2007; reviewed
    Stocker et al. 2009, PMC2682920 "PVN: Potential Target for Integrative
    Treatment of Autonomic Dysfunction"]

INPUTS (from prior_results)
============================
- StressActivationAxis.cortisol_level
- StressActivationAxis.stress_active
- CRHStressDispatcher.crh_release
- CRHStressDispatcher.amygdala_pvn_drive
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- VitalCoreRegulator.sympathetic_tone
- VitalCoreRegulator.parasympathetic_tone
- VitalCoreRegulator.survival_threat_level
- ArousalRegulator.tonic_level
- CircadianTimer.circadian_phase (PVN follows a mild circadian rhythm)

OUTPUTS (to brain_runner enrichment)
=====================================
- pvn_preautonomic_drive (0.0-1.0): net pre-autonomic drive
- pvn_to_rvlm_drive (0.0-1.0): RVLM sympathetic premotor output
- pvn_to_iml_drive (0.0-1.0): IML spinal sympathetic preganglionic drive
- pvn_autonomic_state (str): "sympathetic_engaged" | "balanced" | "parasympathetic_dominant" | "stress_engaged" | "threat_active"
- sympathetic_bias (0.0-1.0): net autonomic balance toward sympathetic
- sustained_sympathetic_recruitment (bool): chronic high drive pattern
- gaba_inhibition_strength (0.0-1.0): local restraint capacity
- pvn_dysregulation_marker (bool): chronic PVN hyperactivity
- neuropeptide_cocktail_proxy (dict): relative contributions of AVP/OT/CRH/ENK in projection

brain_runner enrichment:
    pa = all_results.get("ParaventricularAutonomic", {})
    if pa:
        enrichments["brain_pvn_preautonomic"] = pa.get("pvn_preautonomic_drive", 0.4)
        enrichments["brain_pvn_to_rvlm"] = pa.get("pvn_to_rvlm_drive", 0.0)
        enrichments["brain_sustained_sympathetic"] = pa.get("sustained_sympathetic_recruitment", False)
        enrichments["brain_sympathetic_bias"] = pa.get("sympathetic_bias", 0.5)
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularAutonomic(BrainMechanism):
    BASELINE_DRIVE = 0.40
    SUSTAINED_THRESHOLD_TICKS = 60
    DYSREGULATION_THRESHOLD_TICKS = 120
    SMOOTH = 0.20
    NEUROPEPTIDE_BASELINE = 0.25

    def __init__(self):
        super().__init__(
            name="ParaventricularAutonomic_ParaventricularAutonomic",
            human_analog="PVN parvocellular pre-autonomic descending sympathetic driver",
            layer="foundational",
        )
        self.state.setdefault("pvn_preautonomic_drive", self.BASELINE_DRIVE)
        self.state.setdefault("pvn_to_rvlm_drive", 0.0)
        self.state.setdefault("pvn_to_iml_drive", 0.0)
        self.state.setdefault("pvn_autonomic_state", "balanced")
        self.state.setdefault("sympathetic_bias", 0.50)
        self.state.setdefault("sustained_sympathetic_recruitment", False)
        self.state.setdefault("gaba_inhibition_strength", 0.5)
        self.state.setdefault("pvn_dysregulation_marker", False)
        self.state.setdefault("neuropeptide_cocktail", {
            "avp_contribution": self.NEUROPEPTIDE_BASELINE,
            "ot_contribution": self.NEUROPEPTIDE_BASELINE,
            "crh_contribution": 0.0,
            "enk_contribution": 0.0,
        })
        self.state.setdefault("high_drive_streak", 0)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _compute_excitation(self, crh: float, amyg_pvn: float,
                            threat: bool, threat_level: float,
                            valence_intensity: float) -> float:
        """Sources of PVN pre-autonomic excitation.
        Multiple parallel pathways converge on pre-autonomic neurons.
        """
        excitation = 0.0
        # Autocrine/paracrine CRH within PVN (stress-related)
        excitation += crh * 0.40
        # CeA/BNST limbic input
        excitation += amyg_pvn * 0.30
        # Explicit threat signal
        if threat:
            excitation += 0.15
        # Survival threat magnitude
        excitation += threat_level * 0.20
        # Valence intensity as proxy for limbic urgency
        excitation += max(0.0, valence_intensity - 0.5) * 0.15
        return min(1.0, excitation)

    def _gaba_restraint(self, baseline_arousal: float, parasympathetic: float) -> float:
        """Local GABAergic inhibition strength.
        Stronger when parasympathetic dominant; weaker under sustained arousal.
        """
        if parasympathetic > 0.6:
            return min(1.0, parasympathetic * 0.7)
        if baseline_arousal > 0.7:
            return max(0.10, 0.5 - (baseline_arousal - 0.7) * 0.5)
        return 0.5

    def _project_to_rvlm(self, drive: float) -> float:
        """PVN → RVLM excitatory drive — sustained sympathetic premotor input."""
        return min(1.0, drive * 0.85)

    def _project_to_iml(self, drive: float, sustained: bool) -> float:
        """PVN → IML direct projection — increases under sustained activation."""
        if sustained:
            return min(1.0, drive * 0.75)
        return drive * 0.45

    def _neuropeptide_cocktail(self, crh: float, symp_tone: float,
                               para_tone: float) -> dict:
        """Pre-autonomic PVN releases a peptide mix modulated by stress/autonomic tone.
        AVP rises with sympathetic tone; OT with parasympathetic; CRH with stress.
        """
        avp = self.NEUROPEPTIDE_BASELINE + symp_tone * 0.4 + crh * 0.3
        ot = self.NEUROPEPTIDE_BASELINE + para_tone * 0.35 - crh * 0.15
        crh_out = max(0.0, crh * 0.8 - para_tone * 0.2)
        enk = max(0.0, (symp_tone - 0.5) * 0.3)
        return {
            "avp_contribution": round(min(1.0, avp), 3),
            "ot_contribution": round(min(1.0, max(0.0, ot)), 3),
            "crh_contribution": round(min(1.0, crh_out), 3),
            "enk_contribution": round(min(1.0, enk), 3),
        }

    def _sympathetic_bias(self, drive: float, para_tone: float, symp_tone: float) -> float:
        """Net autonomic bias — 0 = parasympathetic, 1 = sympathetic."""
        return min(1.0, max(0.0, drive * 0.6 + symp_tone * 0.3 - para_tone * 0.2))

    def _classify_state(self, symp_bias: float, sustained: bool, threat: bool) -> str:
        if threat and symp_bias > 0.65:
            return "threat_active"
        if sustained and symp_bias > 0.60:
            return "stress_engaged"
        if symp_bias > 0.60:
            return "sympathetic_engaged"
        if symp_bias < 0.40:
            return "parasympathetic_dominant"
        return "balanced"

    def _detect_sustained(self, streak: int) -> bool:
        return streak > self.SUSTAINED_THRESHOLD_TICKS

    def _detect_dysregulation(self, streak: int) -> bool:
        return streak > self.DYSREGULATION_THRESHOLD_TICKS

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))
        stress_active = bool(stress.get("stress_active", False))

        crh_disp = prior.get("CRHStressDispatcher", {})
        crh_release = float(crh_disp.get("crh_release", 0.0))
        amyg_pvn = float(crh_disp.get("amygdala_pvn_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Compute excitation ---
        excitation = self._compute_excitation(
            crh_release, amyg_pvn, threat_signal, survival_threat, valence_intensity
        )

        # --- GABAergic restraint ---
        gaba_strength = self._gaba_restraint(tonic, para_tone)

        # --- Compute pre-autonomic drive target ---
        target = self.BASELINE_DRIVE + excitation - gaba_strength * 0.30
        if stress_active:
            target += 0.08
        target = max(0.05, min(0.98, target))

        prev_drive = float(self.state.get("pvn_preautonomic_drive", self.BASELINE_DRIVE))
        new_drive = self._smooth(prev_drive, target)

        # --- Sympathetic bias ---
        bias = self._sympathetic_bias(new_drive, para_tone, symp_tone)

        # --- Track sustained activation ---
        prev_streak = int(self.state.get("high_drive_streak", 0))
        if new_drive > 0.65:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 1)

        sustained = self._detect_sustained(streak)
        dysreg = self._detect_dysregulation(streak)

        # --- Project to downstream targets ---
        rvlm_drive = self._project_to_rvlm(new_drive)
        iml_drive = self._project_to_iml(new_drive, sustained)

        # --- Neuropeptide cocktail ---
        cocktail = self._neuropeptide_cocktail(crh_release, symp_tone, para_tone)

        # --- State classification ---
        pvn_state = self._classify_state(bias, sustained, threat_signal)

        # --- History ---
        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_drive, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pvn_preautonomic_drive"] = round(new_drive, 4)
        self.state["pvn_to_rvlm_drive"] = round(rvlm_drive, 4)
        self.state["pvn_to_iml_drive"] = round(iml_drive, 4)
        self.state["pvn_autonomic_state"] = pvn_state
        self.state["sympathetic_bias"] = round(bias, 4)
        self.state["sustained_sympathetic_recruitment"] = sustained
        self.state["gaba_inhibition_strength"] = round(gaba_strength, 4)
        self.state["pvn_dysregulation_marker"] = dysreg
        self.state["neuropeptide_cocktail"] = cocktail
        self.state["high_drive_streak"] = streak
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pvn_preautonomic_drive": round(new_drive, 4),
            "pvn_to_rvlm_drive": round(rvlm_drive, 4),
            "pvn_to_iml_drive": round(iml_drive, 4),
            "pvn_autonomic_state": pvn_state,
            "sympathetic_bias": round(bias, 4),
            "sustained_sympathetic_recruitment": sustained,
            "gaba_inhibition_strength": round(gaba_strength, 4),
            "pvn_dysregulation_marker": dysreg,
        }
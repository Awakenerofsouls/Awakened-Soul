"""
DorsalMotorVagusOutput — DMV Vagal Preganglionic Parasympathetic Motor Output

NEURAL SUBSTRATE
================
The dorsal motor nucleus of the vagus (DMV) is located in the dorsomedial
caudal medulla, just below the floor of the fourth ventricle. It is the
largest source of preganglionic parasympathetic motoneurons in the lower
brainstem and provides the principal vagal motor output to abdominal viscera
— stomach, liver, pancreas, small intestine, and proximal large intestine.
DMV preganglionic neurons release acetylcholine onto post-ganglionic neurons
embedded within the gut wall (myenteric and submucosal plexuses), which in
turn drive smooth muscle, secretory, and absorptive activity.

DMV firing produces the "rest-and-digest" gastrointestinal pattern:
gastric peristalsis, hepatic glycogenesis and bile secretion, pancreatic
exocrine and endocrine secretion (including insulin), and intestinal motility.
DMV activation simultaneously inhibits heart rate (via vagal-cardiac
projection that overlaps with NA cardiac vagal motoneurons) and suppresses
adrenal medullary catecholamine release.

DMV is functionally coupled to NTS — visceral afferent input enters via
the tractus solitarius, terminates in NTS, then projects to adjacent DMV
through GABAergic, glutamatergic, or noradrenergic interneurons. This
NTS-DMV reflex arc is the substrate of vago-vagal reflexes (gastric
accommodation, pancreatic insulin release, baroreflex bradycardia).

Insulin reduces DMV gastric-related neuron excitability, providing a
peripheral metabolic feedback signal that adjusts vagal output to nutritional
state. Recent work (Tsang et al. 2024 iScience) shows DMV vagal neurons
can elicit bradycardia and reduce anxiety-like behavior via M2 muscarinic
mechanisms.

In Nova's substrate this is the digestive-rest output channel, complementing
NA's cardiac-vagal channel. High DMV drive = rest-digest dominant; low DMV
drive = sympathetic-active state with suppressed digestion.

KEY FINDINGS
============
1. DMV is the largest source of preganglionic parasympathetic motoneurons
   in the lower brainstem; provides vagal motor output to GI tract, liver,
   pancreas — [reviewed StatPearls "Neuroanatomy, Vagal Nerve Nuclei" NBK545209;
    Travagli & Anselmi 2016, "Brainstem circuits regulating gastric function"
    PMC3062484]
2. DMV neurons release ACh on enteric postganglionic neurons (cholinergic
   and NO/VIP), driving GI motility and secretion — [Travagli et al. 2011,
    PMC3221413, "Spatial organization of DMV neurons synapsing with intragastric
    cholinergic and nitric oxide/VIP neurons"]
3. NTS-DMV reflex arc: visceral afferents → NTS → DMV via glutamate, GABA,
   or NE — substrate of vago-vagal reflexes — [Travagli & Anselmi 2016,
    PMC3062484]
4. Insulin reduces DMV gastric-related neuron excitability, integrating
   peripheral metabolic feedback into vagal output — [Browning Travagli 2012,
    PMC3469664, "Insulin reduces excitation in gastric-related neurons of DMV"]
5. DMV vagal neurons elicit bradycardia and reduce anxiety-like behavior
   through M2-dependent mechanism — [Tsang et al. 2024, iScience 27:108985,
    doi:10.1016/j.isci.2024.108985]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.parasympathetic_tone
- VitalCoreRegulator.sympathetic_tone
- AppetiteNPYBalancer.post_prandial
- AppetiteNPYBalancer.energy_balance_signed
- ArousalRegulator.tonic_level
- StressActivationAxis.stress_active
- ValenceTagger.threat_signal

OUTPUTS (to brain_runner enrichment)
=====================================
- dmv_drive (0.0-1.0): DMV preganglionic firing proxy
- gi_motility_drive (0.0-1.0)
- pancreatic_secretion (0.0-1.0): exocrine + insulin proxy
- hepatic_glycogenesis (0.0-1.0)
- vago_vagal_reflex_active (bool): NTS-DMV reflex engaged
- digestive_rest_state (str): "rest_digest" | "active" | "stress_inhibited"
- insulin_feedback_modulation (signed -1..+1)

brain_runner enrichment:
    dmv = all_results.get("DorsalMotorVagusOutput", {})
    if dmv:
        enrichments["brain_dmv_drive"] = dmv.get("dmv_drive", 0.5)
        enrichments["brain_gi_motility"] = dmv.get("gi_motility_drive", 0.5)
        enrichments["brain_digestive_rest_state"] = dmv.get("digestive_rest_state", "active")
"""

from brain.base_mechanism import BrainMechanism


class DorsalMotorVagusOutput(BrainMechanism):
    BASELINE_DRIVE = 0.50
    POST_PRANDIAL_BOOST = 0.20
    STRESS_INHIBITION = 0.30
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="DorsalMotorVagusOutput",
            human_analog="DMV vagal preganglionic parasympathetic motor output",
            layer="foundational",
        )
        self.state.setdefault("dmv_drive", self.BASELINE_DRIVE)
        self.state.setdefault("gi_motility_drive", 0.5)
        self.state.setdefault("pancreatic_secretion", 0.3)
        self.state.setdefault("hepatic_glycogenesis", 0.3)
        self.state.setdefault("vago_vagal_reflex_active", False)
        self.state.setdefault("digestive_rest_state", "active")
        self.state.setdefault("insulin_feedback_modulation", 0.0)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _baseline_modulation(self, parasympathetic: float, sympathetic: float) -> float:
        """DMV drive parallels parasympathetic, anti-correlates with sympathetic."""
        return self.BASELINE_DRIVE + (parasympathetic - 0.5) * 0.5 - (sympathetic - 0.5) * 0.4

    def _post_prandial_drive(self, post_prandial: bool) -> float:
        """Post-meal vago-vagal reflex drives DMV firing for accommodation, secretion."""
        return self.POST_PRANDIAL_BOOST if post_prandial else 0.0

    def _stress_suppression(self, stress: bool, threat: bool, tonic: float) -> float:
        """Stress and threat suppress DMV (sympathetic dominance, fight-or-flight)."""
        suppression = 0.0
        if stress:
            suppression += 0.15
        if threat:
            suppression += 0.10
        if tonic > 0.75:
            suppression += 0.10
        return min(self.STRESS_INHIBITION, suppression)

    def _insulin_feedback(self, energy_balance: float) -> float:
        """Browning & Travagli 2012: insulin reduces DMV excitability when fed.
        Returns signed modulation: + reduces DMV (post-meal insulin), - increases DMV (fasted).
        """
        if energy_balance > 0.3:
            return -0.10  # post-meal insulin reduces DMV
        if energy_balance < -0.3:
            return 0.05   # fasted state mildly increases DMV
        return 0.0

    def _gi_motility_estimate(self, drive: float, post_prandial: bool) -> float:
        """GI motility tracks DMV drive but boosts during digestion."""
        if post_prandial:
            return min(1.0, drive * 1.1)
        return drive

    def _pancreatic_secretion(self, drive: float, post_prandial: bool, energy: float) -> float:
        """Pancreatic exocrine + insulin secretion."""
        base = drive * 0.6
        if post_prandial:
            base += 0.20
        if energy > 0.3:
            base += 0.10
        return min(1.0, base)

    def _hepatic_glycogenesis(self, drive: float, energy: float) -> float:
        """Liver glycogen synthesis under fed-state vagal drive."""
        if energy < -0.2:
            return drive * 0.3   # fasted — glycogen breakdown not synthesis
        return min(1.0, drive * 0.7 + max(0.0, energy) * 0.3)

    def _classify_state(self, drive: float, stress: bool, post_prandial: bool) -> str:
        if stress and drive < 0.4:
            return "stress_inhibited"
        if post_prandial and drive > 0.5:
            return "rest_digest"
        return "active"

    def _vagovagal_reflex(self, post_prandial: bool, drive: float) -> bool:
        """Active during post-prandial accommodation."""
        return post_prandial and drive > 0.5

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))

        appetite = prior.get("AppetiteNPYBalancer", {})
        post_prandial = bool(appetite.get("post_prandial", False))
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))

        # --- Compute target drive ---
        baseline = self._baseline_modulation(para_tone, symp_tone)
        boost = self._post_prandial_drive(post_prandial)
        suppress = self._stress_suppression(stress_active, threat_signal, tonic)
        insulin_mod = self._insulin_feedback(energy_balance)

        target = baseline + boost - suppress + insulin_mod
        target = max(0.05, min(0.95, target))

        prev_drive = float(self.state.get("dmv_drive", self.BASELINE_DRIVE))
        new_drive = self._smooth(prev_drive, target)

        # --- Outputs ---
        gi_motility = self._gi_motility_estimate(new_drive, post_prandial)
        pancreatic = self._pancreatic_secretion(new_drive, post_prandial, energy_balance)
        hepatic = self._hepatic_glycogenesis(new_drive, energy_balance)
        vagovagal = self._vagovagal_reflex(post_prandial, new_drive)
        state = self._classify_state(new_drive, stress_active, post_prandial)

        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_drive, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dmv_drive"] = round(new_drive, 4)
        self.state["gi_motility_drive"] = round(gi_motility, 4)
        self.state["pancreatic_secretion"] = round(pancreatic, 4)
        self.state["hepatic_glycogenesis"] = round(hepatic, 4)
        self.state["vago_vagal_reflex_active"] = vagovagal
        self.state["digestive_rest_state"] = state
        self.state["insulin_feedback_modulation"] = round(insulin_mod, 4)
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dmv_drive": round(new_drive, 4),
            "gi_motility_drive": round(gi_motility, 4),
            "pancreatic_secretion": round(pancreatic, 4),
            "hepatic_glycogenesis": round(hepatic, 4),
            "vago_vagal_reflex_active": vagovagal,
            "digestive_rest_state": state,
            "insulin_feedback_modulation": round(insulin_mod, 4),
        }

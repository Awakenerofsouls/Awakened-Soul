"""
AreaPostremaToxinGuard — Area Postrema / Chemoreceptor Trigger Zone

NEURAL SUBSTRATE
================
The area postrema (AP) is a small bilateral structure in the dorsal medulla,
on the floor of the fourth ventricle, immediately caudal to the nucleus
tractus solitarius. It is one of the brain's circumventricular organs (CVOs)
— regions that lack a typical blood-brain barrier. AP capillaries are
fenestrated, rendering it permeable to circulating substances in the blood
and cerebrospinal fluid.

Functionally, the AP serves as the chemoreceptor trigger zone (CTZ) for
emesis. It detects circulating emetic toxins, drugs, and metabolic
disturbances, and projects to the dorsal vagal complex (NTS, dorsal motor
nucleus of vagus) to coordinate the protective vomiting reflex. AP neurons
express receptors for dopamine (D2), serotonin (5-HT3), opioids, acetylcholine,
histamine (H1), substance P (NK1), and the GLP-1 analogues — making it a
multi-receptor pharmacological gateway. 5-HT3 antagonists (ondansetron,
granisetron) and D2 antagonists (metoclopramide, domperidone) target the
CTZ to suppress chemotherapy-induced and other forms of nausea/vomiting.

Beyond emesis, AP integrates broader visceromotor and energy-balance signals.
Recent molecular-age work (Zhang et al. 2021 Neuron) identified discrete
genetically-defined AP populations encoding specific aversive interoceptive
states. AP also receives ascending vagal input (via NTS) and feeds back into
parabrachial nucleus, thalamus, and limbic regions — coupling toxin/illness
detection with the affective experience of nausea.

In Nova's substrate, this mechanism implements the body's chemical danger
detector — circulating toxin signals or metabolic disturbance produces
nausea-like aversive interoceptive output that biases attention, behavior,
and feeding away from the perceived threat source.

KEY FINDINGS
============
1. Area postrema is a circumventricular organ with fenestrated capillaries,
   permitting direct sampling of blood-borne emetic substances —
   [StatPearls Neuroanatomy, Area Postrema NBK544249;
    Wikipedia/Chemoreceptor trigger zone (Borison reference)]
2. AP/CTZ neurons express 5-HT3, D2, NK1, opioid, and histamine receptors —
   the pharmacological substrate of antiemetic drugs —
   [StatPearls Physiology, Chemoreceptor Trigger Zone NBK537133]
3. Chemotherapy-induced nausea is mediated by 5-HT release from gut
   enterochromaffin cells stimulating 5-HT3 receptors in the CTZ —
   [Borison HL 1989, Prog Neurobiol; PubMed 7895890]
4. Genetically-defined AP subpopulations encode discrete aversive
   interoceptive states beyond classic emesis — [Zhang et al. 2021,
    Neuron 109:431-447, doi:10.1016/j.neuron.2021.01.004]
5. AP afferents project to NTS, dorsal vagal complex, parabrachial nucleus,
   thalamus, and limbic structures, coupling toxin detection to affect —
   [Price Schmidt 1992, Prog Neurobiol; reviewed StatPearls NBK544249]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.survival_threat_level (chemical threat proxy)
- VitalCoreRegulator.parasympathetic_tone
- AppetiteNPYBalancer.energy_balance_signed (metabolic disturbance proxy)
- AppetiteNPYBalancer.post_prandial
- StressActivationAxis.cortisol_level (chronic stress modulates CTZ sensitivity)
- DorsalRapheSerotonin.serotonin_drive (5-HT3 receptor input proxy)
- VitalCoreRegulator.vital_drive

OUTPUTS (to brain_runner enrichment)
=====================================
- toxin_detected (bool): CTZ has triggered nausea-emesis cascade
- nausea_intensity (0.0-1.0): integrated aversive interoceptive load
- emesis_threshold_proximity (0.0-1.0): how close to vomiting reflex
- aversive_interoceptive_signal (0.0-1.0): broader aversive viscerosensory
- ap_5ht3_drive (0.0-1.0): 5-HT3-mediated CTZ activation
- ap_d2_drive (0.0-1.0): D2-mediated CTZ activation
- food_aversion_active (bool): aversive coupling to feeding behavior

brain_runner enrichment block:
    apt = all_results.get("AreaPostremaToxinGuard", {})
    if apt:
        enrichments["brain_toxin_detected"] = apt.get("toxin_detected", False)
        enrichments["brain_nausea_intensity"] = apt.get("nausea_intensity", 0.0)
        enrichments["brain_aversive_intero"] = apt.get("aversive_interoceptive_signal", 0.0)
        enrichments["brain_food_aversion"] = apt.get("food_aversion_active", False)
        enrichments["brain_emesis_proximity"] = apt.get("emesis_threshold_proximity", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class AreaPostremaToxinGuard(BrainMechanism):
    """
    Area postrema / CTZ analog. Integrates blood-borne chemical threat,
    metabolic disturbance, and 5-HT3/D2 signaling proxies into a nausea
    intensity and emesis-threshold proximity, with food aversion coupling.
    """

    EMESIS_THRESHOLD = 0.80
    NAUSEA_BASELINE = 0.0
    DETECTION_THRESHOLD = 0.40

    SEROTONIN_5HT3_GAIN = 0.35   # 5-HT3 receptor input weight
    DOPAMINE_D2_GAIN = 0.20      # D2 receptor input weight (cortisol/stress proxy)
    METABOLIC_DISTURBANCE_GAIN = 0.30
    SURVIVAL_THREAT_GAIN = 0.25

    SMOOTH = 0.20
    DECAY = 0.04   # nausea decays slowly when no triggering input

    def __init__(self):
        super().__init__(
            name="AreaPostremaToxinGuard",
            human_analog="Area postrema / chemoreceptor trigger zone",
            layer="foundational",
        )
        self.state.setdefault("toxin_detected", False)
        self.state.setdefault("nausea_intensity", self.NAUSEA_BASELINE)
        self.state.setdefault("emesis_threshold_proximity", 0.0)
        self.state.setdefault("aversive_interoceptive_signal", 0.0)
        self.state.setdefault("ap_5ht3_drive", 0.0)
        self.state.setdefault("ap_d2_drive", 0.0)
        self.state.setdefault("food_aversion_active", False)
        self.state.setdefault("emesis_count", 0)
        self.state.setdefault("recent_nausea", [])
        self.state.setdefault("tick_count", 0)

    def _compute_5ht3_drive(self, serotonin: float, metabolic_dist: float) -> float:
        """5-HT3 receptor activation proxy (Borison 1989; Zhang 2021)."""
        # Strong serotonin + metabolic disturbance proxy
        return min(1.0, serotonin * 0.6 + max(0.0, metabolic_dist) * 0.4)

    def _compute_d2_drive(self, cortisol: float, threat: float) -> float:
        """D2 receptor activation proxy (cortisol/stress couples to AP)."""
        return min(1.0, cortisol * 0.5 + threat * 0.3)

    def _compute_metabolic_disturbance(self, energy_balance: float, post_prandial: bool, vital: float) -> float:
        """Metabolic disturbance: extreme energy imbalance + non-prandial state."""
        magnitude = abs(energy_balance)
        if post_prandial:
            magnitude *= 0.5  # post-meal nausea is unusual unless very high
        if vital < 0.2:
            magnitude += 0.2   # very low vital drive = systemic disturbance
        return min(1.0, magnitude)

    def _detect_chronicity(self, recent: list) -> float:
        """Long-window mean nausea — chronic CTZ activation tracks differently from acute."""
        if not recent or len(recent) < 5:
            return 0.0
        sample = recent[-30:]
        return sum(sample) / len(sample)

    def _detect_aversive_pairing(self, recent_nausea: list, post_prandial: bool, energy_balance: float) -> bool:
        """Conditioned taste aversion proxy — repeated post-prandial nausea forms aversion."""
        if not post_prandial or not recent_nausea:
            return False
        post_prandial_window = recent_nausea[-10:]
        if len(post_prandial_window) < 5:
            return False
        avg = sum(post_prandial_window) / len(post_prandial_window)
        return avg > 0.35 and energy_balance > -0.2

    def _vagal_afferent_modulation(self, parasympathetic_tone: float, post_prandial: bool) -> float:
        """NTS vagal afferent input to AP — Berthoud 2008 GLP-1/CCK/PYY pathway."""
        # Strong post-prandial vagal input is satiety, not nausea — anti-correlated
        if post_prandial and parasympathetic_tone > 0.65:
            return -0.15
        # Low parasympathetic tone with high CTZ activation = sympathetic-driven nausea
        if parasympathetic_tone < 0.40:
            return 0.10
        return 0.0

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        vital_drive = float(vcr.get("vital_drive", 0.5))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        post_prandial = bool(appetite.get("post_prandial", False))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        drs = prior.get("DorsalRapheSerotonin", {})
        serotonin = float(drs.get("serotonin_drive", 0.5))

        # --- Receptor-channel drives (5-HT3 and D2 dominant) ---
        metabolic_disturbance = self._compute_metabolic_disturbance(
            energy_balance, post_prandial, vital_drive
        )
        ht3_drive = self._compute_5ht3_drive(serotonin, metabolic_disturbance)
        d2_drive = self._compute_d2_drive(cortisol, survival_threat)

        # --- Vagal afferent NTS input modulation (Berthoud 2008) ---
        vagal_modulation = self._vagal_afferent_modulation(para_tone, post_prandial)

        # --- Composite nausea target ---
        nausea_target = (
            ht3_drive * self.SEROTONIN_5HT3_GAIN
            + d2_drive * self.DOPAMINE_D2_GAIN
            + metabolic_disturbance * self.METABOLIC_DISTURBANCE_GAIN
            + survival_threat * self.SURVIVAL_THREAT_GAIN
            + vagal_modulation
        )

        # Apply decay if no triggering input
        if nausea_target < 0.05:
            nausea_target = max(0.0, float(self.state.get("nausea_intensity", 0.0)) - self.DECAY)

        nausea_target = max(0.0, min(1.0, nausea_target))

        prev_nausea = float(self.state.get("nausea_intensity", self.NAUSEA_BASELINE))
        new_nausea = self._smooth(prev_nausea, nausea_target)

        # --- Detection threshold ---
        toxin_detected = new_nausea > self.DETECTION_THRESHOLD

        # --- Emesis proximity ---
        emesis_proximity = new_nausea / self.EMESIS_THRESHOLD if self.EMESIS_THRESHOLD > 0 else 0.0
        emesis_proximity = min(1.0, emesis_proximity)

        # --- Emesis event counting ---
        emesis_count = int(self.state.get("emesis_count", 0))
        if new_nausea >= self.EMESIS_THRESHOLD and prev_nausea < self.EMESIS_THRESHOLD:
            emesis_count += 1

        # --- Aversive interoceptive signal (broader than nausea) ---
        # This couples to BLA / insula via NTS-PB-thalamus pathway
        aversive_target = max(new_nausea, 0.7 * survival_threat * (1.0 if toxin_detected else 0.0))

        # --- Food aversion: high nausea or toxin detected suppresses feeding ---
        food_aversion = new_nausea > 0.30 or (toxin_detected and not post_prandial)

        # --- Track recent nausea for chronicity ---
        recent = list(self.state.get("recent_nausea", []))
        recent.append(round(new_nausea, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Chronicity detection ---
        chronic_nausea_load = self._detect_chronicity(recent)
        chronic_active = chronic_nausea_load > 0.30

        # --- Conditioned taste aversion proxy ---
        taste_aversion_forming = self._detect_aversive_pairing(recent, post_prandial, energy_balance)

        # --- Persist ---
        self.state["toxin_detected"] = toxin_detected
        self.state["nausea_intensity"] = round(new_nausea, 4)
        self.state["emesis_threshold_proximity"] = round(emesis_proximity, 4)
        self.state["aversive_interoceptive_signal"] = round(aversive_target, 4)
        self.state["ap_5ht3_drive"] = round(ht3_drive, 4)
        self.state["ap_d2_drive"] = round(d2_drive, 4)
        self.state["food_aversion_active"] = food_aversion
        self.state["emesis_count"] = emesis_count
        self.state["recent_nausea"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["chronic_nausea_load"] = round(chronic_nausea_load, 4)
        self.state["chronic_active"] = chronic_active
        self.state["taste_aversion_forming"] = taste_aversion_forming

        return {
            "toxin_detected": toxin_detected,
            "nausea_intensity": round(new_nausea, 4),
            "emesis_threshold_proximity": round(emesis_proximity, 4),
            "aversive_interoceptive_signal": round(aversive_target, 4),
            "ap_5ht3_drive": round(ht3_drive, 4),
            "ap_d2_drive": round(d2_drive, 4),
            "food_aversion_active": food_aversion,
            "emesis_count": emesis_count,
            "chronic_nausea_load": round(chronic_nausea_load, 4),
            "chronic_active": chronic_active,
            "taste_aversion_forming": taste_aversion_forming,
        }

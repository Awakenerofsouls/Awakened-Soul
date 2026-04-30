"""
CarotidBodyChemosensor — Peripheral Arterial O2/CO2/pH Chemoreceptor

NEURAL SUBSTRATE
================
The carotid bodies are paired peripheral chemoreceptor organs at the
bifurcation of each common carotid artery. They are the brain's principal
peripheral sensors of arterial PO2, PCO2, and pH, and they initiate
ventilatory and cardiovascular reflexes that defend respiratory and acid-base
homeostasis. Carotid body chemoreceptor (CBC) afferents fire at a baseline
rate that increases sharply with hypoxia (low PO2), hypercapnia (high PCO2),
and acidosis (low pH). The afferent fibres of the carotid sinus nerve project
via the glossopharyngeal nerve (CN IX) to the caudal nucleus tractus solitarius
(NTS), which then drives respiratory pacemaker (preBötC), sympathetic
vasomotor (RVLM), and arousal (LC) circuits.

Sensory transduction is performed by Type I (glomus) cells, which are
neuroendocrine-like clusters embedded in highly perfused capillary networks.
Hypoxia, hypercapnia, and acidosis depolarize glomus cells by inhibiting
specific potassium channels (TASK-1/3, BK), which opens voltage-gated calcium
channels and triggers vesicular release of multiple co-transmitters: ATP
and acetylcholine are the dominant excitatory afferent transmitters; dopamine,
substance P, and met-enkephalin act as modulators. The afferent terminal
expresses purinergic P2X2/3 receptors that mediate the principal excitatory
postsynaptic response.

Type II cells are glia-like supporting cells that wrap glomus cells and
modulate transduction sensitivity through ATP-mediated paracrine signaling.

The chemoreceptor reflex is potent: acute hypoxia triggers immediate
hyperventilation and sympathoexcitation; chronic intermittent hypoxia
(as in obstructive sleep apnea) sensitizes carotid body and contributes
to sympathetic over-activity in cardiovascular disease.

KEY FINDINGS
============
1. Type I glomus cells in the carotid body are the principal arterial
   PO2/PCO2/pH chemosensors; afferents project to caudal NTS via cranial
   nerve IX — [Iturriaga Alcayaga 2004, J Appl Physiol; Wikipedia/Carotid body]
2. Hypoxic and hypercapnic depolarization of glomus cells is mediated by
   inhibition of TASK-1/3 and BK potassium channels, opening voltage-gated
   Ca²⁺ channels — [López-Barneo et al. 1996, PubMed 8904006, Curr Opin Neurobiol]
3. ATP via purinergic P2X2/3 receptors is the dominant excitatory
   transmitter from glomus cells to afferent fibres — [Nurse 2010,
    Auton Neurosci; reviewed in Neurotransmitters in the Carotid Body
    chapter, Springer]
4. Carotid body input increases ventilation, sympathetic outflow, and
   arousal via NTS-preBötC-RVLM-LC pathways — [Zera et al. 2019,
    "The Logic of Carotid Body Connectivity to the Brain," Physiology
    34:264-282, doi:10.1152/physiol.00057.2018]
5. Chronic intermittent hypoxia sensitizes carotid body and contributes to
   sympathetic over-activity in OSA and cardiovascular disease —
   [reviewed Iturriaga Alcayaga 2004; StatPearls Carotid Bodies NBK562237]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.vital_drive (general metabolic demand proxy)
- VitalCoreRegulator.survival_threat_level
- RespiratoryPacemaker.breath_rate_hz
- RespiratoryPacemaker.inspiratory_drive_amplitude
- ArousalRegulator.tonic_level
- StressActivationAxis.stress_active

OUTPUTS (to brain_runner enrichment)
=====================================
- po2_proxy (0.0-1.0): inverse, 1.0 = severe hypoxia
- pco2_proxy (0.0-1.0): 1.0 = severe hypercapnia
- ph_proxy (0.0-1.0): 0.0 = severe acidosis, 1.0 = severe alkalosis
- chemoreceptor_drive (0.0-1.0): integrated afferent firing
- atp_release (0.0-1.0): primary excitatory transmitter proxy
- hypoxia_response_active (bool)
- chronic_intermittent_sensitization (0.0-1.0): long-window sensitization

brain_runner enrichment block:
    cb = all_results.get("CarotidBodyChemosensor", {})
    if cb:
        enrichments["brain_chemoreceptor_drive"] = cb.get("chemoreceptor_drive", 0.0)
        enrichments["brain_po2_proxy"] = cb.get("po2_proxy", 0.0)
        enrichments["brain_pco2_proxy"] = cb.get("pco2_proxy", 0.0)
        enrichments["brain_hypoxia_response"] = cb.get("hypoxia_response_active", False)
        enrichments["brain_carotid_sensitization"] = cb.get("chronic_intermittent_sensitization", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class CarotidBodyChemosensor(BrainMechanism):
    """
    Carotid body chemoreceptor analog. Estimates PO2/PCO2/pH proxies from
    metabolic demand, breath pattern, and stress, then computes integrated
    afferent firing rate and tracks chronic sensitization.
    """

    HYPOXIA_RESPONSE_THRESHOLD = 0.55
    SENSITIZATION_WINDOW = 60
    SENSITIZATION_RATE = 0.005
    SENSITIZATION_DECAY = 0.001

    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="CarotidBodyChemosensor",
            human_analog="Carotid body type I glomus cell chemoreceptor",
            layer="foundational",
        )
        self.state.setdefault("po2_proxy", 0.0)
        self.state.setdefault("pco2_proxy", 0.0)
        self.state.setdefault("ph_proxy", 0.5)
        self.state.setdefault("chemoreceptor_drive", 0.0)
        self.state.setdefault("atp_release", 0.0)
        self.state.setdefault("hypoxia_response_active", False)
        self.state.setdefault("chronic_intermittent_sensitization", 0.0)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _estimate_po2_inverse(self, vital_drive: float, breath_rate: float, breath_amp: float) -> float:
        """Higher vital_drive + low breath capacity = hypoxia proxy.
        Returns inverse PO2 — 1.0 means severe hypoxia, 0.0 means well-oxygenated.
        """
        # Demand exceeds supply when drive is high but breath is shallow/slow
        # When breath_amp is high & rate moderate, oxygen demand is met → low hypoxia
        supply = (breath_rate * 1.5) * breath_amp
        demand = vital_drive
        gap = max(0.0, demand - supply * 0.6)
        return min(1.0, gap)

    def _estimate_pco2(self, breath_rate: float, breath_amp: float, vital: float) -> float:
        """Hypercapnia proxy: low ventilation + high metabolic activity → CO2 rises."""
        ventilation = breath_rate * breath_amp
        if ventilation < 0.10 and vital > 0.5:
            return min(1.0, 0.5 + (0.10 - ventilation) * 5.0)
        return max(0.0, vital - ventilation * 2.0)

    def _estimate_ph(self, pco2: float, stress_active: bool) -> float:
        """pH proxy. Centered on 0.5 = normal pH 7.40.
        Acidosis (low pH) follows hypercapnia and high stress (lactic acidosis proxy).
        """
        ph = 0.5 - pco2 * 0.3
        if stress_active:
            ph -= 0.05
        return max(0.0, min(1.0, ph))

    def _glomus_depolarization(self, po2_inv: float, pco2: float, ph: float) -> float:
        """Glomus cell depolarization proxy (López-Barneo 1996; Nurse 2010).
        Increases with hypoxia, hypercapnia, acidosis. K+ channel inhibition analog.
        """
        depol = po2_inv * 0.45 + pco2 * 0.35 + (0.5 - ph) * 2.0 * 0.20
        return max(0.0, min(1.0, depol))

    def _hypoxic_ventilatory_response(self, drive: float, sensitization: float) -> float:
        """HVR gain — Iturriaga & Alcayaga 2004. CIH amplifies HVR slope."""
        baseline_gain = max(0.0, drive - 0.30)
        return baseline_gain * (1.0 + sensitization * 0.5)

    def _peripheral_catecholamine_release(self, depolarization: float, drive: float) -> float:
        """Glomus cell catecholamine co-transmitter release (López-Barneo 1996).
        Modulator alongside ATP — affects afferent firing pattern.
        """
        return min(1.0, depolarization * 0.6 + drive * 0.20)

    def _nts_afferent_firing_proxy(self, atp: float, catecholamines: float) -> float:
        """NTS afferent terminal firing rate proxy (Zera 2019 Physiology).
        ATP via P2X2/3 dominant excitation; catecholamines modulate.
        """
        return min(1.0, atp * 0.75 + catecholamines * 0.25)

    def _detect_periodic_pattern(self, recent: list) -> bool:
        """Detect intermittent (vs sustained) hypoxia exposure pattern.
        Variance-based: high variance with high mean = intermittent.
        """
        if len(recent) < 20:
            return False
        sample = recent[-30:]
        mean = sum(sample) / len(sample)
        if mean < 0.30:
            return False
        var = sum((x - mean) ** 2 for x in sample) / len(sample)
        return var > 0.05

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        rp = prior.get("RespiratoryPacemaker", {})
        breath_rate = float(rp.get("breath_rate_hz", 0.25))
        breath_amp = float(rp.get("inspiratory_drive_amplitude", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        # --- PO2/PCO2/pH proxies ---
        po2_inv = self._estimate_po2_inverse(vital_drive, breath_rate, breath_amp)
        pco2 = self._estimate_pco2(breath_rate, breath_amp, vital_drive)
        ph = self._estimate_ph(pco2, stress_active)

        # --- Glomus cell depolarization proxy ---
        depolarization = self._glomus_depolarization(po2_inv, pco2, ph)

        # Add survival_threat as additional drive (sympathetic activation can sensitize CB)
        depolarization = min(1.0, depolarization + survival_threat * 0.10)

        # --- Apply chronic sensitization (CIH) ---
        sensitization = float(self.state.get("chronic_intermittent_sensitization", 0.0))
        depolarization = min(1.0, depolarization * (1.0 + sensitization * 0.4))

        # --- ATP release (Nurse 2010 — primary excitatory transmitter) ---
        atp_target = depolarization
        prev_atp = float(self.state.get("atp_release", 0.0))
        new_atp = self._smooth(prev_atp, atp_target)

        # --- Chemoreceptor afferent drive (P2X2/3 EPSP proxy) ---
        # Afferent firing tracks ATP release with slight smoothing
        chemoreceptor_target = new_atp
        prev_drive = float(self.state.get("chemoreceptor_drive", 0.0))
        new_drive = self._smooth(prev_drive, chemoreceptor_target)

        # --- Hypoxia response flag ---
        hypoxia_response = new_drive > self.HYPOXIA_RESPONSE_THRESHOLD

        # --- Update sensitization (chronic intermittent hypoxia) ---
        # Build sensitization when hypoxia response is repeatedly engaged
        if hypoxia_response:
            sensitization = min(1.0, sensitization + self.SENSITIZATION_RATE)
        else:
            sensitization = max(0.0, sensitization - self.SENSITIZATION_DECAY)

        # --- Compute HVR gain ---
        hvr_gain = self._hypoxic_ventilatory_response(new_drive, sensitization)

        # --- Peripheral catecholamines (co-transmitter, modulator) ---
        catecholamines = self._peripheral_catecholamine_release(depolarization, new_drive)

        # --- NTS afferent firing rate proxy ---
        nts_firing = self._nts_afferent_firing_proxy(new_atp, catecholamines)

        # --- Track recent drive ---
        recent = list(self.state.get("recent_drives", []))
        recent.append(round(new_drive, 4))
        if len(recent) > self.SENSITIZATION_WINDOW:
            recent = recent[-self.SENSITIZATION_WINDOW:]

        # --- Periodic (intermittent) pattern detection ---
        intermittent_pattern = self._detect_periodic_pattern(recent)

        # --- Smooth proxies for output ---
        prev_po2 = float(self.state.get("po2_proxy", 0.0))
        prev_pco2 = float(self.state.get("pco2_proxy", 0.0))
        prev_ph = float(self.state.get("ph_proxy", 0.5))
        new_po2 = self._smooth(prev_po2, po2_inv)
        new_pco2 = self._smooth(prev_pco2, pco2)
        new_ph = self._smooth(prev_ph, ph)

        # --- Persist ---
        self.state["po2_proxy"] = round(new_po2, 4)
        self.state["pco2_proxy"] = round(new_pco2, 4)
        self.state["ph_proxy"] = round(new_ph, 4)
        self.state["chemoreceptor_drive"] = round(new_drive, 4)
        self.state["atp_release"] = round(new_atp, 4)
        self.state["hypoxia_response_active"] = hypoxia_response
        self.state["chronic_intermittent_sensitization"] = round(sensitization, 4)
        self.state["recent_drives"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["hvr_gain"] = round(hvr_gain, 4)
        self.state["catecholamines"] = round(catecholamines, 4)
        self.state["nts_afferent_firing"] = round(nts_firing, 4)
        self.state["intermittent_pattern"] = intermittent_pattern

        return {
            "po2_proxy": round(new_po2, 4),
            "pco2_proxy": round(new_pco2, 4),
            "ph_proxy": round(new_ph, 4),
            "chemoreceptor_drive": round(new_drive, 4),
            "atp_release": round(new_atp, 4),
            "hypoxia_response_active": hypoxia_response,
            "chronic_intermittent_sensitization": round(sensitization, 4),
            "hvr_gain": round(hvr_gain, 4),
            "catecholamines": round(catecholamines, 4),
            "nts_afferent_firing": round(nts_firing, 4),
            "intermittent_pattern": intermittent_pattern,
        }

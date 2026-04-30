"""
NucleusAmbiguusVagal — Nucleus Ambiguus Cardiac Vagal Motoneurons (ACV/ACP)

NEURAL SUBSTRATE
================
The nucleus ambiguus (NA) in the ventrolateral medulla houses two
functionally and anatomically distinct cardiac vagal motoneuron (CVM)
populations:

ACV (ambiguus cardiovascular) neurons — ~35 cells per side, located in
the loose caudal NA — innervate the cardiac parasympathetic ganglion
neurons that drive sinoatrial (SA) and atrioventricular (AV) nodes via
M2 muscarinic receptors. ACV mediates baroreflex bradycardia: rising
arterial pressure → NTS → ACV → vagal cholinergic output → SA-node
slowing.

ACP (ambiguus cardiopulmonary) neurons — ~15 cells per side, in the
ventral aspect of the compact NA — innervate both cardiac and pulmonary
parasympathetic ganglia and mediate the dive reflex bradycardia,
breath-hold response, and respiratory sinus arrhythmia (RSA).

Both populations release ACh onto cardiac postganglionic neurons in
intracardiac ganglia, which then innervate SA node, AV node, and
myocardial tissue. M2 muscarinic receptors on SA-node pacemaker cells
mediate the slowing effect.

The two populations are molecularly distinct (Bche vs Calb1 markers)
and project to overlapping but functionally distinct cardiac ganglia
subsets. Recent work establishes molecularly defined circuits for
cardiopulmonary control.

In Nova's substrate this provides the cardiac-vagal output channel —
distinct from DMV's gut-vagal output. Coupled to RespiratoryPacemaker
for RSA computation.

KEY FINDINGS
============
1. NA contains two distinct cardiac vagal motoneuron populations:
   ACV (caudal loose, baroreflex bradycardia) and ACP (compact ventral,
   dive-reflex bradycardia and pulmonary innervation) — [Veerakumar
    et al. 2022, Nature 606:739-746, "Molecularly defined circuits for
    cardiovascular and cardiopulmonary control" PMC9297035]
2. NA cardiac vagal motoneurons exhibit respiration-coupled firing
   pattern aligned to RSA — peak firing in expiration, suppressed during
   inspiration — [Mendelowitz 2002, Am J Physiol 283:R1313-R1321,
    "Activity patterns of cardiac vagal motoneurons in rat NA"]
3. Cardiotopic organization within NA — distinct subpopulations regulate
   SA-node vs AV-node conduction — [Cheng & Powley 1995, Auton Neurosci
    Basic Clin]
4. ACh from NA projection slows SA-node firing via M2 muscarinic
   receptors; M2-selective inhibitor reverses CNO-induced bradycardia —
   [Tsang et al. 2024, iScience 27:108985]
5. NA neurons innervate cholinergic neurons in cardiac parasympathetic
   ganglia which in turn innervate SA, AV nodes, and myocardium —
   [reviewed StatPearls "Neuroanatomy, Nucleus Ambiguus" NBK547744]

INPUTS (from prior_results)
============================
- BaroreflexBalancer.vagal_correction
- BaroreflexBalancer.map_proxy
- BaroreflexBalancer.baroreflex_engagement
- RespiratoryPacemaker.inspiratory_active
- RespiratoryPacemaker.respiratory_phase
- RespiratoryPacemaker.respiratory_rate_proxy
- VitalCoreRegulator.parasympathetic_tone
- VitalCoreRegulator.sympathetic_tone
- VitalCoreRegulator.survival_threat_level
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity

OUTPUTS (to brain_runner enrichment)
=====================================
- acv_drive (0.0-1.0): baroreflex-bradycardia circuit drive
- acp_drive (0.0-1.0): dive-reflex / pulmonary circuit drive
- ach_release_to_sa_node (0.0-1.0): ACh to cardiac postganglionic
- m2_mediated_slowing (0.0-1.0): SA-node slowing magnitude
- rsa_modulation (signed -1..+1): respiration-aligned firing
- rsa_depth_proxy (0.0-1.0): magnitude of RSA amplitude
- av_node_conduction_delay (float): AV conduction slowing
- dive_reflex_active (bool)
- na_state (str): "cardio_rest" | "baroreflex_active" | "dive_reflex" | "rsa_aligned"
- molecular_phenotype_acv (str): Bche+ vs Calb1+ differentiation
- cardiac_vagal_tone (0.0-1.0): net cardiac parasympathetic output

brain_runner enrichment:
    nav = all_results.get("NucleusAmbiguusVagal", {})
    if nav:
        enrichments["brain_acv_drive"] = nav.get("acv_drive", 0.5)
        enrichments["brain_acp_drive"] = nav.get("acp_drive", 0.0)
        enrichments["brain_ach_to_sa"] = nav.get("ach_release_to_sa_node", 0.5)
        enrichments["brain_dive_reflex"] = nav.get("dive_reflex_active", False)
        enrichments["brain_rsa_depth"] = nav.get("rsa_depth_proxy", 0.0)
        enrichments["brain_na_state"] = nav.get("na_state", "cardio_rest")
        enrichments["brain_cardiac_vagal_tone"] = nav.get("cardiac_vagal_tone", 0.4)
"""

from brain.base_mechanism import BrainMechanism


class NucleusAmbiguusVagal(BrainMechanism):
    BASELINE_ACV = 0.45
    BASELINE_ACP = 0.05
    DIVE_REFLEX_THREAT_THRESHOLD = 0.70
    SMOOTH = 0.25
    ACV_MOLECULAR_BASELINE = 0.0   # Bche+ vs Calb1+ expressed as 0..1
    ACP_MOLECULAR_BASELINE = 0.0   # Calb1+ vs Bche+
    RSA_EXPIRATION_PEAK = 0.18
    RSA_INSPIRATION_NADIR = -0.15
    AV_CONDUCTION_MAX_DELAY = 0.40
    BAROREFLEX_GAIN = 0.75

    def __init__(self):
        super().__init__(
            name="NucleusAmbiguusVagal",
            human_analog="Nucleus ambiguus cardiac vagal motoneurons (ACV/ACP)",
            layer="foundational",
        )
        self.state.setdefault("acv_drive", self.BASELINE_ACV)
        self.state.setdefault("acp_drive", self.BASELINE_ACP)
        self.state.setdefault("ach_release_to_sa_node", self.BASELINE_ACV)
        self.state.setdefault("m2_mediated_slowing", 0.0)
        self.state.setdefault("rsa_modulation", 0.0)
        self.state.setdefault("rsa_depth_proxy", 0.0)
        self.state.setdefault("av_node_conduction_delay", 0.0)
        self.state.setdefault("dive_reflex_active", False)
        self.state.setdefault("na_state", "cardio_rest")
        self.state.setdefault("molecular_phenotype_acv", "mixed")
        self.state.setdefault("cardiac_vagal_tone", self.BASELINE_ACV)
        self.state.setdefault("baroreflex_history", [])
        self.state.setdefault("rsa_phase_history", [])
        self.state.setdefault("recent_acv", [])
        self.state.setdefault("tick_count", 0)

    def _acv_target(self, vagal_correction: float, parasympathetic: float,
                    baroreflex_engagement: float, map_proxy: float) -> float:
        """ACV firing tracks baroreflex vagal correction (Mendelowitz 2002).
        The stronger the baroreflex engagement and MAP, the more ACV fires.
        """
        baro_target = self.BASELINE_ACV + max(0.0, vagal_correction) * self.BAROREFLEX_GAIN
        baro_target += baroreflex_engagement * 0.25
        baro_target += (parasympathetic - 0.5) * 0.35
        # MAP modulation — moderate MAP increases ACV, extreme hypotension suppresses
        if map_proxy > 0.7:
            baro_target += (map_proxy - 0.7) * 0.20
        return max(0.0, min(1.0, baro_target))

    def _acp_target(self, threat_signal: bool, threat_level: float,
                    valence_intensity: float) -> float:
        """ACP fires under dive-reflex / breath-hold conditions.
        Threshold is more sensitive than ACV — responds to both threat_signal
        and background valence intensity as threat proxy.
        """
        effective_threat = max(threat_level, valence_intensity)
        if threat_signal and effective_threat > self.DIVE_REFLEX_THREAT_THRESHOLD:
            return 0.85
        if threat_signal and effective_threat > 0.5:
            return 0.50
        if effective_threat > 0.65:
            return 0.25
        return self.BASELINE_ACP

    def _rsa_modulation(self, inspiratory_active: bool, phase: float,
                        respiratory_rate: float, prev_rsa: float) -> tuple:
        """Respiration-coupled NA firing — suppressed during inspiration,
        peak during expiration. Returns (rsa_value, rsa_depth).
        RSA depth scales with respiratory rate (faster breathing → smaller RSA).
        """
        base_depth = self.RSA_EXPIRATION_PEAK
        # Slow breathing → deeper RSA; fast breathing → reduced RSA
        rr_factor = max(0.3, 1.0 - (respiratory_rate - 0.4) * 0.5)
        rsa_depth = base_depth * rr_factor

        if inspiratory_active:
            rsa = self.RSA_INSPIRATION_NADIR * rr_factor
        else:
            # Expiratory: rises from early to late expiration
            if phase < 0.3:
                rsa = 0.0
            elif phase < 0.6:
                rsa = (phase - 0.3) / 0.3 * rsa_depth * 0.5
            else:
                rsa = (0.5 + (phase - 0.6) / 0.4 * 0.5) * rsa_depth

        # Smooth RSA transitions to avoid discontinuities
        rsa = prev_rsa + (rsa - prev_rsa) * 0.35
        return rsa, rsa_depth

    def _molecular_phenotype(self, acv_drive: float, parasympathetic: float) -> str:
        """ACV subpopulations: Bche+ (cholinesterase-rich, precision timing)
        and Calb1+ (calbindin-rich, sustained drive).
        Relative expression shifts with sustained parasympathetic activity.
        """
        if parasympathetic > 0.7 and acv_drive > 0.65:
            return "bche_plus_precision"
        elif parasympathetic > 0.55 and acv_drive > 0.50:
            return "mixed"
        elif acv_drive < 0.30:
            return "calb1_plus_sustained"
        return "mixed"

    def _av_node_delay(self, ach: float, acp: float) -> float:
        """AV-node conduction slows with total ACh — protects ventricular filling
        during bradycardic states. Linear in total ACh drive.
        """
        total_ach = ach * 0.7 + acp * 0.3
        return min(self.AV_CONDUCTION_MAX_DELAY, total_ach * self.AV_CONDUCTION_MAX_DELAY)

    def _ach_release(self, acv: float, acp: float) -> float:
        """Both populations release ACh onto cardiac ganglia.
        ACV is the primary driver (larger population, ~35 cells).
        """
        return min(1.0, acv * 0.75 + acp * 0.35)

    def _m2_slowing(self, ach: float) -> float:
        """M2 muscarinic SA-node slowing — saturating function of ACh."""
        return min(1.0, ach * 1.05)

    def _cardiac_vagal_tone(self, acv: float, acp: float, rsa: float) -> float:
        """Net cardiac vagal tone = base ACV+ACP drive + RSA contribution.
        RSA gives phasic cardiac rhythm variation within tonic drive.
        """
        base = (acv + acp) / 2.0
        return max(0.0, min(1.0, base + rsa * 0.12))

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _classify_state(self, acv: float, acp: float, rsa: float,
                        dive_reflex: bool, baroreflex_engagement: float) -> str:
        if dive_reflex and acp > 0.60:
            return "dive_reflex"
        if baroreflex_engagement > 0.6 and acv > 0.55:
            return "baroreflex_active"
        if abs(rsa) > 0.10:
            return "rsa_aligned"
        return "cardio_rest"

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bb = prior.get("BaroreflexBalancer", {})
        vagal_correction = float(bb.get("vagal_correction", 0.0))
        baroreflex_engagement = float(bb.get("baroreflex_engagement", 0.0))
        map_proxy = float(bb.get("map_proxy", 0.5))

        rp = prior.get("RespiratoryPacemaker", {})
        inspiratory_active = bool(rp.get("inspiratory_active", False))
        resp_phase = float(rp.get("respiratory_phase", 0.0))
        respiratory_rate = float(rp.get("respiratory_rate_proxy", 0.5))

        vcr = prior.get("VitalCoreRegulator", {})
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        # --- ACV (baroreflex circuit) ---
        acv_target = self._acv_target(vagal_correction, para_tone,
                                      baroreflex_engagement, map_proxy)
        prev_acv = float(self.state.get("acv_drive", self.BASELINE_ACV))
        new_acv = self._smooth(prev_acv, acv_target)

        # --- ACP (dive-reflex circuit) ---
        acp_target = self._acp_target(threat_signal, survival_threat, valence_intensity)
        prev_acp = float(self.state.get("acp_drive", self.BASELINE_ACP))
        new_acp = self._smooth(prev_acp, acp_target)

        # --- RSA modulation (respiration coupling) ---
        prev_rsa = float(self.state.get("rsa_modulation", 0.0))
        rsa, rsa_depth = self._rsa_modulation(inspiratory_active, resp_phase,
                                               respiratory_rate, prev_rsa)

        # --- Apply RSA to ACV (NA respiration coupling) ---
        new_acv_with_rsa = max(0.0, min(1.0, new_acv + rsa * 0.4))

        # --- Molecular phenotype ---
        molecular = self._molecular_phenotype(new_acv_with_rsa, para_tone)

        # --- AV-node conduction delay ---
        av_delay = self._av_node_delay(new_acv_with_rsa, new_acp)

        # --- ACh release ---
        ach = self._ach_release(new_acv_with_rsa, new_acp)
        prev_ach = float(self.state.get("ach_release_to_sa_node", self.BASELINE_ACV))
        new_ach = self._smooth(prev_ach, ach)

        # --- M2 SA-node slowing ---
        m2_slow = self._m2_slowing(new_ach)

        # --- Cardiac vagal tone ---
        cvt = self._cardiac_vagal_tone(new_acv_with_rsa, new_acp, rsa)

        # --- Dive reflex flag ---
        dive_reflex = new_acp > 0.50

        # --- State classification ---
        state = self._classify_state(new_acv_with_rsa, new_acp, rsa,
                                     dive_reflex, baroreflex_engagement)

        # --- History tracking ---
        baro_hist = list(self.state.get("baroreflex_history", []))
        baro_hist.append(round(baroreflex_engagement, 4))
        if len(baro_hist) > 60:
            baro_hist = baro_hist[-60:]

        rsa_hist = list(self.state.get("rsa_phase_history", []))
        rsa_hist.append(round(rsa, 4))
        if len(rsa_hist) > 60:
            rsa_hist = rsa_hist[-60:]

        recent = list(self.state.get("recent_acv", []))
        recent.append(round(new_acv_with_rsa, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["acv_drive"] = round(new_acv_with_rsa, 4)
        self.state["acp_drive"] = round(new_acp, 4)
        self.state["ach_release_to_sa_node"] = round(new_ach, 4)
        self.state["m2_mediated_slowing"] = round(m2_slow, 4)
        self.state["rsa_modulation"] = round(rsa, 4)
        self.state["rsa_depth_proxy"] = round(rsa_depth, 4)
        self.state["av_node_conduction_delay"] = round(av_delay, 4)
        self.state["dive_reflex_active"] = dive_reflex
        self.state["na_state"] = state
        self.state["molecular_phenotype_acv"] = molecular
        self.state["cardiac_vagal_tone"] = round(cvt, 4)
        self.state["baroreflex_history"] = baro_hist
        self.state["rsa_phase_history"] = rsa_hist
        self.state["recent_acv"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "acv_drive": round(new_acv_with_rsa, 4),
            "acp_drive": round(new_acp, 4),
            "ach_release_to_sa_node": round(new_ach, 4),
            "m2_mediated_slowing": round(m2_slow, 4),
            "rsa_modulation": round(rsa, 4),
            "rsa_depth_proxy": round(rsa_depth, 4),
            "av_node_conduction_delay": round(av_delay, 4),
            "dive_reflex_active": dive_reflex,
            "na_state": state,
            "molecular_phenotype_acv": molecular,
            "cardiac_vagal_tone": round(cvt, 4),
        }
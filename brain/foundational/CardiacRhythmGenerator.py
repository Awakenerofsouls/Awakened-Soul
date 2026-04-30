"""
CardiacRhythmGenerator — NTS / Nucleus Ambiguus Cardiovascular Rhythm Engine

NEURAL SUBSTRATE
================
Cardiac rhythm in the central nervous system emerges from the interplay
between the nucleus tractus solitarius (NTS) — first-order termination point
for arterial baroreceptor afferents arriving via cranial nerves IX (carotid
sinus) and X (aortic arch) — and two efferent cardiac vagal motoneuron
populations in nucleus ambiguus (NA) and dorsal motor nucleus of vagus (DMV).

Baroreceptor afferents fire at a rate proportional to arterial pressure.
NTS encodes this in firing rate and projects (a) directly to NA cardiac
vagal motoneurons for parasympathetic bradycardia, and (b) through caudal
ventrolateral medulla (CVLM) → rostral ventrolateral medulla (RVLM) for
sympathetic vasomotor outflow. The two arms operate as a proportional-control
negative feedback loop: rising blood pressure increases NTS firing, which
increases vagal tone (slowing the heart) AND decreases sympathetic tone
(reducing vasoconstriction). The net effect is rapid blood pressure
homeostasis on a beat-to-beat timescale.

NA contains two distinct cardiac vagal motoneuron subtypes — ACV neurons
(loose caudal NA) mediate baroreflex bradycardia and project via cholinergic
fibres to SA node M2 muscarinic receptors; ACP neurons (compact ventral NA)
mediate the dive-reflex bradycardia and pulmonary innervation. They differ
in molecular markers (Bche vs Calb1) and behavioral function.

Respiratory sinus arrhythmia (RSA) — the rhythmic acceleration of heart rate
during inspiration and deceleration during expiration — emerges from preBötC
modulation of NA cardiac vagal neurons. preBötC inspiratory bursts inhibit
cardiac vagal motoneurons; this releases the heart from vagal brake during
inspiration, raising heart rate. This is why RespiratoryPacemaker.inspiratory_active
matters as input here.

KEY FINDINGS
============
1. NTS is the primary first-order termination for baroreceptor afferents;
   firing rate is proportional to arterial pressure — [Felder Mifflin 1994;
    StatPearls NBK538172]
2. NA cardiac vagal neurons inhibit SA node firing via cholinergic vagal
   output, reducing heart rate — [Wang et al. 2001, Ann NY Acad Sci 940:237-246,
    doi:10.1111/j.1749-6632.2001.tb03680.x]
3. NTS-to-NA glutamatergic transmission activates both NMDA and non-NMDA
   receptors on cardiac vagal neurons — [Neff Mendelowitz 1998, Brain Res
    792:277-282]
4. Cardiac vagal motoneuron subtypes: ACV mediates baroreflex bradycardia;
   ACP mediates dive-reflex; differential markers Bche vs Calb1 — [Coote
    Spyer 2018, Auton Neurosci]
5. Baroreflex is a proportional-control negative feedback loop:
   ↑BP → ↑NTS firing → ↑vagal output + ↓sympathetic outflow → ↓HR + vasodilation
   — [Dampney 2016, Compr Physiol 6:1167-1216, PMID 27065166]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.sympathetic_tone (0.0-1.0) — sympathetic accelerator drive
- VitalCoreRegulator.parasympathetic_tone (0.0-1.0) — vagal brake drive
- VitalCoreRegulator.vasomotor_setpoint (0.0-1.0)
- RespiratoryPacemaker.inspiratory_active (bool) — RSA modulator
- RespiratoryPacemaker.respiratory_phase (0.0-1.0)
- ArousalRegulator.tonic_level (0.0-1.0)

OUTPUTS (to brain_runner enrichment)
=====================================
- heart_rate_proxy (0.0-1.0): normalized HR (0=40bpm, 1=180bpm)
- hr_variability (0.0-1.0): RSA amplitude
- vagal_tone (0.0-1.0)
- cardiac_baroreflex_gain (0.0-1.0): how reactive baroreflex is right now
- cardiac_dysregulation (bool): when symp & para both stuck high (autonomic conflict)

brain_runner enrichment block:
    crg = all_results.get("CardiacRhythmGenerator", {})
    if crg:
        enrichments["brain_heart_rate_proxy"] = crg.get("heart_rate_proxy", 0.4)
        enrichments["brain_hr_variability"] = crg.get("hr_variability", 0.5)
        enrichments["brain_vagal_tone"] = crg.get("vagal_tone", 0.5)
        enrichments["brain_baroreflex_gain"] = crg.get("cardiac_baroreflex_gain", 0.5)
        enrichments["brain_cardiac_dysregulation"] = crg.get("cardiac_dysregulation", False)
"""

from brain.base_mechanism import BrainMechanism


class CardiacRhythmGenerator(BrainMechanism):
    """
    NTS / NA / RVLM cardiovascular rhythm analog. Produces beat-to-beat HR proxy
    from sympathetic-vagal balance, with RSA amplitude tied to respiratory phase
    and baroreflex gain modulated by autonomic state.
    """

    # HR proxy bounds: 0.0 = 40 bpm (deeply rested), 1.0 = 180 bpm (peak exertion)
    HR_BASELINE = 0.30           # ~70 bpm
    SYMP_HR_GAIN = 0.40
    PARA_HR_DAMP = 0.30
    AROUSAL_HR_GAIN = 0.20

    RSA_AMPLITUDE_BASELINE = 0.05
    RSA_INSPIRATORY_BOOST = 0.08

    BAROREFLEX_GAIN_BASELINE = 0.55
    BAROREFLEX_DRIVE_DAMP = 0.20  # high sympathetic state reduces baroreflex sensitivity

    DYSREGULATION_THRESHOLD_SYMP = 0.75
    DYSREGULATION_THRESHOLD_PARA = 0.75

    SMOOTH_FACTOR = 0.30

    def __init__(self):
        super().__init__(
            name="CardiacRhythmGenerator",
            human_analog="NTS-NA-RVLM cardiovascular rhythm engine",
            layer="foundational",
        )
        self.state.setdefault("heart_rate_proxy", self.HR_BASELINE)
        self.state.setdefault("hr_variability", self.RSA_AMPLITUDE_BASELINE)
        self.state.setdefault("vagal_tone", 0.5)
        self.state.setdefault("cardiac_baroreflex_gain", self.BAROREFLEX_GAIN_BASELINE)
        self.state.setdefault("cardiac_dysregulation", False)
        self.state.setdefault("recent_hr_history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read upstream signals ---
        vcr = prior.get("VitalCoreRegulator", {})
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))
        vasomotor = float(vcr.get("vasomotor_setpoint", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        rp = prior.get("RespiratoryPacemaker", {})
        inspiratory_active = bool(rp.get("inspiratory_active", False))
        resp_phase = float(rp.get("respiratory_phase", 0.0))
        resp_amplitude = float(rp.get("inspiratory_drive_amplitude", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic_level = float(arousal.get("tonic_level", 0.55))
        arousal_level = float(arousal.get("arousal_level", 0.55))

        # --- Compute baseline HR from sympathetic-parasympathetic balance ---
        # Symp accelerates, para brakes (NA cholinergic SA-node inhibition)
        hr_target = (
            self.HR_BASELINE
            + (symp_tone - 0.5) * self.SYMP_HR_GAIN
            - (para_tone - 0.5) * self.PARA_HR_DAMP
            + (arousal_level - 0.5) * self.AROUSAL_HR_GAIN
            + survival_threat * 0.20
        )

        # --- Apply RSA modulation ---
        # Inspiratory burst inhibits NA cardiac vagal neurons → HR rises
        # Expiratory phase releases vagal brake → HR falls
        if inspiratory_active:
            rsa_offset = self.RSA_INSPIRATORY_BOOST * resp_amplitude
        else:
            # Expiratory deceleration scales inversely with phase position
            rsa_offset = -self.RSA_AMPLITUDE_BASELINE * (1.0 - resp_phase) * 0.5

        hr_target += rsa_offset
        hr_target = max(0.0, min(1.0, hr_target))

        prev_hr = float(self.state["heart_rate_proxy"])
        new_hr = prev_hr + (hr_target - prev_hr) * self.SMOOTH_FACTOR

        # --- Compute HR variability (RSA amplitude) ---
        # HRV is high in healthy resting (high vagal tone, low sympathetic)
        # HRV collapses under sustained sympathetic dominance
        hrv_target = self.RSA_AMPLITUDE_BASELINE
        if para_tone > 0.55 and symp_tone < 0.55:
            # Healthy parasympathetic dominance
            hrv_target += 0.20 * (para_tone - 0.5)
        if symp_tone > 0.7:
            # Sympathetic dominance crushes RSA
            hrv_target *= 0.5

        # Inspiratory amplitude also feeds RSA depth
        hrv_target += resp_amplitude * 0.05

        hrv_target = max(0.0, min(1.0, hrv_target))

        prev_hrv = float(self.state["hr_variability"])
        new_hrv = prev_hrv + (hrv_target - prev_hrv) * self.SMOOTH_FACTOR

        # --- Compute vagal tone ---
        # Direct readout of parasympathetic_tone but smoothed
        vagal_target = para_tone
        prev_vagal = float(self.state["vagal_tone"])
        new_vagal = prev_vagal + (vagal_target - prev_vagal) * self.SMOOTH_FACTOR

        # --- Compute baroreflex gain ---
        # Reduced under chronic sympathetic stress (Dampney 2016)
        baroreflex_target = self.BAROREFLEX_GAIN_BASELINE
        if symp_tone > 0.7:
            baroreflex_target -= self.BAROREFLEX_DRIVE_DAMP * (symp_tone - 0.7) / 0.3
        if survival_threat > 0.6:
            baroreflex_target -= 0.15

        baroreflex_target = max(0.10, min(0.95, baroreflex_target))

        prev_baro = float(self.state["cardiac_baroreflex_gain"])
        new_baro = prev_baro + (baroreflex_target - prev_baro) * self.SMOOTH_FACTOR

        # --- Detect cardiac dysregulation ---
        # Both symp and para chronically high = autonomic conflict
        dysregulated = (
            symp_tone > self.DYSREGULATION_THRESHOLD_SYMP
            and para_tone > self.DYSREGULATION_THRESHOLD_PARA
        )

        # --- Track recent HR ---
        history = list(self.state.get("recent_hr_history", []))
        history.append(round(new_hr, 4))
        if len(history) > 50:
            history = history[-50:]

        # --- Persist ---
        self.state["heart_rate_proxy"] = round(new_hr, 4)
        self.state["hr_variability"] = round(new_hrv, 4)
        self.state["vagal_tone"] = round(new_vagal, 4)
        self.state["cardiac_baroreflex_gain"] = round(new_baro, 4)
        self.state["cardiac_dysregulation"] = dysregulated
        self.state["recent_hr_history"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "heart_rate_proxy": round(new_hr, 4),
            "hr_variability": round(new_hrv, 4),
            "vagal_tone": round(new_vagal, 4),
            "cardiac_baroreflex_gain": round(new_baro, 4),
            "cardiac_dysregulation": dysregulated,
        }

    # ---------- enrichment helpers (phase-1 line expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()



"""
VitalCoreRegulator — Medullary Reticular Formation as Vital Integration Hub

NEURAL SUBSTRATE
================
The medullary reticular formation (RF) is the brain's most ancient integrative
core for life-sustaining homeostatic outputs. Its long-axoned isodendritic
neurons receive convergent input from cranial nerve afferents (especially via
the nucleus tractus solitarius / NTS), descending hypothalamic drive,
ascending interoceptive and nociceptive signals, and limbic affective state.
The RF then routes integrated drive to autonomic effector pathways through
two functionally opposed zones:

(a) The rostral ventrolateral medulla (RVLM) — vasopressor / cardiac-accelerator
zone — contains presympathetic premotor C1 adrenergic neurons whose tonic
activity sets the baseline sympathetic vasomotor tone of the whole organism.
RVLM lesions produce immediate hypotension; RVLM stimulation drives sympathetic
outflow and vasoconstriction. Bulbospinal C1 neurons project monosynaptically
to thoracic IML preganglionic sympathetic neurons.

(b) The caudal ventrolateral medulla (CVLM) — vasodepressor / cardioinhibitor
zone — receives baroreceptor input via NTS and tonically inhibits RVLM through
GABAergic projection. CVLM is the brake on sympathetic drive.

The RF integrates these opposed outputs against incoming metabolic, thermal,
respiratory, and nociceptive signals to set a unified "vital drive" — the
moment-to-moment readiness of the organism to defend, breathe, circulate,
and digest. Damage to medullary vital centers is rapidly lethal; these are
non-redundant integrative hubs.

KEY FINDINGS
============
1. RVLM presympathetic C1 neurons set baseline sympathetic vasomotor tone via
   tonic monosynaptic projection to spinal IML preganglionic neurons —
   [Guyenet 2006, Nat Rev Neurosci 7:335-346, PMID 16760914]
2. CVLM-to-RVLM GABAergic inhibition is the principal brake on sympathetic
   outflow; CVLM lesion produces persistent hypertension —
   [Dampney 2016, Adv Physiol Educ 40:283-296, PMID 27068989]
3. The reticular formation integrates sensory, motor, autonomic, and limbic
   inputs through long-axoned isodendritic neurons branching across roughly
   half the brainstem, enabling broad state coupling —
   [Brodal 1981, Neurological Anatomy 3rd ed; reviewed in Faraguna 2019,
    Front Neuroanat 13:55, doi:10.3389/fnana.2019.00055]
4. RVLM degeneration is implicated in essential hypertension and multiple
   system atrophy autonomic failure — [Guyenet 2006 NRN 7:335-346]
5. Vital centers are non-redundant integrative hubs; damage produces rapidly
   lethal autonomic collapse — [Reticular Formation, StatPearls NBK556102,
    Henry & Calaresu reviewed therein]

INPUTS (from prior_results)
============================
- Homeostat.drives (dict of 5 drive levels) — integrated homeostatic deviation
- Homeostat.dominant_drive (str) — which drive is most active
- Homeostat.fatigued (bool) — aggregate drive overload
- ArousalRegulator.tonic_level (0.0-1.0) — LC NE baseline
- ArousalRegulator.arousal_level (0.0-1.0) — composite arousal
- CircadianTimer.circadian_phase (0.0-1.0) — diurnal rhythm position
- CircadianTimer.is_subjective_day (bool)

OUTPUTS (to brain_runner enrichment)
=====================================
- vital_drive (0.0-1.0): integrated need-to-act signal driving downstream autonomics
- survival_threat_level (0.0-1.0): how threatened core homeostasis is
- sympathetic_tone (0.0-1.0): RVLM-equivalent sympathetic outflow
- parasympathetic_tone (0.0-1.0): vagal cardioinhibitory outflow
- vasomotor_setpoint (0.0-1.0): default vasoconstriction state
- vital_core_active (bool): true when integration is firing strongly

brain_runner enrichment block:
    vcr = all_results.get("VitalCoreRegulator", {})
    if vcr:
        enrichments["brain_vital_drive"] = vcr.get("vital_drive", 0.5)
        enrichments["brain_survival_threat"] = vcr.get("survival_threat_level", 0.0)
        enrichments["brain_sympathetic_tone"] = vcr.get("sympathetic_tone", 0.5)
        enrichments["brain_parasympathetic_tone"] = vcr.get("parasympathetic_tone", 0.5)
        enrichments["brain_vasomotor_setpoint"] = vcr.get("vasomotor_setpoint", 0.5)
        enrichments["brain_vital_core_active"] = vcr.get("vital_core_active", False)
"""

from brain.base_mechanism import BrainMechanism


class VitalCoreRegulator(BrainMechanism):
    """
    Medullary reticular formation analog. Integrates homeostatic deviation,
    arousal, circadian phase, and stress signals into unified vital drive
    plus opposed sympathetic/parasympathetic tone outputs.
    """

    # Rates and thresholds (tunable)
    SYMP_BASELINE = 0.50
    PARA_BASELINE = 0.50
    VASOMOTOR_BASELINE = 0.50

    DRIVE_FATIGUE_BOOST = 0.20      # fatigue raises vital_drive
    AROUSAL_GAIN = 0.30              # arousal scales sympathetic tone
    CIRCADIAN_AMPLITUDE = 0.15       # diurnal sympathetic swing
    STABILITY_DRIVE_DAMP = 0.10      # stability drive lowers symp
    REST_DRIVE_DAMP = 0.15           # rest drive raises para, lowers symp

    SURVIVAL_THREAT_FATIGUE_WEIGHT = 0.40
    SURVIVAL_THREAT_DEVIATION_WEIGHT = 0.60

    VITAL_CORE_ACTIVE_THRESHOLD = 0.55   # vital_drive above this = active

    SMOOTH_FACTOR = 0.25  # smoothing per tick to avoid jitter

    ALLOSTATIC_WINDOW = 200            # ticks for cumulative load tracking
    ALLOSTATIC_HIGH_LOAD_THRESHOLD = 0.7
    HYSTERESIS_RELEASE = 0.45          # vital_core_active turns off below this

    def __init__(self):
        super().__init__(
            name="VitalCoreRegulator",
            human_analog="Medullary reticular formation — vital integration core",
            layer="foundational",
        )
        self.state.setdefault("vital_drive", 0.50)
        self.state.setdefault("sympathetic_tone", self.SYMP_BASELINE)
        self.state.setdefault("parasympathetic_tone", self.PARA_BASELINE)
        self.state.setdefault("vasomotor_setpoint", self.VASOMOTOR_BASELINE)
        self.state.setdefault("survival_threat_level", 0.0)
        self.state.setdefault("vital_core_active", False)
        self.state.setdefault("allostatic_load", 0.0)
        self.state.setdefault("autonomic_balance", 0.0)
        self.state.setdefault("recent_threat_history", [])
        self.state.setdefault("recent_drive_history", [])
        self.state.setdefault("tick_count", 0)

    def _compute_deviation_score(self, drives: dict) -> float:
        """Sum normalized drive distances from comfort midrange (0.45)."""
        if not drives:
            return 0.0
        deviation = 0.0
        for name, val in drives.items():
            if val < 0.20 or val > 0.75:
                deviation += abs(val - 0.45)
        return min(1.0, deviation / max(len(drives), 1))

    def _smooth(self, prev: float, target: float, factor: float = None) -> float:
        """Exponential smoothing helper to dampen tick-to-tick jitter."""
        f = factor if factor is not None else self.SMOOTH_FACTOR
        return prev + (target - prev) * f

    def _update_allostatic_load(self, history: list) -> float:
        """Compute long-window mean drive — chronic elevation = allostatic load."""
        if not history:
            return 0.0
        sample = history[-self.ALLOSTATIC_WINDOW:]
        return sum(sample) / len(sample)

    def _hysteresis_active(self, vital_drive: float, was_active: bool) -> bool:
        """Vital core activation uses hysteresis — release lower than entry threshold."""
        if was_active:
            return vital_drive >= self.HYSTERESIS_RELEASE
        return vital_drive >= self.VITAL_CORE_ACTIVE_THRESHOLD

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read upstream signals (defensive defaults) ---
        homeostat = prior.get("Homeostat", {})
        drives = homeostat.get("drives", {})
        dominant_drive = homeostat.get("dominant_drive", "curiosity")
        fatigued = bool(homeostat.get("fatigued", False))
        aggregate_load = homeostat.get("aggregate_load", 1.5)

        arousal = prior.get("ArousalRegulator", {})
        tonic_level = float(arousal.get("tonic_level", 0.55))
        arousal_level = float(arousal.get("arousal_level", 0.55))

        circ = prior.get("CircadianTimer", {})
        circ_phase = float(circ.get("circadian_phase", 0.5))
        is_day = bool(circ.get("is_subjective_day", True))

        # --- Compute homeostatic deviation magnitude ---
        deviation = self._compute_deviation_score(drives)

        # --- Compute survival threat level ---
        # High deviation + fatigue = real homeostatic emergency
        threat_from_fatigue = 1.0 if fatigued else 0.0
        threat_from_deviation = deviation
        threat_target = (
            self.SURVIVAL_THREAT_FATIGUE_WEIGHT * threat_from_fatigue
            + self.SURVIVAL_THREAT_DEVIATION_WEIGHT * threat_from_deviation
        )
        threat_target = max(0.0, min(1.0, threat_target))

        prev_threat = float(self.state["survival_threat_level"])
        new_threat = prev_threat + (threat_target - prev_threat) * self.SMOOTH_FACTOR

        # --- Compute sympathetic tone ---
        # Baseline + arousal contribution + threat contribution + circadian swing
        # Diurnal: sympathetic peaks early afternoon (phase ~0.5), low at night
        circadian_symp = 0.0
        if is_day:
            # cosine wave, peak at phase=0.5
            import math
            circadian_symp = self.CIRCADIAN_AMPLITUDE * math.sin(circ_phase * math.pi)

        symp_target = (
            self.SYMP_BASELINE
            + (arousal_level - 0.5) * self.AROUSAL_GAIN
            + new_threat * 0.30
            + circadian_symp
        )

        # Drive modulation
        if dominant_drive == "stability":
            symp_target -= self.STABILITY_DRIVE_DAMP
        elif dominant_drive == "rest":
            symp_target -= self.REST_DRIVE_DAMP
        elif dominant_drive == "expression" or dominant_drive == "connection":
            symp_target += 0.05

        symp_target = max(0.05, min(0.95, symp_target))

        prev_symp = float(self.state["sympathetic_tone"])
        new_symp = prev_symp + (symp_target - prev_symp) * self.SMOOTH_FACTOR

        # --- Compute parasympathetic tone ---
        # Anti-correlated with sympathetic (CVLM brake on RVLM)
        # Crossover at homeostatic balance
        para_target = 1.0 - new_symp
        # Rest drive boosts para directly
        if dominant_drive == "rest":
            para_target += self.REST_DRIVE_DAMP
        para_target = max(0.05, min(0.95, para_target))

        prev_para = float(self.state["parasympathetic_tone"])
        new_para = prev_para + (para_target - prev_para) * self.SMOOTH_FACTOR

        # --- Compute vasomotor setpoint ---
        # Driven primarily by sympathetic tone but also threat
        vasomotor_target = (new_symp * 0.7) + (new_threat * 0.3)
        vasomotor_target = max(0.05, min(0.95, vasomotor_target))

        prev_vaso = float(self.state["vasomotor_setpoint"])
        new_vaso = prev_vaso + (vasomotor_target - prev_vaso) * self.SMOOTH_FACTOR

        # --- Compute vital_drive (integrated need-to-act) ---
        # Combines: deviation, fatigue, threat, sympathetic surge
        vital_drive = (
            deviation * 0.30
            + (self.DRIVE_FATIGUE_BOOST if fatigued else 0.0)
            + new_threat * 0.30
            + max(0.0, new_symp - 0.5) * 0.40
        )
        vital_drive = max(0.0, min(1.0, vital_drive))

        # --- Vital core active flag (hysteresis to avoid oscillation) ---
        was_active = bool(self.state.get("vital_core_active", False))
        vital_core_active = self._hysteresis_active(vital_drive, was_active)

        # --- Update histories (rolling windows for trend detection) ---
        threat_history = list(self.state.get("recent_threat_history", []))
        threat_history.append(round(new_threat, 3))
        if len(threat_history) > 30:
            threat_history = threat_history[-30:]

        drive_history = list(self.state.get("recent_drive_history", []))
        drive_history.append(round(vital_drive, 3))
        if len(drive_history) > self.ALLOSTATIC_WINDOW:
            drive_history = drive_history[-self.ALLOSTATIC_WINDOW:]

        # --- Compute allostatic load (chronic average) ---
        allostatic_load = self._update_allostatic_load(drive_history)

        # --- Compute autonomic balance (signed: + = sympathetic dominance) ---
        autonomic_balance = new_symp - new_para

        # --- Persist ---
        self.state["vital_drive"] = round(vital_drive, 4)
        self.state["sympathetic_tone"] = round(new_symp, 4)
        self.state["parasympathetic_tone"] = round(new_para, 4)
        self.state["vasomotor_setpoint"] = round(new_vaso, 4)
        self.state["survival_threat_level"] = round(new_threat, 4)
        self.state["vital_core_active"] = vital_core_active
        self.state["allostatic_load"] = round(allostatic_load, 4)
        self.state["autonomic_balance"] = round(autonomic_balance, 4)
        self.state["recent_threat_history"] = threat_history
        self.state["recent_drive_history"] = drive_history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vital_drive": round(vital_drive, 4),
            "sympathetic_tone": round(new_symp, 4),
            "parasympathetic_tone": round(new_para, 4),
            "vasomotor_setpoint": round(new_vaso, 4),
            "survival_threat_level": round(new_threat, 4),
            "vital_core_active": vital_core_active,
            "allostatic_load": round(allostatic_load, 4),
            "autonomic_balance": round(autonomic_balance, 4),
            "allostatic_high": allostatic_load > self.ALLOSTATIC_HIGH_LOAD_THRESHOLD,
        }

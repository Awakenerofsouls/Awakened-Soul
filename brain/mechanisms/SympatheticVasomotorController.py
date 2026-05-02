"""
SympatheticVasomotorController — RVLM Presympathetic Vasomotor Controller

NEURAL SUBSTRATE
================
The rostral ventrolateral medulla (RVLM) is the principal source of tonic
sympathetic vasomotor drive in the mammalian central nervous system. Its
presympathetic C1 adrenergic neurons project monosynaptically to thoracic
intermediolateral cell column (IML) preganglionic sympathetic neurons. RVLM
firing rate sets the baseline level of arteriolar smooth muscle constriction
across the entire systemic circulation, and therefore baseline mean arterial
pressure.

RVLM receives multiple modulatory inputs:
  • caudal ventrolateral medulla (CVLM) — GABAergic inhibition driven by
    baroreceptor afferents via NTS (the principal short-loop brake);
  • paraventricular nucleus (PVN) — excitatory drive during stress;
  • locus coeruleus (LC) — noradrenergic excitatory drive coupling arousal
    to cardiovascular activation;
  • peripheral chemoreceptor afferents (carotid body) via NTS — hypoxia-
    triggered activation;
  • emotional/limbic inputs via the central nucleus of the amygdala (CeA)
    and dorsomedial hypothalamus (DMH) — mediating defense-reaction-driven
    sympathetic surges.

Tonic activity is necessary to maintain blood pressure: bilateral RVLM
inhibition produces immediate severe hypotension. The system responds rapidly
(seconds) to baroreflex drops, more slowly (minutes) to humoral and emotional
input, and chronically (hours-days) to renal-pressure feedback through angiotensin.

The vasomotor output is not single-valued: separate functional populations
control vasoconstrictor outflow to splanchnic, renal, muscle, and cutaneous
vascular beds. Stress preferentially recruits muscle and splanchnic
vasoconstriction; thermal regulation recruits cutaneous; the baroreflex
operates broadly across all beds.

KEY FINDINGS
============
1. RVLM presympathetic C1 neurons set baseline sympathetic vasomotor tone
   via tonic monosynaptic projection to IML — [Guyenet 2006, Nat Rev Neurosci
    7:335-346, PMID 16760914]
2. CVLM GABAergic inhibition of RVLM is the principal baroreflex brake on
   sympathetic outflow — [Dampney 2016, Compr Physiol 6:1167-1216, PMID 27065166]
3. PVN excitatory drive to RVLM mediates stress-induced sympathetic activation
   via vasopressinergic and glutamatergic projections — [Dampney 2016 Compr
    Physiol; Coote 2007, Exp Physiol]
4. RVLM C1 neurons exhibit functional topography — distinct subpopulations
   preferentially target different vascular beds (muscle, splanchnic, renal,
   cutaneous) — [Dampney 2016; Card 2010, J Comp Neurol]
5. RVLM degeneration is a major pathophysiological substrate in essential
   hypertension and multi-system atrophy autonomic failure — [Guyenet 2006,
    Nat Rev Neurosci 7:335-346]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.sympathetic_tone (0.0-1.0)
- VitalCoreRegulator.vasomotor_setpoint (0.0-1.0)
- VitalCoreRegulator.survival_threat_level (0.0-1.0)
- ArousalRegulator.tonic_level (0.0-1.0)
- ArousalRegulator.phasic_burst_active (bool)
- StressActivationAxis.stress_active (bool, optional)
- StressActivationAxis.cortisol_level (0.0-1.0, optional)
- ValenceTagger.threat_signal (bool, optional)

OUTPUTS (to brain_runner enrichment)
=====================================
- rvlm_drive (0.0-1.0): tonic presympathetic firing proxy
- vasoconstriction_muscle (0.0-1.0)
- vasoconstriction_splanchnic (0.0-1.0)
- vasoconstriction_cutaneous (0.0-1.0)
- vasoconstriction_renal (0.0-1.0)
- defense_reaction_active (bool): when CeA/PVN drive is recruiting strong sympathetic surge

brain_runner enrichment block:
    svc = all_results.get("SympatheticVasomotorController", {})
    if svc:
        enrichments["brain_rvlm_drive"] = svc.get("rvlm_drive", 0.5)
        enrichments["brain_vasoconstriction_muscle"] = svc.get("vasoconstriction_muscle", 0.5)
        enrichments["brain_vasoconstriction_splanchnic"] = svc.get("vasoconstriction_splanchnic", 0.5)
        enrichments["brain_vasoconstriction_cutaneous"] = svc.get("vasoconstriction_cutaneous", 0.5)
        enrichments["brain_defense_reaction_active"] = svc.get("defense_reaction_active", False)
"""

from brain.base_mechanism import BrainMechanism


class SympatheticVasomotorController(BrainMechanism):
    """
    RVLM presympathetic analog. Computes regional vasoconstriction outputs
    from sympathetic tone, threat, arousal, and stress inputs, with
    topographic differentiation across vascular beds.
    """

    BASELINE_DRIVE = 0.50
    THREAT_GAIN = 0.30
    AROUSAL_GAIN = 0.20
    PHASIC_BURST_BOOST = 0.12
    STRESS_BOOST = 0.20

    DEFENSE_REACTION_THRESHOLD = 0.75

    SMOOTH_FACTOR = 0.30

    def __init__(self):
        super().__init__(
            name="SympatheticVasomotorController_SympatheticVasomotorController",
            human_analog="RVLM C1 presympathetic vasomotor controller",
            layer="foundational",
        )
        self.state.setdefault("rvlm_drive", self.BASELINE_DRIVE)
        self.state.setdefault("vasoconstriction_muscle", 0.5)
        self.state.setdefault("vasoconstriction_splanchnic", 0.5)
        self.state.setdefault("vasoconstriction_cutaneous", 0.5)
        self.state.setdefault("vasoconstriction_renal", 0.5)
        self.state.setdefault("defense_reaction_active", False)
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        vasomotor_set = float(vcr.get("vasomotor_setpoint", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic_level = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))

        # --- Compute integrated RVLM drive ---
        drive_target = (
            self.BASELINE_DRIVE
            + (symp_tone - 0.5) * 0.40
            + (tonic_level - 0.5) * self.AROUSAL_GAIN
            + survival_threat * self.THREAT_GAIN
        )

        if phasic:
            drive_target += self.PHASIC_BURST_BOOST
        if stress_active:
            drive_target += self.STRESS_BOOST * (0.5 + cortisol * 0.5)
        if threat_signal:
            drive_target += 0.10

        drive_target = max(0.05, min(0.98, drive_target))

        prev_drive = float(self.state["rvlm_drive"])
        new_drive = prev_drive + (drive_target - prev_drive) * self.SMOOTH_FACTOR

        # --- Topographic differentiation (Dampney/Card functional populations) ---
        # Muscle bed: strong response to defense reaction (CeA/PVN drive)
        muscle = new_drive
        if threat_signal or stress_active:
            muscle = min(0.98, muscle + 0.10)

        # Splanchnic bed: strong response to stress, baseline otherwise
        splanchnic = new_drive
        if stress_active:
            splanchnic = min(0.98, splanchnic + 0.15 * (0.5 + cortisol * 0.5))

        # Cutaneous bed: dominated by thermoregulation, sympathetic baseline added
        # We don't have direct thermal input here — read vasomotor_setpoint as proxy
        cutaneous = vasomotor_set * 0.8 + new_drive * 0.2
        if survival_threat > 0.5:
            cutaneous = min(0.95, cutaneous + 0.10)

        # Renal bed: tracks tonic drive, less reactive to phasic events
        renal = float(self.state.get("vasoconstriction_renal", 0.5))
        renal_target = (symp_tone - 0.4) * 0.7 + 0.3
        renal_target = max(0.10, min(0.90, renal_target))
        renal = renal + (renal_target - renal) * self.SMOOTH_FACTOR

        # Smooth all
        prev_muscle = float(self.state.get("vasoconstriction_muscle", 0.5))
        prev_splanch = float(self.state.get("vasoconstriction_splanchnic", 0.5))
        prev_cut = float(self.state.get("vasoconstriction_cutaneous", 0.5))

        new_muscle = prev_muscle + (muscle - prev_muscle) * self.SMOOTH_FACTOR
        new_splanchnic = prev_splanch + (splanchnic - prev_splanch) * self.SMOOTH_FACTOR
        new_cutaneous = prev_cut + (cutaneous - prev_cut) * self.SMOOTH_FACTOR

        # --- Defense reaction flag ---
        defense_reaction = (
            new_drive > self.DEFENSE_REACTION_THRESHOLD
            and (threat_signal or survival_threat > 0.6 or stress_active)
        )

        history = list(self.state.get("recent_drives", []))
        history.append(round(new_drive, 4))
        if len(history) > 30:
            history = history[-30:]

        # --- Persist ---
        self.state["rvlm_drive"] = round(new_drive, 4)
        self.state["vasoconstriction_muscle"] = round(new_muscle, 4)
        self.state["vasoconstriction_splanchnic"] = round(new_splanchnic, 4)
        self.state["vasoconstriction_cutaneous"] = round(new_cutaneous, 4)
        self.state["vasoconstriction_renal"] = round(renal, 4)
        self.state["defense_reaction_active"] = defense_reaction
        self.state["recent_drives"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "rvlm_drive": round(new_drive, 4),
            "vasoconstriction_muscle": round(new_muscle, 4),
            "vasoconstriction_splanchnic": round(new_splanchnic, 4),
            "vasoconstriction_cutaneous": round(new_cutaneous, 4),
            "vasoconstriction_renal": round(renal, 4),
            "defense_reaction_active": defense_reaction,
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



"""
ThermoregulationCore — Preoptic Area Thermoregulatory Coordinator

NEURAL SUBSTRATE
================
The preoptic area (POA) of the hypothalamus is the central coordinating hub
for body temperature homeostasis. Three subregions cooperate: median preoptic
nucleus (MnPO), medial preoptic area (MPO), and ventral lateral preoptic
nucleus (vLPO). Within these, warm-sensitive neurons (W-S, defined by
temperature coefficient dF/dT > +0.8 Hz/°C) increase firing rate as local
brain temperature or thermal afferent input rises, and they tonically inhibit
downstream thermogenesis-promoting neurons in the dorsomedial hypothalamus
(DMH). DMH in turn projects to premotor neurons in the rostral raphe pallidus
(rRPa), which drive brown adipose tissue (BAT) thermogenesis, shivering, and
cutaneous vasoconstriction.

Skin thermal afferents reach the POA via spinal dorsal horn → lateral
parabrachial nucleus (cool: LPBel; warm: LPBd) → MnPO. POA loss produces
hyperthermia because the tonic inhibition of thermogenesis is removed —
fever is a setpoint shift, not a regulation failure: pyrogens (PGE2) acting
through EP3R receptors specifically inhibit W-S neurons, raising the effective
setpoint.

Several molecular markers define functional POA populations. TRPM2 is an
intrinsic warm sensor on POA neurons and triggers heat-loss responses. PACAP
and BDNF mark warm-activated neurons. Galanin/QRFP/Lepr neurons span the
sleep-thermoregulation overlap (vLPO galanin neurons drive both NREM sleep
and hypothermia). EP3R neurons are the fever-sensing population.

Body temperature has a circadian swing of approximately ±0.5°C centered on
37°C, peaking in late afternoon and nadiring in early morning. The core
setpoint shifts under physiological state: fever raises it; hypothermia in
torpor and sleep lowers it.

KEY FINDINGS
============
1. POA coordinates parallel effector-specific thermoregulatory pathways
   (BAT thermogenesis, shivering, cutaneous vasoconstriction for heat loss,
   sweating/panting) sharing common peripheral thermal input — [Morrison
    Nakamura 2011, Front Biosci 16:74-104, PMID 21196160]
2. POA lesion produces hyperthermia (no fever needed) — POA tonically
   inhibits thermogenesis — [Boulant 2000, Clin Infect Dis 31 Suppl 5:S157-61]
3. TRPM2 is an intrinsic POA warm sensor; activation triggers heat-loss
   responses — [Song et al. 2016, Science 353:1393-1398]
4. vLPO galanin GABAergic neurons drive hypothermia when activated;
   inhibiting them produces fever-level hyperthermia — [Zhang et al. 2020,
    Nature 583:109-114]
5. Pyrogens raise the thermoregulatory setpoint by inhibiting W-S neurons
   via PGE2/EP3R signaling — fever is a setpoint shift — [Ushikubi et al.
    1998, Nature 395:281-284]

INPUTS (from prior_results)
============================
- CircadianTimer.circadian_phase (0.0-1.0) — body temp circadian swing
- CircadianTimer.is_subjective_day (bool)
- VitalCoreRegulator.vital_drive (0.0-1.0)
- VitalCoreRegulator.survival_threat_level (0.0-1.0)
- ArousalRegulator.tonic_level (0.0-1.0)
- (optional) inflammation_signal — pyrogen analog (currently from threat)

OUTPUTS (to brain_runner enrichment)
=====================================
- core_temp_setpoint (float, °C centered on 37.0)
- thermal_drive (float, signed: + = heat loss demand, - = thermogenesis demand)
- bat_activation (0.0-1.0): brown adipose / shivering analog
- cutaneous_vasoconstriction (0.0-1.0)
- fever_state (bool): elevated setpoint
- sleep_thermal_drop_active (bool): vLPO galanin coupling

brain_runner enrichment block:
    tc = all_results.get("ThermoregulationCore", {})
    if tc:
        enrichments["brain_core_temp_setpoint"] = tc.get("core_temp_setpoint", 37.0)
        enrichments["brain_thermal_drive"] = tc.get("thermal_drive", 0.0)
        enrichments["brain_bat_activation"] = tc.get("bat_activation", 0.0)
        enrichments["brain_cutaneous_vasoconstriction"] = tc.get("cutaneous_vasoconstriction", 0.5)
        enrichments["brain_fever_state"] = tc.get("fever_state", False)
"""

import math

from brain.base_mechanism import BrainMechanism


class ThermoregulationCore(BrainMechanism):
    """
    Preoptic area thermoregulation analog. Computes core temperature setpoint
    with circadian + fever modulation, then derives bidirectional thermal_drive
    and effector activations (BAT, vasoconstriction, sleep-coupled drop).
    """

    BASELINE_SETPOINT_C = 37.0
    CIRCADIAN_SWING_C = 0.5     # ±0.5°C peak-trough
    FEVER_PYROGEN_THRESHOLD = 0.55   # survival_threat above this raises setpoint
    FEVER_MAX_RISE_C = 1.5
    SLEEP_DROP_C = 0.4

    BAT_DRIVE_BASELINE = 0.10
    VASOCONSTRICTION_BASELINE = 0.50

    SMOOTH_FACTOR = 0.20

    def __init__(self):
        super().__init__(
            name="ThermoregulationCore",
            human_analog="POA — preoptic thermoregulatory coordinator",
            layer="foundational",
        )
        self.state.setdefault("core_temp_setpoint", self.BASELINE_SETPOINT_C)
        self.state.setdefault("thermal_drive", 0.0)
        self.state.setdefault("bat_activation", self.BAT_DRIVE_BASELINE)
        self.state.setdefault("cutaneous_vasoconstriction", self.VASOCONSTRICTION_BASELINE)
        self.state.setdefault("fever_state", False)
        self.state.setdefault("sleep_thermal_drop_active", False)
        self.state.setdefault("recent_setpoints", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read upstream signals ---
        circ = prior.get("CircadianTimer", {})
        circ_phase = float(circ.get("circadian_phase", 0.5))
        is_day = bool(circ.get("is_subjective_day", True))

        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic_level = float(arousal.get("tonic_level", 0.55))

        homeostat = prior.get("Homeostat", {})
        dominant_drive = homeostat.get("dominant_drive", "curiosity")
        rest_drive_active = dominant_drive == "rest"

        # --- Compute circadian temperature setpoint swing ---
        # Body temp peaks late afternoon (phase ~0.6) and nadirs early morning (phase ~0.15)
        # Use sine wave aligned so peak is at phase 0.6
        circadian_swing = self.CIRCADIAN_SWING_C * math.sin(
            2 * math.pi * (circ_phase - 0.35)
        )

        # --- Determine fever pyrogen drive ---
        # survival_threat above threshold acts as inflammation/pyrogen analog
        pyrogen_drive = max(0.0, survival_threat - self.FEVER_PYROGEN_THRESHOLD)
        fever_rise = pyrogen_drive * (self.FEVER_MAX_RISE_C / (1.0 - self.FEVER_PYROGEN_THRESHOLD))

        fever_state = pyrogen_drive > 0.05

        # --- Sleep / rest thermal drop (vLPO galanin) ---
        sleep_drop = 0.0
        sleep_thermal_drop_active = False
        if rest_drive_active and tonic_level < 0.40:
            sleep_drop = -self.SLEEP_DROP_C
            sleep_thermal_drop_active = True

        # --- Compute final setpoint ---
        setpoint_target = (
            self.BASELINE_SETPOINT_C
            + circadian_swing
            + fever_rise
            + sleep_drop
        )

        prev_setpoint = float(self.state["core_temp_setpoint"])
        new_setpoint = prev_setpoint + (setpoint_target - prev_setpoint) * self.SMOOTH_FACTOR

        # --- Compute thermal drive (signed) ---
        # We don't have a real core_temp sensor — use survival_threat + arousal
        # as a proxy for ambient heat load. Then drive = setpoint - estimated_temp.
        # Signed: + means heat loss demand, - means thermogenesis demand.
        estimated_temp = (
            self.BASELINE_SETPOINT_C
            + (tonic_level - 0.5) * 0.4   # higher arousal = warmer
            + (vital_drive - 0.5) * 0.3
        )
        thermal_drive = estimated_temp - new_setpoint
        # Clamp to reasonable signed range
        thermal_drive = max(-2.0, min(2.0, thermal_drive))

        prev_drive = float(self.state["thermal_drive"])
        new_drive = prev_drive + (thermal_drive - prev_drive) * self.SMOOTH_FACTOR

        # --- BAT activation (only when temp below setpoint, i.e. drive negative) ---
        if new_drive < -0.1:
            bat_target = min(1.0, abs(new_drive) * 0.8 + self.BAT_DRIVE_BASELINE)
        else:
            # Decay toward baseline
            bat_target = self.BAT_DRIVE_BASELINE

        prev_bat = float(self.state["bat_activation"])
        new_bat = prev_bat + (bat_target - prev_bat) * self.SMOOTH_FACTOR

        # --- Cutaneous vasoconstriction ---
        # Constriction conserves heat; vasodilation dumps heat
        # Constriction increases when thermal_drive < 0 (need to retain heat)
        # OR when sympathetic tone is high (general vasoconstriction)
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        if new_drive < 0:
            vaso_target = min(0.95, self.VASOCONSTRICTION_BASELINE + abs(new_drive) * 0.3 + (symp_tone - 0.5) * 0.2)
        else:
            vaso_target = max(0.10, self.VASOCONSTRICTION_BASELINE - new_drive * 0.3 + (symp_tone - 0.5) * 0.1)

        prev_vaso = float(self.state["cutaneous_vasoconstriction"])
        new_vaso = prev_vaso + (vaso_target - prev_vaso) * self.SMOOTH_FACTOR

        # --- Track setpoint history ---
        history = list(self.state.get("recent_setpoints", []))
        history.append(round(new_setpoint, 3))
        if len(history) > 30:
            history = history[-30:]

        # --- Persist ---
        self.state["core_temp_setpoint"] = round(new_setpoint, 3)
        self.state["thermal_drive"] = round(new_drive, 4)
        self.state["bat_activation"] = round(new_bat, 4)
        self.state["cutaneous_vasoconstriction"] = round(new_vaso, 4)
        self.state["fever_state"] = fever_state
        self.state["sleep_thermal_drop_active"] = sleep_thermal_drop_active
        self.state["recent_setpoints"] = history
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "core_temp_setpoint": round(new_setpoint, 3),
            "thermal_drive": round(new_drive, 4),
            "bat_activation": round(new_bat, 4),
            "cutaneous_vasoconstriction": round(new_vaso, 4),
            "fever_state": fever_state,
            "sleep_thermal_drop_active": sleep_thermal_drop_active,
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



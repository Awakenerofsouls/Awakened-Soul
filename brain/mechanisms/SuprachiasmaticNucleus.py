"""
SuprachiasmaticNucleus — SCN — Master Circadian Pacemaker

NEURAL SUBSTRATE
================
The suprachiasmatic nucleus (SCN) sits immediately above the optic chiasm
in the anterior hypothalamus and is the master circadian pacemaker of
mammals. The SCN is organized into two sub-domains:

- VIP+ "core" (ventrolateral): receives the retinohypothalamic tract
  (RHT) directly from intrinsically photosensitive retinal ganglion
  cells (ipRGCs) carrying photic information. Releases vasoactive
  intestinal polypeptide (VIP).
- AVP+ "shell" (dorsomedial): contains the bulk of arginine-vasopressin
  neurons; sustains the rhythmic output to downstream hypothalamic
  targets including subPVN, DMH and MPO.

Each SCN cell is an autonomous ~24-h oscillator driven by a transcription-
translation feedback loop (BMAL1/CLOCK ↔ PER/CRY). VIP neurons synchronize
the ~20,000-neuron network. SCN output drives the phase of pineal
melatonin, glucocorticoid rhythm (via PVN), core temperature minimum,
and sleep-wake propensity.

KEY FINDINGS
============
1. Individual SCN neurons are autonomous circadian oscillators with
   independently phased firing rhythms in dispersed culture —
   [Welsh D 1995, Neuron 14:697, doi:10.1016/0896-6273(95)90214-7]
2. Coordination of mammalian circadian timing: SCN as the master
   pacemaker network entrained by light via RHT —
   [Reppert S 2002, Nature 418:935, doi:10.1038/nature00965]
3. SCN cell autonomy and network properties: VIP-dependent synchrony
   among ~20,000 oscillators.
   [Welsh D 2010, Annu Rev Physiol 72:551, doi:10.1146/annurev-physiol-021909-135919]
4. Central and peripheral circadian clocks: SCN drives peripheral
   organ clocks via neural and humoral pathways.
   [Mohawk J 2012, Annu Rev Neurosci 35:445, doi:10.1146/annurev-neuro-060909-153128]
5. Synchronization mechanisms among SCN neurons via VIP, GABA and
   peptidergic coupling —
   [Aton S 2005, Neuron 48:531, doi:10.1016/j.neuron.2005.11.001]
6. Hypothalamic regulation of sleep and circadian rhythms: SCN gates
   the wake-sleep flip-flop through subPVN and DMH —
   [Saper C 2005, Nature 437:1257, doi:10.1038/nature04284]

INPUTS
======
- LateralGeniculateNucleus.light_signal (proxy for photic RHT input)
- ParaventricularNucleusThalamusAnterior.pvt_drive (arousal context)
- (intrinsic phase clock — runs on tick_count)

OUTPUTS
=======
- scn_drive (0-1)
- circadian_phase (0-1) — current normalized phase (0=dawn)
- vip_signal (0-1) — VIP core neurons
- avp_shell_signal (0-1) — shell vasopressin neurons
- subpvn_output (0-1) — to subparaventricular zone
- light_entrainment_signal (0-1)
- scn_state (str): "subjective_day" | "subjective_night" |
                    "phase_shifting" | "quiet"
"""

import math

from brain.base_mechanism import BrainMechanism


class SuprachiasmaticNucleus(BrainMechanism):
    """SCN — master circadian pacemaker."""

    BASELINE = 0.05  # Intrinsic clock runs; engagement requires input/light
    SMOOTH = 0.15
    PHASE_SHIFT_THRESHOLD = 0.30
    QUIET_THRESHOLD = 0.20
    DAY_PHASE_LOW = 0.0
    DAY_PHASE_HIGH = 0.5

    PERIOD_TICKS = 240  # ~24 h scaled to 240 ticks (test convenience)

    def __init__(self):
        super().__init__(
            name="SuprachiasmaticNucleus",
            human_analog="SCN (master circadian pacemaker)",
            layer="subcortical",
        )
        self.state.setdefault("scn_drive", self.BASELINE)
        self.state.setdefault("circadian_phase", 0.0)
        self.state.setdefault("vip_signal", 0.0)
        self.state.setdefault("avp_shell_signal", 0.0)
        self.state.setdefault("subpvn_output", 0.0)
        self.state.setdefault("light_entrainment_signal", 0.0)
        self.state.setdefault("scn_state", "quiet")
        self.state.setdefault("phase_offset", 0.0)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("entrainment_count", 0)

    def _intrinsic_phase(self) -> float:
        """Cell-autonomous oscillator (Welsh 1995)."""
        ticks = int(self.state.get("tick_count", 0))
        offset = float(self.state.get("phase_offset", 0.0))
        phase = ((ticks / self.PERIOD_TICKS) + offset) % 1.0
        return phase

    def _light_entrainment(self, light: float, phase: float) -> float:
        """Photic phase shift (Reppert 2002): light at subjective night
        advances/delays phase. Light at subjective day = no shift."""
        if light < 0.10:
            return 0.0
        # Phase response: light during early night delays, late night
        # advances; during day no shift.
        if 0.0 <= phase < 0.5:  # subjective day
            return 0.0
        # Light during night: shift magnitude
        return min(1.0, light * 0.5)

    def _apply_phase_shift(self, entrainment: float, phase: float):
        """Update phase offset based on light entrainment."""
        if entrainment < 0.10:
            return
        offset = float(self.state.get("phase_offset", 0.0))
        # Early subjective night (0.5-0.75): delay
        # Late subjective night (0.75-1.0): advance
        if 0.5 <= phase < 0.75:
            offset -= 0.005 * entrainment
        else:
            offset += 0.005 * entrainment
        self.state["phase_offset"] = offset % 1.0

    def _vip_signal(self, drive: float, light: float, phase: float) -> float:
        """VIP core release; peaks during subjective day light input
        (Aton 2005)."""
        day_factor = 1.0 if phase < 0.5 else 0.3
        return min(1.0, drive * 0.4 + light * 0.5 * day_factor)

    def _avp_shell(self, drive: float, phase: float) -> float:
        """AVP shell signal; peaks mid-subjective-day (Welsh 2010)."""
        # Sinusoidal peak around phase 0.25 (mid-day)
        amp = max(0.0, math.cos(2 * math.pi * (phase - 0.25)))
        return min(1.0, drive * 0.5 + amp * 0.5)

    def _subpvn(self, drive: float, avp: float, vip: float) -> float:
        """SCN→subPVN output (Saper 2005)."""
        return min(1.0, drive * 0.3 + avp * 0.4 + vip * 0.3)

    def _drive_target(self, light: float, phase: float) -> float:
        """SCN intrinsic drive modulated by phase (Mohawk 2012)."""
        # Drive is highest during subjective day; baseline plus light
        # entrainment input. Without external input, stays low.
        day_factor = 1.0 if phase < 0.5 else 0.4
        return min(1.0, self.BASELINE + light * 0.55 + day_factor * 0.10)

    def _classify_state(self, drive: float, phase: float,
                         entrainment: float, light: float) -> str:
        if drive < self.QUIET_THRESHOLD and light < 0.05:
            return "quiet"
        if entrainment > self.PHASE_SHIFT_THRESHOLD:
            return "phase_shifting"
        if self.DAY_PHASE_LOW <= phase < self.DAY_PHASE_HIGH:
            return "subjective_day"
        return "subjective_night"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        light = float(lgn_data.get("light_signal",
                            lgn_data.get("photic_drive", 0.0)))

        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        phase = self._intrinsic_phase()
        entrainment = self._light_entrainment(light, phase)
        self._apply_phase_shift(entrainment, phase)

        target = self._drive_target(light, phase)
        prev_drive = float(self.state.get("scn_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        vip = self._vip_signal(new_drive, light, phase)
        avp_s = self._avp_shell(new_drive, phase)
        sub = self._subpvn(new_drive, avp_s, vip)

        state = self._classify_state(new_drive, phase, entrainment, light)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        ec = int(self.state.get("entrainment_count", 0))
        if state == "phase_shifting":
            ec += 1

        self.state["scn_drive"] = round(new_drive, 4)
        self.state["circadian_phase"] = round(phase, 4)
        self.state["vip_signal"] = round(vip, 4)
        self.state["avp_shell_signal"] = round(avp_s, 4)
        self.state["subpvn_output"] = round(sub, 4)
        self.state["light_entrainment_signal"] = round(entrainment, 4)
        self.state["scn_state"] = state
        self.state["recent_states"] = recent
        self.state["entrainment_count"] = ec
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('scn_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('scn_state', "quiet") if 'scn_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "scn_drive": round(new_drive, 4),
            "circadian_phase": round(phase, 4),
            "vip_signal": round(vip, 4),
            "avp_shell_signal": round(avp_s, 4),
            "subpvn_output": round(sub, 4),
            "light_entrainment_signal": round(entrainment, 4),
            "scn_state": state,
        }

    def _entrainment_pressure(self) -> float:
        """Cumulative entrainment events index (Reppert 2002)."""
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("entrainment_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("scn_drive", 0.0),
            "phase": self.state.get("circadian_phase", 0.0),
            "state": self.state.get("scn_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return self.state.get('scn_state', "quiet") if 'scn_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('scn_drive', 0.0)) if 'scn_drive' else 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('scn_drive', 0.0) if 'scn_drive' else 0.0,
            "state": self.state.get('scn_state', "quiet") if 'scn_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


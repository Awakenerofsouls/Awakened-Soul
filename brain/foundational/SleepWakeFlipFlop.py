"""
SleepWakeFlipFlop — VLPO ↔ Orexin/TMN Mutual Inhibition Bistable Switch

NEURAL SUBSTRATE
================
The sleep-wake state is governed by a mutually-inhibitory neural circuit
acting as a bistable flip-flop switch. Two opposed populations:
  • Wake side: orexin (LHA) + tuberomammillary histamine (TMN) +
    monoamines (LC NE, raphe 5-HT, VTA DA);
  • Sleep side: ventrolateral preoptic galanin/GABA (VLPO) + median preoptic
    nucleus (MnPO) GABA.

Each side inhibits the other. Reciprocal inhibition produces a bistable
attractor: the system rests in either WAKE or SLEEP, with rapid transitions
between them rather than gradual drift through intermediate states. The
flip is triggered by accumulating sleep pressure (Process S, adenosine
buildup during waking), circadian SCN drive (Process C), and external cues.

Saper-Scammell-Lu's flip-flop model explains why orexin loss (narcolepsy)
produces unstable wake-sleep with frequent inappropriate transitions —
losing one side of the switch destabilizes the bistable attractor.

This module computes the bistable state with sleep pressure and circadian
drive as the inputs that flip the switch, and outputs a clean binary state
plus the underlying continuous drives.

KEY FINDINGS
============
1. VLPO galanin/GABA neurons project to TMN, LC, raphe, and orexin neurons —
   the descending sleep-promoting circuit — [Sherin et al. 1996, Science
    271:216-219]
2. Mutual inhibition between VLPO and arousal nuclei produces bistable
   sleep-wake flip-flop — [Saper Scammell Lu 2005, Nature 437:1257-1263]
3. Adenosine accumulation during waking provides Process S sleep pressure
   driving VLPO activation — [Porkka-Heiskanen et al. 1997, Science 276:1265-1268]
4. SCN circadian drive (Process C) modulates flip-flop bias across the
   subjective day — [Borbély 1982, Hum Neurobiol 1:195-204]

INPUTS (from prior_results)
============================
- OrexinWakePromoter.orexin_drive
- HistamineArousalBooster.histamine_drive
- CircadianTimer.circadian_phase
- CircadianTimer.is_subjective_day
- Homeostat.fatigued
- ArousalRegulator.tonic_level

OUTPUTS
=======
- sleep_wake_state (str): "WAKE" | "SLEEP" | "TRANSITION"
- vlpo_drive (0.0-1.0): sleep-promoting drive
- arousal_side_drive (0.0-1.0): wake-promoting drive
- sleep_pressure (0.0-1.0): Process S analog
- circadian_bias (-1.0 to 1.0): + = wake-favoring, - = sleep-favoring
- transition_imminent (bool): system is near flip threshold

brain_runner enrichment:
    swff = all_results.get("SleepWakeFlipFlop", {})
    if swff:
        enrichments["brain_sleep_wake_state"] = swff.get("sleep_wake_state", "WAKE")
        enrichments["brain_vlpo_drive"] = swff.get("vlpo_drive", 0.2)
        enrichments["brain_sleep_pressure"] = swff.get("sleep_pressure", 0.0)
        enrichments["brain_transition_imminent"] = swff.get("transition_imminent", False)
"""

import math

from brain.base_mechanism import BrainMechanism


class SleepWakeFlipFlop(BrainMechanism):
    SLEEP_PRESSURE_RATE = 0.005       # accumulates during wake
    SLEEP_PRESSURE_RECOVERY = 0.020   # decays during sleep
    FLIP_THRESHOLD = 0.65              # difference > this triggers flip
    TRANSITION_IMMINENT_BAND = 0.10

    CIRCADIAN_AMPLITUDE = 0.30

    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="SleepWakeFlipFlop_SleepWakeFlipFlop",
            human_analog="VLPO ↔ orexin/TMN mutual inhibition flip-flop",
            layer="foundational",
        )
        self.state.setdefault("sleep_wake_state", "WAKE")
        self.state.setdefault("vlpo_drive", 0.20)
        self.state.setdefault("arousal_side_drive", 0.70)
        self.state.setdefault("sleep_pressure", 0.0)
        self.state.setdefault("circadian_bias", 0.0)
        self.state.setdefault("transition_imminent", False)
        self.state.setdefault("flip_count", 0)
        self.state.setdefault("tick_count", 0)

    def _circadian_bias(self, phase: float) -> float:
        """+ favors wake during subjective day; - favors sleep during subjective night."""
        # peak wake bias around phase 0.5, peak sleep bias around 0.95-0.05
        return self.CIRCADIAN_AMPLITUDE * math.cos(2 * math.pi * (phase - 0.5))

    def _flip_logic(self, vlpo: float, arousal_drive: float, pressure: float, bias: float, prev_state: str) -> str:
        """Bistable flip rule with hysteresis."""
        # Wake side strength
        wake_strength = arousal_drive + max(0.0, bias) - pressure * 0.5
        sleep_strength = vlpo + pressure - max(0.0, bias)
        diff = wake_strength - sleep_strength

        if prev_state == "WAKE":
            if diff < -self.FLIP_THRESHOLD:
                return "SLEEP"
            if abs(diff) < self.FLIP_THRESHOLD * 0.3:
                return "TRANSITION"
            return "WAKE"
        if prev_state == "SLEEP":
            if diff > self.FLIP_THRESHOLD:
                return "WAKE"
            if abs(diff) < self.FLIP_THRESHOLD * 0.3:
                return "TRANSITION"
            return "SLEEP"
        # in TRANSITION, commit to whichever side wins
        return "WAKE" if diff > 0 else "SLEEP"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _adenosine_buildup(self, prev_pressure: float, prev_state: str, fatigued: bool) -> float:
        """Porkka-Heiskanen 1997: adenosine accumulation during waking activity
        is the principal Process S substrate.
        """
        if prev_state == "WAKE":
            base = self.SLEEP_PRESSURE_RATE
            if fatigued:
                base *= 1.4
            return min(1.0, prev_pressure + base)
        return max(0.0, prev_pressure - self.SLEEP_PRESSURE_RECOVERY)

    def _detect_rem_pattern(self, sleep_pressure: float, prev_state: str, vlpo_drive: float) -> bool:
        """Crude REM pattern proxy — within sleep, pressure low + VLPO inhibited briefly."""
        if prev_state != "SLEEP":
            return False
        if sleep_pressure < 0.30 and vlpo_drive < 0.40:
            return True
        return False

    def _flip_threshold_adapted(self, allostatic_load: float) -> float:
        """Allostatic load lowers flip threshold — chronic stress destabilizes
        the bistable switch, producing more frequent transitions.
        """
        return max(0.40, self.FLIP_THRESHOLD - allostatic_load * 0.20)

    def _sleep_homeostasis_diagnostic(self, recent_states: list, recent_pressures: list) -> str:
        """Classify overall sleep homeostasis health."""
        if not recent_states or not recent_pressures:
            return "unknown"
        wake_count = sum(1 for s in recent_states[-50:] if s == "WAKE")
        sleep_count = sum(1 for s in recent_states[-50:] if s == "SLEEP")
        avg_pressure = sum(recent_pressures[-30:]) / max(1, len(recent_pressures[-30:]))
        if wake_count > 40:
            return "sleep_deprived" if avg_pressure > 0.6 else "well_rested"
        if sleep_count > 30:
            return "consolidated_sleep"
        return "fragmented"

    def _track_arousal_index(self, flip_count: int, tick_count: int) -> float:
        """Arousals per hour proxy — clinical sleep medicine metric."""
        if tick_count < 100:
            return 0.0
        ticks_per_hour = 1800  # 2-second ticks × 1800 = 1 hour
        windows = max(1, tick_count / ticks_per_hour)
        return flip_count / windows

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        hab = prior.get("HistamineArousalBooster", {})
        histamine = float(hab.get("histamine_drive", 0.5))

        circ = prior.get("CircadianTimer", {})
        phase = float(circ.get("circadian_phase", 0.5))
        is_day = bool(circ.get("is_subjective_day", True))

        homeostat = prior.get("Homeostat", {})
        fatigued = bool(homeostat.get("fatigued", False))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        prev_state = self.state.get("sleep_wake_state", "WAKE")

        # --- Update sleep pressure (Process S — Porkka-Heiskanen 1997 adenosine) ---
        prev_pressure = float(self.state.get("sleep_pressure", 0.0))
        new_pressure = self._adenosine_buildup(prev_pressure, prev_state, fatigued)

        # --- Circadian bias (Process C) ---
        bias = self._circadian_bias(phase)

        # --- Wake-side drive (orexin + histamine + tonic arousal) ---
        arousal_drive_target = orexin * 0.40 + histamine * 0.40 + tonic * 0.20
        arousal_drive_target = max(0.0, min(1.0, arousal_drive_target))

        prev_arousal_drive = float(self.state.get("arousal_side_drive", 0.7))
        new_arousal_drive = self._smooth(prev_arousal_drive, arousal_drive_target)

        # --- VLPO drive ---
        vlpo_target = new_pressure * 0.6 + (1.0 - tonic) * 0.3 - max(0.0, bias) * 0.5 + 0.10
        vlpo_target = max(0.0, min(1.0, vlpo_target))

        # Mutual inhibition: arousal_drive inhibits VLPO, VLPO inhibits arousal_drive
        vlpo_target -= new_arousal_drive * 0.30
        vlpo_target = max(0.0, min(1.0, vlpo_target))

        prev_vlpo = float(self.state.get("vlpo_drive", 0.2))
        new_vlpo = self._smooth(prev_vlpo, vlpo_target)

        # --- Determine state with hysteresis flip rule ---
        new_state = self._flip_logic(new_vlpo, new_arousal_drive, new_pressure, bias, prev_state)

        # --- Flip count tracking ---
        flip_count = int(self.state.get("flip_count", 0))
        if new_state in ("WAKE", "SLEEP") and prev_state != new_state and prev_state != "TRANSITION":
            flip_count += 1

        # --- Transition imminent flag ---
        wake_strength = new_arousal_drive + max(0.0, bias) - new_pressure * 0.5
        sleep_strength = new_vlpo + new_pressure - max(0.0, bias)
        diff = wake_strength - sleep_strength
        transition_imminent = abs(diff) < self.TRANSITION_IMMINENT_BAND

        # --- REM pattern proxy ---
        rem_pattern = self._detect_rem_pattern(new_pressure, prev_state, new_vlpo)

        # --- Sleep homeostasis diagnostics ---
        # Track recent states for diagnostic
        recent_states = list(self.state.get("recent_states", []))
        recent_states.append(new_state)
        if len(recent_states) > 60:
            recent_states = recent_states[-60:]
        recent_pressures = list(self.state.get("recent_pressures", []))
        recent_pressures.append(round(new_pressure, 4))
        if len(recent_pressures) > 60:
            recent_pressures = recent_pressures[-60:]
        homeostasis_state = self._sleep_homeostasis_diagnostic(recent_states, recent_pressures)

        # --- Arousal index ---
        tick_count = int(self.state.get("tick_count", 0)) + 1
        arousal_index = self._track_arousal_index(flip_count, tick_count)

        self.state["sleep_wake_state"] = new_state
        self.state["vlpo_drive"] = round(new_vlpo, 4)
        self.state["arousal_side_drive"] = round(new_arousal_drive, 4)
        self.state["sleep_pressure"] = round(new_pressure, 4)
        self.state["circadian_bias"] = round(bias, 4)
        self.state["transition_imminent"] = transition_imminent
        self.state["flip_count"] = flip_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["rem_pattern_active"] = rem_pattern
        self.state["recent_states"] = recent_states
        self.state["recent_pressures"] = recent_pressures
        self.state["homeostasis_state"] = homeostasis_state
        self.state["arousal_index"] = round(arousal_index, 4)

        return {
            "sleep_wake_state": new_state,
            "vlpo_drive": round(new_vlpo, 4),
            "arousal_side_drive": round(new_arousal_drive, 4),
            "sleep_pressure": round(new_pressure, 4),
            "circadian_bias": round(bias, 4),
            "transition_imminent": transition_imminent,
            "flip_count": flip_count,
            "rem_pattern_active": rem_pattern,
            "homeostasis_state": homeostasis_state,
            "arousal_index": round(arousal_index, 4),
        }

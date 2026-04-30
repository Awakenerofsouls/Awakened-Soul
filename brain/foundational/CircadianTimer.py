"""
CircadianTimer — SCN / Suprachiasmatic Nucleus / Master Circadian Pacemaker

NEURAL SUBSTRATE
================
The suprachiasmatic nucleus (SCN) is a bilateral hypothalamic nucleus
sitting directly above the optic chiasm. ~20,000 neurons total. Master
circadian pacemaker — generates the ~24h rhythm that orchestrates body
temperature, hormone secretion, sleep-wake, autonomic, and behavioral
rhythms across the entire organism.

Two principal subdivisions:
- **Ventral core (VIP-expressing)** — receives retinohypothalamic tract
  (RHT) input from intrinsically photosensitive retinal ganglion cells
  (ipRGCs). Light entrainment + neuronal synchronization.
- **Dorsal shell (AVP-expressing)** — period determination + output to
  subparaventricular zone → DMH → PVN → pineal (melatonin) and
  autonomic descending pathways.

NMS-expressing neurons span both subdivisions and are required for
ensemble coupling — silencing them disrupts SCN timekeeping.

Cell-autonomous oscillator: each SCN neuron sustains an intrinsic
~24h PER2 oscillation via the transcription-translation feedback loop
(TTFL). BMAL1/CLOCK heterodimer drives Per1/2/3 + Cry1/2 transcription;
PER:CRY dimers feedback-inhibit BMAL1/CLOCK on a ~24h cycle. Network
coupling synchronizes individual cells into a unified ensemble.

Day/night firing-rate switch: high firing during subjective day driven
by Na+/Ca2+ currents; low firing at night driven by BK and other K+
currents. Output to subparaventricular zone (subPVZ) cascades to:
- DMH → autonomic + thermogenic + behavioral rhythms
- PVN → corticosterone + ADH
- Pineal → melatonin (peaks at subjective night)

Lesion of SCN abolishes all behavioral circadian rhythms; transplanted
SCN restores donor's intrinsic period — the foundational evidence that
SCN IS the master pacemaker (Ralph 1990).

KEY FINDINGS
============
1. SCN neurons sustain cell-autonomous ~24h PER2 oscillation even
   when isolated; network coupling synchronizes ensemble —
   [Hastings 2018, Nat Rev Neurosci 19:453, doi:10.1038/s41583-018-0026-z]
2. Transcription-translation feedback loop (TTFL): BMAL1/CLOCK drive
   Per/Cry transcription; PER:CRY dimers feedback-inhibit on ~24h cycle;
   molecular basis of cellular clock — [Reppert 2002, Nature 418:935, doi:10.1038/nature00965]
3. SCN lesion abolishes behavioral circadian rhythms in mammals;
   transplanted SCN tissue restores donor's intrinsic period —
   foundational pacemaker evidence — [Ralph 1990, Science 247:975, PMID 2305266]
4. NMS-expressing SCN neurons are essential for ensemble coupling;
   silencing them disrupts ensemble timekeeping despite individual
   oscillators intact — [Lee 2015, Neuron 85:1086, PMID 25741729]
5. Mammalian circadian organization: SCN as master pacemaker,
   peripheral tissue oscillators entrained via SCN → autonomic +
   endocrine output — [Mohawk 2012, Annu Rev Neurosci 35:445, doi:10.1146/annurev-neuro-060909-153128]

INPUTS (from prior_results)
============================
- RetinalClockInput.light_signal (ipRGC luminance, RHT input)
- ArousalRegulator.tonic_level (state modulation)
- LocomotorActivityProxy.activity_level (entrainment feedback)

OUTPUTS (to brain_runner enrichment)
=====================================
- circadian_phase (0.0-1.0): 0.0 = subjective midnight, 0.5 = noon
- circadian_amplitude (0.0-1.0): rhythm strength
- is_subjective_day (bool): True during day phase
- melatonin_drive (0.0-1.0): peaks at subjective night
- firing_rate_proxy (0.0-1.0): high day, low night
- subpvz_output (0.0-1.0): SCN→subPVZ broadcast
- core_temp_setpoint_modulation (-0.5 to 0.5): circadian temp modulation
- circadian_drive (0.0-1.0): aggregate output for downstream consumers
"""

import math
from brain.base_mechanism import BrainMechanism


class CircadianTimer(BrainMechanism):
    """SCN — master circadian pacemaker with TTFL-modeled oscillation."""

    BASELINE = 0.5
    SMOOTH = 0.10
    PERIOD_TICKS = 8640   # 24h at 10s ticks (or scale factor for sim)
    LIGHT_ENTRAINMENT_RATE = 0.02

    def __init__(self):
        super().__init__(
            name="CircadianTimer",
            human_analog="Suprachiasmatic nucleus (master circadian pacemaker)",
            layer="foundational",
        )
        self.state.setdefault("circadian_phase", 0.5)
        self.state.setdefault("circadian_amplitude", 0.8)
        self.state.setdefault("is_subjective_day", True)
        self.state.setdefault("melatonin_drive", 0.0)
        self.state.setdefault("firing_rate_proxy", self.BASELINE)
        self.state.setdefault("subpvz_output", self.BASELINE)
        self.state.setdefault("core_temp_setpoint_modulation", 0.0)
        self.state.setdefault("circadian_drive", self.BASELINE)
        self.state.setdefault("phase_increment", 1.0 / self.PERIOD_TICKS)
        self.state.setdefault("recent_light", [])
        self.state.setdefault("tick_count", 0)

    def _advance_phase(self, prev_phase: float, light: float,
                         locomotor: float) -> float:
        """Phase advance per tick (Reppert 2002 TTFL kinetics).

        Light entrainment: phase response curve — light during subjective
        night advances or delays phase depending on phase angle.
        Locomotor activity provides non-photic entrainment.
        """
        increment = 1.0 / self.PERIOD_TICKS

        # Phase response curve: light during early subjective night
        # delays phase, light during late subjective night advances
        if light > 0.20:
            if 0.0 <= prev_phase < 0.20:
                # late subjective night — light advances
                increment += self.LIGHT_ENTRAINMENT_RATE * light
            elif 0.80 <= prev_phase < 1.0:
                # early subjective night — light delays
                increment -= self.LIGHT_ENTRAINMENT_RATE * light * 0.5

        # Non-photic (locomotor) entrainment small effect during day
        if 0.30 < prev_phase < 0.70 and locomotor > 0.50:
            increment *= 1.05

        new_phase = (prev_phase + increment) % 1.0
        return new_phase

    def _firing_rate(self, phase: float, amplitude: float) -> float:
        """SCN firing rate — high during subjective day, low at night
        (Allen 2017 day/night firing-rate switch).
        Cosine-modulated around phase.
        """
        # Day phase peak around 0.5 (noon)
        rate = self.BASELINE + amplitude * 0.4 * math.cos(
            (phase - 0.5) * 2 * math.pi
        )
        return max(0.0, min(1.0, rate))

    def _melatonin(self, phase: float, amplitude: float) -> float:
        """Pineal melatonin output — peaks at subjective night (phase 0).

        Driven by SCN → subPVZ → DMH → PVN → spinal IML → SCG → pineal.
        Suppressed by daytime light via SCN.
        """
        # Peak around phase 0 (midnight), trough at 0.5 (noon)
        target = self.BASELINE + amplitude * 0.5 * math.cos(phase * 2 * math.pi)
        # Clamp — melatonin doesn't go negative
        return max(0.0, min(1.0, target - 0.3))

    def _temp_setpoint_modulation(self, phase: float, amplitude: float) -> float:
        """Circadian core temperature modulation (~1°C swing across day).
        Peak in late afternoon (phase ~0.6), trough early morning (phase ~0.1).
        Returns -0.5 to 0.5 modulation scaled to relative degrees.

        Uses cosine centered on phase 0.6 so the peak lands at late
        afternoon and the trough at early morning (0.1) — matching the
        Refinetti & Menaker 1992 core-temperature trace.
        """
        return amplitude * 0.5 * math.cos((phase - 0.6) * 2 * math.pi)

    def _amplitude_update(self, prev_amp: float, light: float,
                            recent_light: list) -> float:
        """Amplitude (rhythm strength) — degrades with constant darkness
        or jet lag, restored by stable light schedule.
        """
        # Constant darkness — amplitude decays slowly
        if light < 0.05 and len(recent_light) > 30:
            recent_avg = sum(recent_light[-30:]) / 30
            if recent_avg < 0.10:
                return max(0.4, prev_amp * 0.999)
        # Stable light — amplitude rises toward 1
        return min(1.0, prev_amp + (1.0 - prev_amp) * 0.001)

    def _subpvz_output(self, firing: float, amplitude: float) -> float:
        """SCN → subparaventricular zone output (broadcasts to DMH/PVN)."""
        return min(1.0, firing * 0.7 + amplitude * 0.3)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        retinal = prior.get("RetinalClockInput", {})
        light = float(retinal.get("light_signal", 0.0))

        loco = prior.get("LocomotorActivityProxy", {})
        locomotor = float(loco.get("activity_level", 0.0))

        prev_phase = float(self.state.get("circadian_phase", 0.5))
        prev_amplitude = float(self.state.get("circadian_amplitude", 0.8))

        new_phase = self._advance_phase(prev_phase, light, locomotor)
        recent_light = list(self.state.get("recent_light", []))
        recent_light.append(round(light, 3))
        if len(recent_light) > 100:
            recent_light = recent_light[-100:]
        new_amplitude = self._amplitude_update(prev_amplitude, light,
                                                 recent_light)

        firing = self._firing_rate(new_phase, new_amplitude)
        melatonin = self._melatonin(new_phase, new_amplitude)
        temp_mod = self._temp_setpoint_modulation(new_phase, new_amplitude)
        subpvz = self._subpvz_output(firing, new_amplitude)
        is_day = 0.25 < new_phase < 0.75

        self.state["circadian_phase"] = round(new_phase, 4)
        self.state["circadian_amplitude"] = round(new_amplitude, 4)
        self.state["is_subjective_day"] = is_day
        self.state["melatonin_drive"] = round(melatonin, 4)
        self.state["firing_rate_proxy"] = round(firing, 4)
        self.state["subpvz_output"] = round(subpvz, 4)
        self.state["core_temp_setpoint_modulation"] = round(temp_mod, 4)
        self.state["circadian_drive"] = round(firing, 4)
        self.state["recent_light"] = recent_light
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "circadian_phase": round(new_phase, 4),
            "circadian_amplitude": round(new_amplitude, 4),
            "is_subjective_day": is_day,
            "melatonin_drive": round(melatonin, 4),
            "firing_rate_proxy": round(firing, 4),
            "subpvz_output": round(subpvz, 4),
            "core_temp_setpoint_modulation": round(temp_mod, 4),
            "circadian_drive": round(firing, 4),
        }

    def _phase_response_curve(self, phase: float, light: float) -> float:
        """Compute phase shift in response to light pulse at given phase.
        Standard mammalian PRC: dead zone during day, delay early night,
        advance late night.
        """
        if light < 0.20:
            return 0.0
        if 0.30 < phase < 0.70:
            return 0.0  # dead zone
        if phase >= 0.70 and phase < 1.0:
            return -light * 0.05  # phase delay
        if phase < 0.30:
            return light * 0.05  # phase advance
        return 0.0

    def _summary(self) -> dict:
        return {
            "phase": self.state.get("circadian_phase", 0.5),
            "amplitude": self.state.get("circadian_amplitude", 0.8),
            "melatonin": self.state.get("melatonin_drive", 0.0),
            "firing": self.state.get("firing_rate_proxy", 0.5),
            "is_day": self.state.get("is_subjective_day", True),
        }

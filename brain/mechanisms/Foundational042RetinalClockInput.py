"""
Build 42: Foundational042RetinalClockInput — Suprachiasmatic Nucleus Light Entrainment
===================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — suprachiasmatic nucleus, SCN)
  Filename: brain/foundational/Foundational042RetinalClockInput.py
  Instance name: RetinalClockInput

NEURAL SUBSTRATE:
  Suprachiasmatic nucleus (SCN) — the master circadian clock. Contains
  ~20,000 neurons (in humans) with autonomous molecular clocks (CLOCK/BMAL1/
  PER/CRY transcriptional/translational feedback loops). The SCN receives
  direct photic input via the retinohypothalamic tract (RHT) from
  intrinsically photosensitive retinal ganglion cells (ipRGCs) expressing
  melanopsin (OPN4).

  KEY SCN FUNCTIONS:
  - Entrains to light-dark cycles (zeitgeber)
  - Generates ~24-hour circadian rhythm in all physiological variables
  - Drives melatonin release (pineal gland via PVN) — darkness signal
  - Coordinates peripheral clocks (SCN → autonomic nervous system)

  PHOTIC INPUT PATHWAY:
  ipRGC → SCN (direct) + OPN → LGN → V1 cortex (indirect, for conscious awareness)

  Human analog: circadian rhythm, jet lag, seasonal affective disorder.

Output keys:
  circadian_phase: float [0.0–1.0] — current circadian time (0=midnight, 0.5=noon)
  light_entrainment_strength: float [0.0–1.0] — SCN light-driven resetting
  melatonin_drive: float [0.0–1.0] — pineal melatonin release signal
  circadian_arousal: float [0.0–1.0] — SCN-driven wakefulness
  peripheral_clock_sync: float [0.0–1.0] — SCN → peripheral organ synchronization

CITATIONS:
    PMC5451709 — Tsuji T, Allchorne AJ, Zhang M et al. (2017). Vasopressin Casts
        Light on the Suprachiasmatic Nucleus. J Neurosci.
    PMC10449486 — Calligaro H, Shoghi A, Chen X et al. (2023). Ultrastructure of
        Synaptic Connectivity Within Subregions of the Suprachiasmatic Nucleus.
        J Comp Neurol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism
import numpy as np


class RetinalClockInput(BrainMechanism):
    """
    SCN circadian clock: light entrainment, melatonin, circadian arousal.

    Models the molecular clock in SCN neurons with light-driven entrainment
    and melatonin release drive.
    """

    STATE_FIELDS = [
        "circadian_phase", "light_entrainment_strength", "melatonin_drive",
        "circadian_arousal", "peripheral_clock_sync", "tick_count",
    ]

    CLOCK_PERIOD = 1.0        # one full cycle per tick (normalized 24h)
    MELATONIN_GATE_OPEN = 0.7  # melatonin fires when phase > this value
    LIGHT_RESET_GAIN = 0.08    # light shifts clock slowly
    AROUSAL_GAIN = 0.55

    def __init__(self, name: str = "RetinalClockInput",
                 human_analog: str = "SCN — retinohypothalamic circadian clock",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["circadian_phase"] = 0.50  # start at noon
        self.state["light_entrainment_strength"] = 0.60
        self.state["melatonin_drive"] = 0.0
        self.state["circadian_arousal"] = 0.50
        self.state["peripheral_clock_sync"] = 0.60
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        light_level = prior.get("LightLevelDetector", {}).get("light_level", 0.50)
        ambient = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        temperature = prior.get("CoreTemperatureMonitor", {}).get("core_temperature", 0.50)

        current_phase = self.state["circadian_phase"]

        # Advance clock: one tick ≈ one hour (in normalized time)
        new_phase = current_phase + 0.04
        if new_phase >= 1.0:
            new_phase -= 1.0

        # Light entrainment: light shifts phase (phase-response curve)
        # Light during subjective night → phase advance
        # Light during subjective day → phase delay
        if new_phase > 0.7 or new_phase < 0.2:  # subjective night
            light_shift = light_level * self.LIGHT_RESET_GAIN
        else:  # subjective day
            light_shift = -light_level * self.LIGHT_RESET_GAIN * 0.5
        new_phase = (new_phase + light_shift) % 1.0

        # Melatonin drive: darkness triggers melatonin release (pineal gland via PVN)
        # Melatonin fires during the melatonin gate (subjective night, phase > 0.7)
        if new_phase > self.MELATONIN_GATE_OPEN:
            # Light suppresses melatonin even during the gate
            melatonin_drive = (new_phase - self.MELATONIN_GATE_OPEN) / (1.0 - self.MELATONIN_GATE_OPEN)
            melatonin_drive *= (1.0 - light_level * 0.90)
        else:
            melatonin_drive = 0.0
        melatonin_drive = min(1.0, max(0.0, melatonin_drive))

        # Circadian arousal: high during subjective day, low at night
        # Uses sinusoidal template (peaks at noon, trough at midnight)
        phase_angle = new_phase * 2.0 * np.pi
        circadian_arousal = 0.50 + 0.50 * np.sin(phase_angle - (np.pi / 2))
        circadian_arousal = max(0.0, min(1.0, circadian_arousal))

        # Light entrainment strength: brighter light → stronger entrainment
        light_entrainment = 0.30 + light_level * 0.50

        # Peripheral clock sync: temperature also entrains peripheral clocks
        temp_sync = (1.0 - abs(temperature - 0.50) * 2.0) * 0.20
        peripheral_clock_sync = (light_entrainment * 0.60) + temp_sync

        # --- Persist ---
        self.state["circadian_phase"] = round(new_phase, 4)
        self.state["light_entrainment_strength"] = round(light_entrainment, 4)
        self.state["melatonin_drive"] = round(melatonin_drive, 4)
        self.state["circadian_arousal"] = round(circadian_arousal, 4)
        self.state["peripheral_clock_sync"] = round(peripheral_clock_sync, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "circadian_phase": round(new_phase, 4),
            "light_entrainment_strength": round(light_entrainment, 4),
            "melatonin_drive": round(melatonin_drive, 4),
            "circadian_arousal": round(circadian_arousal, 4),
            "peripheral_clock_sync": round(peripheral_clock_sync, 4),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
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

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


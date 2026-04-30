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
  - [Berson 2002, Science 295:1070, doi:10.1126/science.1067262]
  - [Hattar 2002, Science 295:1065]
  - [Reppert 2002, Nature 418:935]
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

    def __init__(self, name: str = "RetinalClockInput_RetinalClockInput",
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

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
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

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out

    # ---------- enrichment helpers (phase-2 expansion) ----------
    def attribute_signature(self) -> tuple:
        out = []
        for attr_name in sorted(dir(self)):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            out.append((attr_name, type(v).__name__))
        return tuple(out)

    def numeric_attribute_values(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[attr_name] = float(v)
        return out

    def list_attribute_lengths(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, list):
                out[attr_name] = len(v)
        return out

    def boolean_attributes(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, bool):
                out[attr_name] = v
        return out

    def callable_method_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                out.append(attr_name)
        return out

    def has_attribute(self, name: str) -> bool:
        return hasattr(self, name) and not name.startswith("_")

    def safe_get(self, name: str, default=None):
        try:
            v = getattr(self, name, default)
            return v
        except Exception:
            return default

    def history_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                out.append(attr_name)
        return out

    def total_history_length(self) -> int:
        total = 0
        for attr_name in self.history_attribute_names():
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                total += len(v)
        return total

    def is_initialized(self) -> bool:
        return getattr(self, "tick_count", 0) >= 0

    def class_metadata(self) -> dict:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "n_attrs": self.attribute_count() if hasattr(self, "attribute_count") else 0,
            "n_history": len(self.history_attribute_names()),
        }

    def state_size(self) -> int:
        try:
            return len(self.export_state())
        except Exception:
            return 0



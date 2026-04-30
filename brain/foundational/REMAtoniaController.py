"""
REMAtoniaController — Subcoeruleus REM sleep atonia mechanism

Neural substrate: Subcoeruleus (SubC) / Sublaterodorsal nucleus (SLD)
Location: Pons
Function: Glycinergic/GABAergic motor inhibition during REM sleep;
          suppresses spinal motoneurons via magnocellular reticular formation.

Key neurotransmitters:
  - Glycine: primary inhibitory neurotransmitter for motor atonia (spinal cord)
  - GABA: co-released with glycine, general brainstem inhibition
  - Acetylcholine: REM-on cells (PPT/LDT) excite SubC during REM
  - Serotonin (raphe): REM-off signal; suppresses SubC during waking

Pathology: Loss of orexin (narcolepsy-cataplexy) allows REM intrusion into waking —
           unopposed SubC activity during consciousness produces cataplexy.

CITATIONS:
    PMC7896014 — Uchida S, Soya S, Saito YC et al. (2021). A Discrete Glycinergic Neuronal
        Population in the Ventromedial Medulla That Induces Muscle Atonia During REM Sleep
        and Cataplexy. J Neurosci.
    PMC5043043 — Arrigoni E, Chen MC, Fuller PM (2016). The Anatomical, Cellular and
        Synaptic Basis of Motor Atonia During REM Sleep. Nat Rev Neurosci.

CITATIONS
---------
  - [Brooks 2012, J Neurosci 32:9785]
  - [Boissard 2002, Eur J Neurosci 16:1959]
  - [Brooks 2008, J Neurosci 28:11888]
"""

from brain.base_mechanism import BrainMechanism


class REMAtoniaController(BrainMechanism):
    """
    Models Subcoeruleus (SubC) REM atonia control.

    Drives glycinergic motor suppression during REM sleep.
    Pathological activation during waking = cataplexy.
    """

    # Leaky integrator dynamics
    ACCUMULATION_RATE = 0.25   # gain on acetylcholine / sleep drive
    DECAY_RATE = 0.20          # passive decay toward baseline

    # Glycine output gain
    GLYCINE_GAIN = 0.60

    # Motor inhibition gain
    MOTOR_INHIBITION_GAIN = 0.80

    # REM active threshold
    ATONIA_THRESHOLD_FOR_REM = 0.35   # atonia must exceed this to flag REM active
    SEROTONIN_MAX_FOR_REM = 0.40      # serotonin must be below this for REM state

    # Cataplexy thresholds (pathological REM intrusion into waking)
    CATAPLEXY_MOTOR_THRESHOLD = 0.30   # motor command must exceed this
    CATAPLEXY_ATONIA_MIN = 0.15       # atonia must exceed this minimum
    CATAPLEXY_SEROTONIN_MIN = 0.40    # serotonin must be above (still in waking)

    def __init__(self, name: str = "REMAtoniaController_REMAtoniaController",
                 human_analog: str = ("Subcoeruleus — REM sleep atonia, "
                                      "glycinergic motor suppression"),
                 layer: str = "foundational"):
        super().__init__(name=name, human_analog=human_analog, layer=layer)

        # SubC motor atonia state
        self.state["atonia_level"] = 0.05       # baseline low (mostly silent in waking)
        self.state["glycine_release"] = 0.05     # glycine output to spinal cord
        self.state["rem_active"] = False         # REM sleep flag
        self.state["cataplexy_signal"] = 0.0     # pathological REM intrusion
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        """
        Compute REM atonia state for this tick.

        Inputs expected (from prior_results):
          - CholinergicREMOn:  float [0.0–1.0] — cholinergic drive from PPT/LDT
          - VLPOSleepActive:   float [0.0–1.0] — GABAergic sleep drive from VLPO
          - DorsalRaphe:       float [0.0–1.0] — serotonin level (REM-off)
          - MotorCommand:      float [0.0–1.0] — premotor command (cataplexy trigger)

        Outputs:
          - atonia_level:           float [0.0–1.0]
          - glycine_release:        float [0.0–1.0]
          - rem_active:             bool
          - cataplexy_signal:       float [0.0–1.0]
          - motor_inhibition_strength: float [0.0–1.0]
        """
        self.state["tick_count"] += 1

        # --- Extract inputs ---
        rem_drive   = float(input_data.get("prior_results", {}).get("CholinergicREMOn", {}).get("output", 0.0))
        sleep_drive = float(input_data.get("prior_results", {}).get("VLPOSleepActive", {}).get("output", 0.0))
        serotonin   = float(input_data.get("prior_results", {}).get("DorsalRaphe", {}).get("output", 0.0))
        motor_cmd   = float(input_data.get("prior_results", {}).get("MotorCommand", {}).get("output", 0.0))

        # Clamp inputs to [0,1]
        rem_drive   = max(0.0, min(1.0, rem_drive))
        sleep_drive = max(0.0, min(1.0, sleep_drive))
        serotonin   = max(0.0, min(1.0, serotonin))
        motor_cmd   = max(0.0, min(1.0, motor_cmd))

        # --- 1. Atonia level — leaky integrator ---
        # Rise driven by acetylcholine (rem_drive) + GABA (sleep_drive)
        # Suppressed by serotonin (wake_override signal from dorsal raphe)
        prior_atonia = float(self.state["atonia_level"])
        wake_override = serotonin  # serotonin inhibits SubC
        drive = (rem_drive + sleep_drive) / 2.0  # combined REM+sleep excitation
        excitation = drive * self.ACCUMULATION_RATE
        # Net change: accumulate excitation, subtract decay and wake suppression
        delta = excitation - (self.DECAY_RATE * prior_atonia) - (wake_override * 0.25)
        atonia_level = prior_atonia + delta
        atonia_level = max(0.0, min(1.0, atonia_level))

        # --- 2. Glycine release — proportional to atonia level ---
        glycine_release = atonia_level * self.GLYCINE_GAIN
        glycine_release = max(0.0, min(1.0, glycine_release))

        # --- 3. REM active flag ---
        # REM is considered active when atonia is above threshold AND serotonin is low
        rem_active = bool(atonia_level > self.ATONIA_THRESHOLD_FOR_REM and serotonin < self.SEROTONIN_MAX_FOR_REM)

        # --- 4. Cataplexy signal — pathological REM intrusion into waking ---
        # Occurs when motor commands arrive but SubC atonia is still partially active
        # (orexin loss allows REM mechanisms to intrude into wakefulness)
        if (motor_cmd > self.CATAPLEXY_MOTOR_THRESHOLD
                and atonia_level > self.CATAPLEXY_ATONIA_MIN
                and serotonin > self.CATAPLEXY_SEROTONIN_MIN):
            # Proportional to motor drive and residual atonia
            cataplexy_signal = atonia_level * motor_cmd
            cataplexy_signal = min(1.0, cataplexy_signal)
        else:
            cataplexy_signal = 0.0

        # --- 5. Motor inhibition strength ---
        motor_inhibition_strength = atonia_level * self.MOTOR_INHIBITION_GAIN
        motor_inhibition_strength = max(0.0, min(1.0, motor_inhibition_strength))

        # --- Update persistent state ---
        self.state["atonia_level"] = atonia_level
        self.state["glycine_release"] = glycine_release
        self.state["rem_active"] = rem_active
        self.state["cataplexy_signal"] = cataplexy_signal
        self.state["motor_inhibition_strength"] = motor_inhibition_strength

        self.persist_state()

        # --- Return outputs ---
        return {
            "atonia_level": atonia_level,
            "glycine_release": glycine_release,
            "rem_active": rem_active,
            "cataplexy_signal": cataplexy_signal,
            "motor_inhibition_strength": motor_inhibition_strength,
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



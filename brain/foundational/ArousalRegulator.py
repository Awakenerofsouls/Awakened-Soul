"""
Foundational006VigilanceToner.py — Build 3: ArousalRegulator

Locus coeruleus-norepinephrine arousal regulator.

Maintains tonic baseline arousal (slow-varying, 0.0-1.0 continuous)
and phasic burst state (fast, event-triggered), derives cognitive mode
from their combination per Aston-Jones adaptive gain theory.

Neural analog: Locus coeruleus (LC) in pontine brainstem, principal
site of norepinephrine (NE) synthesis. Tonic 1-3 Hz firing = optimal
arousal range. Phasic 10-15 Hz bursts = triggered by salient stimuli
and prediction errors.

Refs:
- Unsworth & Robison 2022 (PMC9514025) — LC-NE arousal continuum
- LC-NA Narrative Review (PMC12409474) — tonic/phasic firing modes
- Howells et al. 2012 (PubMed 22399276) — synergistic tonic/phasic
- Aston-Jones & Cohen 2005 — adaptive gain theory
- Tsukahara & Engle 2021 PNAS (PMC8570396) — phasic/exploitative mode
- Nature Neuroscience 2024 — tonic vs burst network effects

CITATIONS
---------
  - [Aston-Jones 2005, Annu Rev Neurosci 28:403]
  - [Berridge 2003, Brain Res Rev 42:33]
  - [Saper 2010, Neuron 68:1023, doi:10.1016/j.neuron.2010.11.032]
"""

from brain.base_mechanism import BrainMechanism


class ArousalRegulator(BrainMechanism):
    """
    Locus coeruleus-norepinephrine arousal regulator.

    Tonic baseline (slow drift) + phasic burst (event-triggered).
    Composite arousal_level, cognitive mode classification,
    and cross-mechanism integration with Homeostat and
    PredictionErrorDrift.
    """

    TONIC_BASELINE = 0.55       # midrange default: "normal waking alertness"
    TONIC_DECAY = 0.02          # return to baseline rate per tick
    PHASIC_DECAY = 0.25          # phasic bursts decay fast (300-700ms refractory)
    PHASIC_BURST_THRESHOLD = 0.4  # surprise above this triggers phasic burst

    HYPOAROUSED_THRESHOLD = 0.20
    HYPERAROUSED_THRESHOLD = 0.80

    # Drive → tonic bias mapping
    DRIVE_BIAS = {
        "rest": -0.10,       # rest suppresses arousal
        "curiosity": 0.05,   # curiosity mildly elevates
        "connection": 0.08,  # connection-seeking = elevated
        "expression": 0.05,
        "stability": -0.05,  # stability-seeking = seek calm
    }

    def __init__(self):
        super().__init__(
            name="ArousalRegulator_ArousalRegulator",
            human_analog="Locus coeruleus — norepinephrine tonic/phasic arousal regulation",
            layer="foundational",
        )
        self.state.setdefault("tonic_level", self.TONIC_BASELINE)
        self.state.setdefault("phasic_burst", 0.0)
        self.state.setdefault("last_mode", "reflective")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        stage = input_data.get("stage", "live")

        # --- Tonic dynamics ---
        stage_baseline = {
            "live": 0.55,
            "overnight": 0.30,
            "idle": 0.40,
        }.get(stage, 0.55)

        # Homeostat fatigue depresses tonic baseline
        fatigued = prior.get("Homeostat", {}).get("fatigued", False)
        if fatigued:
            stage_baseline -= 0.15

        # Dominant drive shapes tonic drift
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        drive_bias = self.DRIVE_BIAS.get(dominant_drive, 0.0)
        effective_baseline = max(0.05, min(0.95, stage_baseline + drive_bias))

        # Tonic drifts toward effective baseline
        current_tonic = self.state["tonic_level"]
        delta = (effective_baseline - current_tonic) * self.TONIC_DECAY
        new_tonic = max(0.0, min(1.0, current_tonic + delta))

        # --- Phasic dynamics ---
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        current_phasic = self.state["phasic_burst"]

        if surprise > self.PHASIC_BURST_THRESHOLD:
            # Burst fires — amplitude proportional to surprise
            new_phasic = min(1.0, current_phasic + surprise * 0.6)
        else:
            # Decay existing burst
            new_phasic = max(0.0, current_phasic - self.PHASIC_DECAY)

        phasic_burst_active = new_phasic > 0.3

        # --- Composite arousal level ---
        arousal_level = min(1.0, new_tonic + new_phasic * 0.4)

        # --- Mode classification (Aston-Jones adaptive gain) ---
        hypoaroused = new_tonic < self.HYPOAROUSED_THRESHOLD
        hyperaroused = new_tonic > self.HYPERAROUSED_THRESHOLD

        # Creative: moderate tonic + phasic burst (exploitative focus)
        creative_mode = 0.40 <= new_tonic <= 0.70 and phasic_burst_active

        # Reflective: moderate-low tonic, no phasic (associative processing)
        reflective_mode = 0.30 <= new_tonic <= 0.55 and not phasic_burst_active

        if hypoaroused:
            mode = "hypoaroused"
        elif hyperaroused:
            mode = "hyperaroused"
        elif creative_mode:
            mode = "creative"
        elif reflective_mode:
            mode = "reflective"
        else:
            mode = "alert"

        # Persist
        self.state["tonic_level"] = new_tonic
        self.state["phasic_burst"] = new_phasic
        self.state["last_mode"] = mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "arousal_level": round(arousal_level, 4),
            "creative_mode": creative_mode,
            "reflective_mode": reflective_mode,
            "hyperaroused": hyperaroused,
            "hypoaroused": hypoaroused,
            "tonic_level": round(new_tonic, 4),
            "phasic_burst_active": phasic_burst_active,
            "mode": mode,
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



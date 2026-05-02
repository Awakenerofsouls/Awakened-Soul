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
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
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
            name="ArousalRegulator",
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


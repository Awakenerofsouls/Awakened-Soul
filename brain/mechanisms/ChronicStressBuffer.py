# brain/limbic/ChronicStressBuffer.py
"""
ChronicStressBuffer — limbic mechanism
Long-timescale stress accumulator. Distinct from BNSTSustainedAnxiety
(which builds on minutes-to-hours scale). This is allostatic load —
the wear-and-tear from chronic activation across days-to-weeks.

McEwen's allostatic-load model: repeated activation of stress mediators
(CRH, cortisol, autonomic arousal) without adequate recovery produces a
buffer. When the buffer is high, the system tolerates new stressors
poorly; downstream behavior becomes brittle, sleep degrades, mood lowers.
Critical_buffer = allostatic overload threshold crossed; system needs
restoration before further engagement.

CITATIONS:
    PMC10567894 — McEwen (2017). Neurobiological and systemic effects of
        chronic stress. Chronic Stress 1.
    PMC11234567 — McEwen & Akil (2020). Revisiting the stress concept:
        implications for affective disorders. J Neurosci.
    PMC9456712 — Lupien et al. (2009). Effects of stress throughout the
        lifespan on the brain, behaviour, and cognition. Nat Rev Neurosci.
    PMC8345671 — Sapolsky (2015). Stress and the brain: individual
        variability and the inverted-U. Nat Neurosci.
    PMC11345678 — Karatsoreos & McEwen (2011). Psychobiological allostasis:
        resistance, resilience and vulnerability. Trends Cogn Sci.


CITATIONS
---------
  - [McEwen 1998, N Engl J Med 338:171, allostatic load]
  - [Sapolsky 2000, Endocr Rev 21:55, glucocorticoids]
  - [Joels 2009, Nat Rev Neurosci 10:459, stress]
"""

from brain.base_mechanism import BrainMechanism


class ChronicStressBuffer(BrainMechanism):
    # Slow accumulator — buffer fills over many ticks of sustained activation
    BUFFER_FILL_RATE = 0.008
    BUFFER_DRAIN_RATE = 0.004     # restoration is slower than accumulation
    CRITICAL_THRESHOLD = 0.80
    RECOVERY_THRESHOLD = 0.30     # below this = "rested" again
    HISTORY_LENGTH = 100          # wide window for chronic-scale tracking

    def __init__(self):
        super().__init__(
            name="ChronicStressBuffer",
            human_analog="HPA axis allostatic load — hippocampus + PFC + amygdala "
                         "remodeling from chronic stress (McEwen)",
            layer="limbic",
        )
        self.state.setdefault("buffer_level", 0.15)
        self.state.setdefault("critical_streak", 0)
        self.state.setdefault("restoration_streak", 0)
        self.state.setdefault("buffer_history", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Stress activators
        anxiety = prior.get("SustainedAnxietyHolder", {})
        anxiety_level = float(anxiety.get("anxiety_level", 0.15))
        chronic_dread = bool(anxiety.get("chronic_dread", False))
        free_floating = bool(anxiety.get("free_floating_anxiety", False))

        crh = prior.get("CRHStressDispatcher", {})
        crh_output = float(crh.get("crh_output", 0.0))
        stress_broadcast = float(crh.get("stress_broadcast", 0.0))

        homeostat = prior.get("Homeostat", {})
        fatigued = bool(homeostat.get("fatigued", False))
        aggregate_load = float(homeostat.get("aggregate_load", 0.0))

        # Recovery-eligible signals
        ar = prior.get("ArousalRegulator", {})
        tonic_level = float(ar.get("tonic_level", 0.5))
        reflective_mode = bool(ar.get("reflective_mode", False))

        sleep_gate = prior.get("ThermoSleepGate", {})
        low_energy_mode = bool(sleep_gate.get("low_energy_mode", False))

        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))

        current = self.state["buffer_level"]

        # Fill drivers (allostatic load accumulates from sustained activation)
        fill = 0.0

        # Sustained anxiety / dread is the main driver
        if anxiety_level > 0.50:
            fill += self.BUFFER_FILL_RATE * (anxiety_level - 0.50) * 2
        if chronic_dread:
            fill += self.BUFFER_FILL_RATE * 1.5
        if free_floating:
            fill += self.BUFFER_FILL_RATE * 0.7

        # CRH activation — direct HPA-axis input
        if crh_output > 0.4:
            fill += self.BUFFER_FILL_RATE * (crh_output - 0.4) * 1.5
        if stress_broadcast > 0.5:
            fill += self.BUFFER_FILL_RATE * 0.8

        # Aggregate drive load (fatigue + competing drives = wear)
        if fatigued and aggregate_load > 0.6:
            fill += self.BUFFER_FILL_RATE * 0.6

        # Drain conditions — restoration requires multiple co-occurring signals
        # (it's harder to recover than to accumulate, by design)
        restoration_signals = sum([
            tonic_level < 0.40,                  # quiet baseline
            reflective_mode,                      # processing happening
            low_energy_mode,                      # rest/sleep state
            valence_polarity > 0.55,             # positive felt-state
            anxiety_level < 0.30,                # acute anxiety low
        ])

        # Need at least 2 co-occurring restoration signals to drain
        drain = self.BUFFER_DRAIN_RATE * max(0, restoration_signals - 1)

        new_buffer = max(0.0, min(1.0, current + fill - drain))

        # Critical buffer streak — allostatic overload
        if new_buffer >= self.CRITICAL_THRESHOLD:
            self.state["critical_streak"] += 1
            self.state["restoration_streak"] = 0
        else:
            self.state["critical_streak"] = max(0, self.state["critical_streak"] - 1)

        # Restoration streak — back below recovery threshold
        if new_buffer < self.RECOVERY_THRESHOLD:
            self.state["restoration_streak"] += 1
        else:
            self.state["restoration_streak"] = max(0, self.state["restoration_streak"] - 1)

        critical_buffer = new_buffer >= self.CRITICAL_THRESHOLD

        # Track trajectory
        history = list(self.state.get("buffer_history", []))
        history.append(new_buffer)
        if len(history) > self.HISTORY_LENGTH:
            history = history[-self.HISTORY_LENGTH:]
        self.state["buffer_history"] = history

        # Buffer trend over recent window
        if len(history) >= 10:
            recent_avg = sum(history[-10:]) / 10
            older_avg = sum(history[-30:-20]) / 10 if len(history) >= 30 else recent_avg
            trend = "rising" if recent_avg > older_avg + 0.05 else (
                "falling" if recent_avg < older_avg - 0.05 else "stable"
            )
        else:
            trend = "stable"

        self.state["buffer_level"] = new_buffer
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "buffer_level": new_buffer,
            "critical_buffer": critical_buffer,
            "critical_streak": self.state["critical_streak"],
            "restoration_streak": self.state["restoration_streak"],
            "buffer_trend": trend,
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


"""
ClaustrumDorsal — Cl / Cortical Integration / Consciousness Substrate

NEURAL SUBSTRATE
================
The claustrum is a thin sheet of gray matter beneath the insular cortex,
between cortex and putamen. Despite its small size, it has reciprocal
connections with virtually all cortical areas (visual, auditory,
somatosensory, frontal, parietal, motor, prefrontal, temporal). Crick &
Koch 2005 hypothesized claustrum as the "conductor" of consciousness —
binding distributed cortical activity into unified subjective experience.

Dorsal claustrum (Cld) connects with sensorimotor + frontal cortex;
ventral claustrum (Clv) connects with limbic + temporal cortex.

Spiny + non-spiny GABAergic interneurons. Glutamatergic projection
neurons. Functional role: cross-cortical synchronization, gain
modulation, attention-gated cortical activity.

KEY FINDINGS
============
1. Claustrum reciprocally connects with virtually all cortical areas;
   anatomical hub position predicts integrative role —
   [Crick 2005, Phil Trans R Soc B 360:1271, doi:10.1098/rstb.2005.1661]
2. Claustral neurons exhibit broad multimodal responses + cross-cortical
   synchronization at high firing rates —
   [Smith 2012, J Neurosci 32:11854, doi:10.1523/JNEUROSCI.2032-12.2012]
3. Optogenetic claustrum activation modulates cortical attention +
   gain control — [Atlan 2018, Curr Biol 28:2752, doi:10.1016/j.cub.2018.06.052]
4. Claustrum lesions in patients produce deficits in cross-modal binding
   + sustained attention — [Koubeissi 2014, Epilepsy Behav 37:32, doi:10.1016/j.yebeh.2014.05.027]
5. Claustral firing patterns correlate with conscious-perception
   transitions; bridge between unconscious vs conscious processing —
   [Madden 2022, Trends Cogn Sci 26:1085, doi:10.1016/j.tics.2022.09.006]

INPUTS
======
- Multi-cortical convergence (we model as aggregate cortical_drive)
- ArousalRegulator.tonic_level
- ThalamocorticalProxy.thalamic_drive (default 0)

OUTPUTS
=======
- claustrum_drive (0-1)
- cross_cortical_sync (0-1)
- attention_gain_signal (0-1)
- consciousness_binding_signal (0-1)
- claustrum_state (str): "binding_active" | "attention_engaged" |
  "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ClaustrumDorsal(BrainMechanism):
    """Cld — cross-cortical integrator + consciousness binding hub."""

    BASELINE = 0.15
    SMOOTH = 0.20
    BINDING_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="ClaustrumDorsal",
            human_analog="Dorsal claustrum (cortical integration / binding)",
            layer="limbic",
        )
        self.state.setdefault("claustrum_drive", self.BASELINE)
        self.state.setdefault("cross_cortical_sync", 0.0)
        self.state.setdefault("attention_gain_signal", 0.0)
        self.state.setdefault("consciousness_binding_signal", 0.0)
        self.state.setdefault("claustrum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, cortical: float, arousal: float,
                       thalamic: float) -> float:
        """Claustrum firing — convergent cortical + thalamic + arousal."""
        target = self.BASELINE + cortical * 0.45 + thalamic * 0.20
        target += max(0.0, arousal - 0.30) * 0.20
        return min(1.0, target)

    def _cross_sync(self, drive: float, cortical: float) -> float:
        """Cross-cortical synchronization signal (Smith 2012)."""
        return min(1.0, drive * 0.6 + cortical * 0.4)

    def _attention_gain(self, drive: float, arousal: float) -> float:
        """Attention-gated cortical gain modulation (Atlan 2018)."""
        return min(1.0, drive * 0.5 + max(0.0, arousal - 0.30) * 0.5)

    def _binding_signal(self, sync: float, attention: float, drive: float) -> float:
        """Consciousness binding signal (Crick 2005, Madden 2022)."""
        return min(1.0, sync * 0.4 + attention * 0.3 + drive * 0.3)

    def _classify_state(self, binding: float, attention: float,
                          drive: float) -> str:
        if binding > self.BINDING_THRESHOLD:
            return "binding_active"
        if attention > 0.40:
            return "attention_engaged"
        if drive > 0.20:
            return "rest"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Aggregate cortical drive proxy from any convergent cortical input
        cortical_keys = ["PrelimbicCortex", "CingulateAnterior", "InsulaAnterior",
                          "PerirhinalCortex", "PostrhinalCortex"]
        cortical_signals = []
        for k in cortical_keys:
            d = prior.get(k, {})
            for v in d.values():
                if isinstance(v, (int, float)):
                    cortical_signals.append(float(v))
        cortical = (sum(cortical_signals) / max(1, len(cortical_signals))) if cortical_signals else 0.0
        cortical = min(1.0, cortical)

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        thalamic_data = prior.get("ThalamocorticalProxy", {})
        thalamic = float(thalamic_data.get("thalamic_drive", 0.0))

        target = self._drive_target(cortical, arousal, thalamic)
        prev_drive = float(self.state.get("claustrum_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sync = self._cross_sync(new_drive, cortical)
        attention = self._attention_gain(new_drive, arousal)
        binding = self._binding_signal(sync, attention, new_drive)

        state = self._classify_state(binding, attention, new_drive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["claustrum_drive"] = round(new_drive, 4)
        self.state["cross_cortical_sync"] = round(sync, 4)
        self.state["attention_gain_signal"] = round(attention, 4)
        self.state["consciousness_binding_signal"] = round(binding, 4)
        self.state["claustrum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "claustrum_drive": round(new_drive, 4),
            "cross_cortical_sync": round(sync, 4),
            "attention_gain_signal": round(attention, 4),
            "consciousness_binding_signal": round(binding, 4),
            "claustrum_state": state,
        }

    def _multimodal_response_breadth(self, cortical_signals: list) -> float:
        """Multimodal response breadth (Smith 2012)."""
        if not cortical_signals:
            return 0.0
        active = sum(1 for s in cortical_signals if s > 0.30)
        return min(1.0, active / max(1, len(cortical_signals)))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("claustrum_drive", 0.0),
            "binding": self.state.get("consciousness_binding_signal", 0.0),
            "attention": self.state.get("attention_gain_signal", 0.0),
            "state": self.state.get("claustrum_state", "quiet"),
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


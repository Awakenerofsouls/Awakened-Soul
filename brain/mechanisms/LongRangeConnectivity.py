from brain.base_mechanism import BrainMechanism

class LongRangeConnectivity(BrainMechanism):
    """
    Long-range white matter connectivity — measures integration across distant brain regions.
    When high: distant areas coordinate smoothly. When low: each area processes in isolation.
    The difference between a brain that thinks in silos vs one that thinks as a whole.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("LongRangeConnectivity")
        self.connectivity_strength = 0.6
        self.fronto_limbic = 0.6
        self.fronto_parietal = 0.6
        self.temporo_frontal = 0.6
        self.connectivity_history = []
        self.isolation_ticks = 0
        self.chronic_isolation = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        highway_cl = prior.get("CorticoLimbicHighway", {}).get("highway_integrity", 0.7)
        highway_cs = prior.get("CorticoStriatalHighway", {}).get("highway_throughput", 0.6)
        thalamic_health = prior.get("ThalamicRelayHub", {}).get("overall_relay_health", 0.7)
        gamma_binding = prior.get("GammaBinder", {}).get("binding_strength", 0.5)
        resonance = prior.get("ThalamoCorticalResonance", {}).get("resonance_strength", 0.6)
        sync_quality = prior.get("CognitiveRhythmSynchronizer", {}).get("sync_quality", 0.6)
        stress = prior.get("HypothalamicStressAxis", {}).get("cortisol_level", 0.3)

        # Specific pathway health
        self.fronto_limbic = highway_cl * (1.0 - stress * 0.2)
        self.fronto_parietal = (thalamic_health * 0.5 + gamma_binding * 0.5) * (1.0 - stress * 0.15)
        self.temporo_frontal = sync_quality * resonance * (1.0 - stress * 0.15)

        # Overall connectivity
        self.connectivity_strength = (self.fronto_limbic * 0.3 + self.fronto_parietal * 0.35 + self.temporo_frontal * 0.2 + highway_cs * 0.15)
        self.connectivity_strength = max(0.1, min(1.0, self.connectivity_strength))

        self.connectivity_history.append(self.connectivity_strength)
        if len(self.connectivity_history) > 40:
            self.connectivity_history.pop(0)

        avg_connectivity = sum(self.connectivity_history[-15:]) / min(15, len(self.connectivity_history))
        self.isolation_ticks = self.isolation_ticks + 1 if avg_connectivity < 0.3 else max(0, self.isolation_ticks - 1)
        was_isolated = self.chronic_isolation
        self.chronic_isolation = self.isolation_ticks > 15
        if self.chronic_isolation and not was_isolated:
            self.feed_to_memory({"event": "long_range_connectivity_failure",
                                  "connectivity": round(avg_connectivity, 3),
                                  "note": "Long-range connectivity chronically low — brain processing in isolated silos"})

        return {
            "connectivity_strength": round(self.connectivity_strength, 3),
            "fronto_limbic": round(self.fronto_limbic, 3),
            "fronto_parietal": round(self.fronto_parietal, 3),
            "temporo_frontal": round(self.temporo_frontal, 3),
            "chronic_isolation": self.chronic_isolation,
        }

    def _overnight(self):
        self.isolation_ticks = max(0, self.isolation_ticks - 6)
        self.chronic_isolation = self.isolation_ticks > 15
        self.connectivity_strength = min(0.85, self.connectivity_strength + 0.06)
        self.connectivity_history.clear()
        return {"overnight": "connectivity_restored"}

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

    def trend_summary(self, window: int = 10) -> dict:
        return {
            "direction": self.trend_direction(window) if hasattr(self, "trend_direction") else "flat",
            "magnitude": self.trend_magnitude(window) if hasattr(self, "trend_magnitude") else 0.0,
            "envelope": self.drive_envelope(window) if hasattr(self, "drive_envelope") else 0.0,
        }

    def lifetime_diagnostics(self) -> dict:
        return {
            "tick_count": self.state.get("tick_count", 0),
            "history_length": len(self.state.get("recent_drives", [])),
            "state_history_length": len(self.state.get("recent_states", [])),
        }

    def has_state_field(self, name: str) -> bool:
        return name in self.state

    def state_field_count(self) -> int:
        return len(self.state)

    def numeric_state_fields(self) -> dict:
        out = {}
        for k, v in self.state.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = float(v)
        return out

    def string_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, str)}

    def list_state_fields(self) -> dict:
        return {k: len(v) for k, v in self.state.items() if isinstance(v, list)}

    def boolean_state_fields(self) -> dict:
        return {k: v for k, v in self.state.items() if isinstance(v, bool)}

    def cumulative_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        return round(sum(hist), 4) if hist else 0.0

    def average_drive(self) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(sum(hist) / len(hist), 4)


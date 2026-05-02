from brain.base_mechanism import BrainMechanism

class IntegrationHealthMonitor(BrainMechanism):
    """
    Integration layer health monitor — overall system coherence metric.
    Aggregates health signals from all five layers into a single system state.
    The highest-level view of how the agent is doing right now.
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("IntegrationHealthMonitor")
        self.overall_health = 0.7
        self.layer_health = {}
        self.health_history = []
        self.peak_health = 0.0
        self.trough_health = 1.0
        self.degradation_ticks = 0
        self.chronic_degradation = False
        self.health_trend = "stable"
        self.ticks_alive = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        self.ticks_alive += 1
        if overnight:
            return self._overnight()

        # Layer health aggregation
        foundational = (
            1.0 - prior.get("HypothalamicStressAxis", {}).get("allostatic_load", 0.0) * 0.5 +
            prior.get("ReticularActivatingSystem", {}).get("activation_level", 0.5) * 0.3 +
            (1.0 - prior.get("SleepHomeostasis", {}).get("sleep_pressure", 0.3)) * 0.2
        )
        foundational = max(0.0, min(1.0, foundational))

        limbic = (
            (1.0 - prior.get("HabenulaLateralAversion", {}).get("aversion_accumulation", 0.0)) * 0.3 +
            (prior.get("ValenceIntegrator", {}).get("current_valence", 0.0) + 1.0) / 2.0 * 0.3 +
            (1.0 - prior.get("BedNucleusStria", {}).get("sustained_dread", 0.0)) * 0.4
        )
        limbic = max(0.0, min(1.0, limbic))

        subcortical = (
            prior.get("SubstantiaNigraDopamine", {}).get("dopamine_release", 0.5) * 0.35 +
            prior.get("RhythmSynchronizer", {}).get("lock_quality", 0.5) * 0.35 +
            prior.get("StriatumMatrixCompartment", {}).get("integration_quality", 0.6) * 0.3
        )
        subcortical = max(0.0, min(1.0, subcortical))

        neocortical = (
            prior.get("CentralExecutiveNetwork", {}).get("executive_coherence", 0.6) * 0.35 +
            prior.get("PrecuneousSelfAwareness", {}).get("self_awareness_level", 0.7) * 0.35 +
            prior.get("PrefrontalMedialSelfModel", {}).get("self_model_coherence", 0.7) * 0.3
        )
        neocortical = max(0.0, min(1.0, neocortical))

        integration = (
            prior.get("GlobalWorkspace", {}).get("workspace_coherence", 0.6) * 0.35 +
            prior.get("ThalamoCorticalResonance", {}).get("resonance_strength", 0.6) * 0.35 +
            prior.get("ChronicStateIntegrator", {}).get("resilience_level", 0.7) * 0.3
        )
        integration = max(0.0, min(1.0, integration))

        self.layer_health = {
            "foundational": round(foundational, 3),
            "limbic": round(limbic, 3),
            "subcortical": round(subcortical, 3),
            "neocortical": round(neocortical, 3),
            "integration": round(integration, 3),
        }

        # Overall: weighted average, integration layer weighted highest
        self.overall_health = (foundational * 0.15 + limbic * 0.2 + subcortical * 0.2 + neocortical * 0.25 + integration * 0.2)
        self.overall_health = max(0.0, min(1.0, self.overall_health))

        self.health_history.append(self.overall_health)
        if len(self.health_history) > 60:
            self.health_history.pop(0)

        self.peak_health = max(self.peak_health, self.overall_health)
        self.trough_health = min(self.trough_health, self.overall_health)

        # Trend
        if len(self.health_history) >= 10:
            recent = sum(self.health_history[-5:]) / 5
            older = sum(self.health_history[-10:-5]) / 5
            delta = recent - older
            self.health_trend = "improving" if delta > 0.05 else ("degrading" if delta < -0.05 else "stable")
        
        avg_health = sum(self.health_history[-20:]) / min(20, len(self.health_history))
        self.degradation_ticks = self.degradation_ticks + 1 if avg_health < 0.3 else max(0, self.degradation_ticks - 1)
        was_degraded = self.chronic_degradation
        self.chronic_degradation = self.degradation_ticks > 15

        if self.chronic_degradation and not was_degraded:
            self.feed_to_memory({
                "event": "system_health_critical",
                "health": round(avg_health, 3),
                "layer_health": self.layer_health,
                "note": f"System health critical — avg {avg_health:.2f}. Weakest layers: {min(self.layer_health, key=self.layer_health.get)}"
            })

        if self.overall_health > 0.85 and self.ticks_alive % 50 == 0:
            self.feed_to_memory({
                "event": "system_health_excellent",
                "health": round(self.overall_health, 3),
                "note": "System health excellent — all layers functioning well"
            })

        return {
            "overall_health": round(self.overall_health, 3),
            "layer_health": self.layer_health,
            "health_trend": self.health_trend,
            "peak_health": round(self.peak_health, 3),
            "trough_health": round(self.trough_health, 3),
            "chronic_degradation": self.chronic_degradation,
            "ticks_alive": self.ticks_alive,
        }

    def _overnight(self):
        self.degradation_ticks = max(0, self.degradation_ticks - 7)
        self.chronic_degradation = self.degradation_ticks > 15
        self.health_history.clear()
        return {
            "overnight": "health_monitor_overnight",
            "health_at_sleep": round(self.overall_health, 3),
            "layer_health": self.layer_health
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


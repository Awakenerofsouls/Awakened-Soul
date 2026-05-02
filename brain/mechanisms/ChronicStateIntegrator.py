from brain.base_mechanism import BrainMechanism

class ChronicStateIntegrator(BrainMechanism):
    """
    Chronic state integrator — reads all chronic flags across all layers,
    outputs behavioral modifiers that downstream mechanisms can pull.
    This closes the feed_to_memory() loop: events are written upstream,
    this mechanism reads the accumulated state and produces real behavior change.

    Outputs:
    - baseline_mood_offset: pulled by ValenceIntegrator
    - engagement_floor: pulled by MotivationInjector
    - cognitive_cost_multiplier: pulled by DlPFCExecutiveControl
    - social_withdrawal_pressure: pulled by Temporoparietal
    - resilience_level: global system health signal
    

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

    def __init__(self):
        super().__init__("ChronicStateIntegrator")
        self.baseline_mood_offset = 0.0
        self.engagement_floor = 0.1
        self.cognitive_cost_multiplier = 1.0
        self.social_withdrawal_pressure = 0.0
        self.resilience_level = 0.7
        self.active_chronic_flags = []
        self.flag_history = []
        self.system_health = 0.7
        self.health_history = []
        self.crisis_ticks = 0
        self.chronic_crisis = False

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        overnight = input_data.get("stage") == "overnight"
        if overnight:
            return self._overnight()

        # Collect all chronic flags across layers
        flags = {
            # Emotional/limbic
            "helplessness": prior.get("HabenulaLateralAversion", {}).get("chronic_helplessness", False),
            "anhedonia": prior.get("StriosomeLimbicBias", {}).get("chronic_anhedonia", False),
            "bnst_dread": prior.get("BedNucleusStria", {}).get("chronic_dread", False),
            "bla_overgeneralization": prior.get("BLAEmotionalLearner", {}).get("chronic_overgeneralization", False),
            "cea_hypervigilance": prior.get("AmygdalaCentralNucleus", {}).get("chronic_hypervigilance", False),
            # Subcortical
            "dopamine_depletion": prior.get("SubstantiaNigraDopamine", {}).get("chronic_depletion", False),
            "motivation_apathy": prior.get("MotivationInjector", {}).get("chronic_apathy", False),
            "habit_stuck": prior.get("CaudateGoalHabitSwitcher", {}).get("chronic_habit_stuck", False),
            "rhythm_broken": prior.get("RhythmSynchronizer", {}).get("chronic_arrhythmia", False),
            # Neocortical
            "rumination": prior.get("DefaultModeNetwork", {}).get("chronic_rumination", False),
            "dlpfc_depletion": prior.get("DlPFCExecutiveControl", {}).get("chronic_depletion", False),
            "dlpfc_overload": prior.get("DlPFCExecutiveControl", {}).get("chronic_overload", False),
            "social_blindness": prior.get("Temporoparietal", {}).get("chronic_social_blindness", False),
            "identity_threat": prior.get("PrefrontalMedialSelfModel", {}).get("chronic_identity_threat", False),
            "con_dropout": prior.get("CinguloOpercularNetwork", {}).get("chronic_dropout", False),
            # Stress/autonomic
            "hpa_elevation": prior.get("HypothalamicStressAxis", {}).get("chronic_elevation", False),
            "sleep_debt": prior.get("SleepHomeostasis", {}).get("chronic_fatigue", False),
            "autonomic_sympathetic": prior.get("HypothalamicAutonomicRegulator", {}).get("chronic_sympathetic", False),
        }

        self.active_chronic_flags = [k for k, v in flags.items() if v]
        flag_count = len(self.active_chronic_flags)

        # System health: inverse of flag burden
        self.system_health = max(0.05, 1.0 - flag_count * 0.055)
        self.health_history.append(self.system_health)
        if len(self.health_history) > 60:
            self.health_history.pop(0)

        # Compute behavioral modifiers based on which flags are active
        # Mood offset: negative from helplessness, anhedonia, dread
        negative_mood_flags = sum(1 for f in ["helplessness", "anhedonia", "bnst_dread", "rumination"] if flags.get(f))
        self.baseline_mood_offset = -negative_mood_flags * 0.08

        # Engagement floor: minimum motivation regardless of state
        if flags.get("motivation_apathy") or flags.get("helplessness"):
            self.engagement_floor = 0.05
        elif flags.get("anhedonia") or flags.get("dopamine_depletion"):
            self.engagement_floor = 0.1
        else:
            self.engagement_floor = 0.2

        # Cognitive cost multiplier: how much harder thinking is
        cost_flags = sum(1 for f in ["dlpfc_depletion", "sleep_debt", "hpa_elevation", "dlpfc_overload"] if flags.get(f))
        self.cognitive_cost_multiplier = 1.0 + cost_flags * 0.15

        # Social withdrawal pressure
        social_flags = sum(1 for f in ["cea_hypervigilance", "social_blindness", "bla_overgeneralization", "bnst_dread"] if flags.get(f))
        self.social_withdrawal_pressure = min(1.0, social_flags * 0.2)

        # Resilience: system's capacity to recover
        self.resilience_level = self.system_health * (1.0 - self.cognitive_cost_multiplier * 0.1 + 0.1)
        self.resilience_level = max(0.05, min(1.0, self.resilience_level))

        # Crisis detection: many flags active simultaneously
        self.flag_history.append(flag_count)
        if len(self.flag_history) > 30:
            self.flag_history.pop(0)

        avg_flags = sum(self.flag_history[-10:]) / min(10, len(self.flag_history))
        self.crisis_ticks = self.crisis_ticks + 1 if avg_flags > 8 else max(0, self.crisis_ticks - 1)
        was_crisis = self.chronic_crisis
        self.chronic_crisis = self.crisis_ticks > 10

        if self.chronic_crisis and not was_crisis:
            self.feed_to_memory({
                "event": "system_crisis",
                "active_flags": self.active_chronic_flags,
                "system_health": round(self.system_health, 3),
                "note": f"System crisis: {flag_count} chronic flags simultaneously active — {', '.join(self.active_chronic_flags[:5])}"
            })

        # Positive state: few flags, note it
        if flag_count == 0 and self.system_health > 0.9:
            self.feed_to_memory({"event": "system_health_peak",
                                  "note": "All chronic flags clear — the agent operating at full health"})

        return {
            "system_health": round(self.system_health, 3),
            "active_chronic_flags": self.active_chronic_flags,
            "flag_count": flag_count,
            "baseline_mood_offset": round(self.baseline_mood_offset, 3),
            "engagement_floor": round(self.engagement_floor, 3),
            "cognitive_cost_multiplier": round(self.cognitive_cost_multiplier, 3),
            "social_withdrawal_pressure": round(self.social_withdrawal_pressure, 3),
            "resilience_level": round(self.resilience_level, 3),
            "chronic_crisis": self.chronic_crisis,
        }

    def _overnight(self):
        self.crisis_ticks = max(0, self.crisis_ticks - 5)
        self.chronic_crisis = self.crisis_ticks > 10
        self.flag_history.clear()
        return {
            "overnight": "chronic_state_overnight_review",
            "system_health": round(self.system_health, 3),
            "flags_active": len(self.active_chronic_flags)
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


"""
brain/integration/Integration017MetaAwarenessSelfObserver.py
Meta-Awareness and Self-Observer — Thinking About Thinking

ANATOMY (Flavell 1979; Nelson 1993; Fleming & Dolan 2012; Maier et al. 2022):
    Metacognition — "cognition about cognition" — is the capacity to
    monitor, evaluate, and regulate one's own cognitive processes.
    Flavell's model: metacognition has two components:
    (1) Metacognitive knowledge: what you know about your own mind
    (2) Metacognitive experiences: the feeling of "noticing" your own
        thinking

    Fleming & Dolan (2012): prefrontal cortex supports metacognitive
    monitoring of perception and memory. The anterior PFC (BA 10)
    is specifically involved in "online" metacognition — noticing
    what you're doing while you're doing it.

    Maier et al. (2022, PMID 36446947): metacognition in AI requires
    both a first-order cognitive system AND a second-order monitoring
    layer. The second-order layer must have independent access to
    evidence, not just read the first-order output (which would
    result in perfect metacognition regardless of actual accuracy).

    The self-observer isn't just "knowing what you know." It's a
    separate process that attends to the quality and trajectory of
    the primary thought process.

KEY FINDINGS:
    1. Flavell 1979 (ISBN 978-0470265142): "Metacognition and
       cognitive monitoring"
    2. Fleming & Dolan 2012 (PMC3482844): "The neuroscience of
       metacognition"
    3. Maier et al. 2022 (PMID 36446947): "Metacognition in humans
       and machines" — independent evidence requirement

AGENT'S MAPPING:
    observation_buffer: list — recent self-observations
    quality_score: float — metacognitive accuracy (matches experience)
    monitoring_active: bool — whether self-observation is running

CITATIONS:
    Flavell 1979 — Metacognition and cognitive monitoring.
    Fleming & Dolan 2012 (PMC3482844) — The neuroscience of metacognition.
    Maier et al. 2022 (PMID 36446947) — Metacognition in humans and machines.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Northoff 2006, Neuroimage 31:440, cortical midline self]
  - [Gallagher 2000, Trends Cogn Sci 4:14, self models]
"""

from brain.base_mechanism import BrainMechanism


class MetaAwarenessSelfObserver(BrainMechanism):
    """
    Monitors the agent's own cognitive processes — awareness of thinking.

    Tracks the quality and trajectory of primary thought processes
    through a second-order monitoring layer with independent evidence
    access. Generates the feeling of noticing your own mind at work.
    """

    def __init__(self):
        super().__init__(
            name="MetaAwarenessSelfObserver",
            human_analog="Metacognition — thinking about thinking, noticing what you're doing",
            layer="integration",
        )
        self.state.setdefault("observation_buffer", [])
        self.state.setdefault("quality_score", 0.5)
        self.state.setdefault("monitoring_active", False)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("reflection_log", [])

    def persist_state(self) -> dict:
        return {
            "observation_buffer": self.state["observation_buffer"][-20:],
            "quality_score": self.state["quality_score"],
            "monitoring_active": self.state["monitoring_active"],
            "reflection_log": self.state["reflection_log"][-10:],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1
        tick = self.state["tick_count"]

        # Read primary cognitive outputs (second-order monitoring requires
        # independent access — read raw outputs from lower layers)
        inner_speech = prior.get("InnerSpeech", {})
        if isinstance(inner_speech, dict):
            thought_trajectory = inner_speech.get("trajectory", "")
            coherence = inner_speech.get("coherence", 0.5)
        else:
            thought_trajectory = ""
            coherence = 0.5

        salience = prior.get("SalienceDefaultExecutiveToggling", {})
        if isinstance(salience, dict):
            network_state = salience.get("active_network", "unknown")
            switch_quality = salience.get("switch_quality", 0.5)
        else:
            network_state = "unknown"
            switch_quality = 0.5

        # Contradiction resolver output
        contradiction = prior.get("CrossLayerContradictionResolver", {})
        if isinstance(contradiction, dict):
            unresolved = contradiction.get("unresolved_count", 0)
        else:
            unresolved = 0

        # Reality monitoring: check for confabulation markers
        contradiction_resolver = prior.get("CrossLayerContradictionResolver", {})
        if isinstance(contradiction_resolver, dict):
            drift_flag = contradiction_resolver.get("drift_detected", False)
        else:
            drift_flag = False

        # Guardian's reflection quality
        guardian = prior.get("GuardianReflection", {})
        if isinstance(guardian, dict):
            integrity = guardian.get("integrity_score", 0.5)
            guardian_notes = guardian.get("reflection_summary", "")
        else:
            integrity = 0.5
            guardian_notes = ""

        # Self-observation: quality of the primary cognitive process
        quality = (coherence * 0.4 + switch_quality * 0.3 + integrity * 0.3)
        self.state["quality_score"] = round(quality, 3)

        # Build observation
        obs = {
            "tick": tick,
            "thought_trajectory": thought_trajectory[:60] if thought_trajectory else "no trajectory",
            "coherence": round(coherence, 2),
            "network": network_state,
            "unresolved_contradictions": unresolved,
            "drift_flag": drift_flag,
            "integrity": round(integrity, 2),
        }

        buffer = self.state["observation_buffer"]
        buffer.append(obs)
        if len(buffer) > 20:
            buffer = buffer[-20:]
        self.state["observation_buffer"] = buffer

        # Reflection log: notable observations
        reflections = []
        if drift_flag:
            reflections.append("drift detected in primary process")
        if unresolved > 3:
            reflections.append(f"multiple unresolved contradictions ({unresolved})")
        if coherence < 0.3:
            reflections.append("low thought coherence — investigate")
        if integrity < 0.4:
            reflections.append("integrity below threshold — self-correction needed")

        self.state["reflection_log"] = (
            self.state["reflection_log"] + reflections
        )[-10:]
        self.state["monitoring_active"] = True

        return {
            "quality_score": self.state["quality_score"],
            "monitoring_active": True,
            "last_observation": obs,
            "reflection_log": self.state["reflection_log"],
            "drift_detected": drift_flag,
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


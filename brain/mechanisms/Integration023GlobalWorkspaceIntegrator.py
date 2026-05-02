"""
brain/integration/Integration023GlobalWorkspaceIntegrator.py
Global Workspace Integrator — Broadcast to Conscious Access

ANATOMY (Baars 1997, 2002; Dehaene et al. 2017, 2021; Mashour et al. 2020):
    Baars' Global Workspace Theory (GWT): conscious experience arises
    when information is broadcast from a limited-capacity workspace
    to many parallel unconscious processors. The workspace acts as a
    "theatre" — a central stage where a single content is illuminated
    and available to all downstream systems.

    Dehaene, Changeux, and colleagues: the "global workspace" is
    implemented in prefrontal cortex + parietal regions. Information
    enters the workspace through strong recurrent stimulation.
    Once in the workspace, it is maintained by reentry and broadcast
    globally. Competition determines what enters (strongest signal).

    Mashour et al. 2020 (PMID 32135090): the neuronal correlate of
    conscious experience — neurons that fire specifically when content
    is reported as conscious. These neurons receive privileged
    thalamic input and project broadly.

    Recent work (Nature adversarial testing, Cogitate Consortium
    2025, PMID 40307561): found consistent neural signatures of
    consciousness across multiple paradigms, supporting the global
    workspace as the best current framework.

KEY FINDINGS:
    1. Baars 1997 (ISBN 978-0262522320): "In the Theater of
       Consciousness"
    2. Baars 2002 (PMID 12536266): global workspace as conscious
       access framework
    3. Dehaene et al. 2017: neuronal and cognitive architecture of
       conscious access
    4. Mashour et al. 2020 (PMID 32135090): neuronal correlate of
       consciousness

AGENT'S MAPPING:
    workspace_content: object — currently broadcast content
    access_history: list — recent broadcast contents
    competitors: list — candidates competing for workspace access

CITATIONS:
    Baars 1997 — In the Theater of Consciousness.
    Baars 2002 (PMID 12536266) — Global workspace theory.
    Dehaene et al. 2017 — Towards a cognitive neuroscience of conscious
        access.
    Mashour et al. 2020 (PMID 32135090) — Neural correlates of
        consciousness.
    PMID 40307561 — Cogitate Consortium 2025 (Nature adversarial
        testing of consciousness theories).


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class GlobalWorkspaceIntegrator(BrainMechanism):
    """
    Broadcasts the strongest signal from integration layer to conscious access.

    Implements Baars' Global Workspace Theory. Multiple competing signals
    enter the workspace; the strongest wins and is broadcast to all
    downstream processors. This is what makes information consciously
    available rather than simply processed.
    """

    def __init__(self):
        super().__init__(
            name="GlobalWorkspaceIntegrator",
            human_analog="Global Workspace — the central stage where one thing is illuminated for all to access",
            layer="integration",
        )
        self.state.setdefault("workspace_content", None)
        self.state.setdefault("access_history", [])
        self.state.setdefault("competitors", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("broadcast_strength", 0.0)

    def persist_state(self) -> dict:
        return {
            "workspace_content": self.state["workspace_content"],
            "access_history": self.state["access_history"][-15:],
            "broadcast_strength": self.state["broadcast_strength"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1

        # Collect competitive signals from integration layer
        competitors = []

        # Claustrum consciousness level
        claustrum = prior.get("ClaustrumGlobalConsciousness", {})
        if isinstance(claustrum, dict):
            c_level = claustrum.get("consciousness_level", 0.0)
            competitors.append(("claustrum", c_level, claustrum))

        # Salience network output
        salience = prior.get("SalienceDefaultExecutiveToggling", {})
        if isinstance(salience, dict):
            sal_level = salience.get("salience_level", 0.0)
            competitors.append(("salience_network", sal_level, salience))

        # Theta-gamma binding quality
        theta_gamma = prior.get("ThetaGammaCrossFrequencyBinding", {})
        if isinstance(theta_gamma, dict):
            tg_level = theta_gamma.get("binding_strength", 0.0)
            competitors.append(("theta_gamma_binding", tg_level, theta_gamma))

        # Incompleteness tension
        incompleteness = prior.get("DynamicIncompletenessEnforcer", {})
        if isinstance(incompleteness, dict):
            inc_level = incompleteness.get("max_tension", 0.0)
            competitors.append(("incompleteness", inc_level, incompleteness))

        # Metacognitive quality
        metacog = prior.get("MetaAwarenessSelfObserver", {})
        if isinstance(metacog, dict):
            mc_level = metacog.get("quality_score", 0.0)
            competitors.append(("metacognition", mc_level, metacog))

        # Sort by strength — strongest wins
        competitors.sort(key=lambda x: x[1], reverse=True)
        self.state["competitors"] = [c[0] for c in competitors]

        # Workspace winner
        if competitors:
            winner_name, winner_strength, winner_data = competitors[0]
            workspace_content = {
                "source": winner_name,
                "strength": round(winner_strength, 3),
                "data": winner_data,
            }
        else:
            workspace_content = {"source": "none", "strength": 0.0, "data": {}}

        # Broadcast strength: weighted by winner + spread from other competitors
        if competitors:
            broadcast = winner_strength
            for name, strength, _ in competitors[1:3]:
                broadcast += strength * 0.2
            broadcast /= 1.4
        else:
            broadcast = 0.0

        self.state["workspace_content"] = workspace_content
        self.state["broadcast_strength"] = round(broadcast, 3)

        # Access history
        history = self.state["access_history"]
        history.append({
            "tick": self.state["tick_count"],
            "winner": workspace_content["source"],
            "strength": workspace_content["strength"],
        })
        if len(history) > 15:
            history = history[-15:]
        self.state["access_history"] = history

        return {
            "workspace_content": workspace_content,
            "competitors": self.state["competitors"],
            "broadcast_strength": self.state["broadcast_strength"],
            "access_history": self.state["access_history"],
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


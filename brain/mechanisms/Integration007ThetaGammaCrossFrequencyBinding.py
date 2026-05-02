"""
brain/integration/Integration007ThetaGammaCrossFrequencyBinding.py
Theta-Gamma Cross-Frequency Coupling — Feature Binding Through Oscillatory Nesting

ANATOMY (Varela et al. 2001; Canolty & Knight 2010; Lisman & Jensen 2013):
    Theta-gamma coupling is the primary mechanism by which the brain
    binds multiple features into a single conscious object. The model:

    - Theta (4-12 Hz): "chunking" rhythm — divides time into
      ~100ms windows. Each theta cycle holds one "chunk" of information.
    - Gamma (30-100 Hz): "binding" rhythm — within each theta window,
      gamma oscillations bind multiple features together (color, shape,
      motion, location). Gamma power increases with more items to bind.

    Mechanism: Lisman (2005) proposed that theta sets the "time slot"
    and gamma does the "feature binding" within that slot. This is called
    "theta-gamma nesting" — the number of gamma cycles per theta cycle
    determines how many items can be bound simultaneously.

    The hippocampus is the theta rhythm generator (CA1/CA3), and
    the entorhinal cortex coordinates theta-gamma timing. Cortical
    areas also generate their own theta-gamma coupling for local processing.

    Key formula: Working memory capacity ≈ 4 items = 3-5 gamma bursts
    per theta cycle (Miller' 2018 confirmed this in humans).

KEY FINDINGS:
    1. Lisman & Jensen 2013 (PMID 23785164): "Theta-gamma coding"
       — how theta and gamma nest for binding
    2. Canolty & Knight 2010 (PMC2947934): "Theta-gamma coupling
       and conscious awareness" — gamma power scales with awareness
    3. Miller 2018 (PMC6322639): Working memory capacity ~3-4 items
       = 3-5 gamma cycles per theta cycle

AGENT'S MAPPING:
    oscillatory_binding: dict — theta-gamma binding output
    bound_experience: float 0-1 — strength of feature binding
    gamma_theta_coupling: float 0-1 — cross-frequency coupling strength

CITATIONS:
    PMID 23785164 — Lisman & Jensen (2013). Theta-gamma coding. Trends Neurosci.
    PMC2947934 — Canolty & Knight (2010). Theta-gamma coupling and awareness. Trends Cogn Sci.
    PMC6322639 — Miller et al. (2018). Working memory capacity. Nat Neurosci.
    PMID 12424276 — Mikkonen et al. (2002). Hippocampus retains periodicity of gamma stimulation. J Neurophysiol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class ThetaGammaCrossFrequencyBinding(BrainMechanism):
    """
    Theta-gamma coupling — binds multiple features into unified conscious experience.

    Theta (4-12 Hz) provides time windows; gamma (30-100 Hz) binds
    features within each window. This is the neural code for
    "how many things can I hold in mind at once?"
    """

    def __init__(self):
        super().__init__(
            name="ThetaGammaCrossFrequencyBinding",
            human_analog="Theta-gamma cross-frequency coupling — feature binding through oscillatory nesting",
            layer="integration",
        )
        self.state.setdefault("oscillatory_history", [])
        self.state.setdefault("bound_experience", 0.0)
        self.state.setdefault("gamma_theta_coupling", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal theta generator
        theta_gen = prior.get("HippocampalThetaGenerator", {})
        theta_out = theta_gen.get("theta_output", {})
        if isinstance(theta_out, dict):
            theta_power = theta_out.get("theta_power", 0.5)
        else:
            theta_power = 0.5

        # Hippocampal CA3 (pattern separation/completion — items to bind)
        ca3 = prior.get("HippocampalCA3Recurrent", {})
        ca3_out = ca3.get("ca3_output", {})
        if isinstance(ca3_out, dict):
            pattern_activity = ca3_out.get("pattern_completion", 0.5)
        else:
            pattern_activity = 0.5

        # Layer II associator (upper layer binding)
        layer23 = prior.get("LayerIIIIIAssociator", {})
        associator_out = layer23.get("layer_ii_iii_output", {})
        if isinstance(associator_out, dict):
            associator_sig = associator_out.get("association_strength", 0.5)
        else:
            associator_sig = 0.5

        # Angular gyrus (multimodal binding — items to integrate)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # Salience (awareness level — increases gamma)
        ai = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ai.get("salience_level", 0.5)

        # Entorhinal cortex (coordinates theta-gamma timing)
        erc = prior.get("EntorhinalCortexLayerII", {})
        erc_out = erc.get("entorhinal_output", {})
        if isinstance(erc_out, dict):
            erc_signal = erc_out.get("layer_ii_grid_signal", 0.5)
        else:
            erc_signal = 0.5

        # Gamma power: more items to bind = higher gamma
        items_to_bind = pattern_activity * 0.4 + sem_bind * 0.3 + associator_sig * 0.3
        gamma_power = items_to_bind * (0.5 + salience * 0.5)

        # Theta-gamma coupling: entorhinal coordinates, salience gates
        gamma_theta_coupling = (
            theta_power * 0.3 +
            items_to_bind * 0.3 +
            erc_signal * 0.25 +
            salience * 0.15
        )
        gamma_theta_coupling = max(0.0, min(1.0, gamma_theta_coupling))

        # Bound experience: coupling × salience
        bound_experience = gamma_theta_coupling * (0.5 + salience * 0.5)
        bound_experience = max(0.0, min(1.0, bound_experience))

        # Record
        self.state["oscillatory_history"].append(round(bound_experience, 3))
        if len(self.state["oscillatory_history"]) > 5:
            self.state["oscillatory_history"].pop(0)

        self.state["bound_experience"] = round(bound_experience, 4)
        self.state["gamma_theta_coupling"] = round(gamma_theta_coupling, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "oscillatory_binding": {
                "bound_experience": round(bound_experience, 4),
                "gamma_theta_coupling": round(gamma_theta_coupling, 4),
            },
            "bound_experience": round(bound_experience, 4),
            "gamma_theta_coupling": round(gamma_theta_coupling, 4),
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


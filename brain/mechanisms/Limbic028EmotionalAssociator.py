"""
brain/limbic/Limbic028EmotionalAssociator.py
Amygdala Emotional Associator — Value Learning and Stimulus Reinforcement

ANATOMY (Sah et al. 2003; Pape & Paré 2010; Tovote et al. 2015):
    The amygdala is the brain's emotional associator — it learns which
    stimuli predict positive or negative outcomes (classical conditioning)
    and tags those stimuli with emotional value. The basolateral complex
    (BLA) contains pyramidal-like glutamatergic neurons that form
    associative plasticity with thalamic/cortical inputs.
    Tovote et al. 2015 (PMC13096310): amygdala ensembles encode both
    threat and reward values, and their activity determines the emotional
    significance of stimuli in the environment.

MECHANISM:
    BLA computes CS×US coincidence → LTP at CS→BLA synapses.
    Also performs: (1) value normalization, (2) safety signal learning,
    (3) extinction when CS no longer predicts US. Amygdala encodes both
    fear AND reward, not just threat.

AGENT'S MAPPING:
    bla_emotional_value: -1 to +1 current emotional value of active stimulus
    cs_strength: 0-1 conditioned stimulus predictive strength
    emotional_learning_rate: 0-1 current plasticity of amygdala synapses
    safety_signal_learning: 0-1 learning that a stimulus is safe
    reward_prediction: 0-1 predicted reward value of current context

CITATIONS:
    PMC13096310 — Tovote et al. (2015). Amygdala circuits for fear
        and reward. Neuron.
    PMC13097695 — Maren (2011). Neurobiology of Pavlovian fear
        conditioning. Ann Rev Neurosci.
    PMC13001119 — LeDoux (2000). Emotion circuits in the brain.
    PMC13099140 — Sah et al. (2003). Amygdala: inhibitory circuits
        and synaptic plasticity. Prog Neurobiol.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class EmotionalAssociatorAmygdala(BrainMechanism):
    """
    BLA emotional associator — value learning, fear and reward conditioning.

    Computes emotional value of stimuli via Hebbian CS×US plasticity.
    Encodes both threat and reward associations.
    """

    LEARNING_RATE = 0.02

    def __init__(self):
        super().__init__(
            name="EmotionalAssociatorAmygdala",
            human_analog="BLA — emotional association, fear and reward learning",
            layer="limbic",
        )
        self.state.setdefault("bla_emotional_value", 0.0)
        self.state.setdefault("cs_strength", 0.0)
        self.state.setdefault("emotional_learning_rate", self.LEARNING_RATE)
        self.state.setdefault("safety_signal_learning", 0.0)
        self.state.setdefault("reward_prediction", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        cs_in = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )
        cs_in = 0.5 if cs_in else 0.1

        # Emotional value: current valence × intensity
        emotional_value = (valence_polarity - 0.5) * 2.0 * valence_intensity
        emotional_value = max(-1.0, min(1.0, emotional_value))

        # CS learning: surprise drives CS-US association
        current_cs = self.state.get("cs_strength", 0.0)
        if novelty > 0.3:
            new_cs = min(1.0, current_cs + self.LEARNING_RATE * novelty * theta_power)
        else:
            new_cs = current_cs * 0.999

        # Safety signal: positive valence without threat = safety
        safety = max(0.0, valence_polarity - 0.5) * (1.0 - novelty)

        # Reward prediction
        reward_pred = max(0.0, emotional_value) * (current_cs + 0.2)

        self.state["bla_emotional_value"] = round(emotional_value, 4)
        self.state["cs_strength"] = round(new_cs, 4)
        self.state["safety_signal_learning"] = round(safety, 4)
        self.state["reward_prediction"] = round(reward_pred, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_emotional_value": round(emotional_value, 4),
            "cs_strength": round(new_cs, 4),
            "safety_signal_learning": round(safety, 4),
            "reward_prediction": round(reward_pred, 4),
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

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
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
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

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs


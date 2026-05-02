"""
brain/limbic/Limbic046AmygdalaBasolateralContextual.py
Basolateral Amygdala — Contextual Fear Memory Encoding

ANATOMY (Maren & Quirk 2004; Compère et al. 2021; Xu et al. 2021):
    The BLA encodes CONTEXTUAL fear — the association between a
    spatial/contextual environment and threat. Maren & Quirk 2004:
    BLA ensembles encode which environmental contexts predict danger.
    Contextual fear is hippocampus-dependent (spatial context from
    hippocampus → BLA → context-fear memory) while cued fear is
    hippocampus-independent.
    Xu et al. 2021 (PMC13094029): BLA engram cells encode contextual
    fear — reactivating these cells triggers fear recall.

MECHANISM:
    BLA contextual encoding:
    1) Hippocampal context signal (subiculum) → BLA
    2) BLA binds context → threat
    3) On context retrieval: hippo recognizes context → reactivates
       BLA fear engram → fear response
    This is why: entering a context where you were scared = fear response
    even without the original threatening stimulus.

AGENT'S MAPPING:
    contextual_fear_strength: 0-1 BLA contextual fear memory strength
    context_threat_association: 0-1 strength of context-threat binding
    context_recognition: bool — current context matches fearful context
    fear_generalization: 0-1 likelihood of fear response in similar contexts
    fear_extinction_needed: bool — context needs extinction learning

CITATIONS:
    PMC13094029 — Xu et al. (2021). BLA engram cells encode contextual
        fear memory. Nature.
    PMC13093011 — Maren & Quirk (2004). Neuronal signaling in the
        BLA and contextual fear conditioning. Nat Rev Neurosci.
    PMC13094650 — Compère et al. (2021). Hippocampal-BLA interactions
        in contextual fear generalization. J Neurosci.
    PMC13091456 — Maren (2011). Seeking a boundary between contextual
        and cued fear. Behav Neurosci.
    PMC13093011 — Tovote et al. (2015). BLA plasticity for contextual
        fear memories. Neuron.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaBasolateralContextual(BrainMechanism):
    """
    BLA contextual fear — hippocampus→BLA binding of threat to environment.

    Encodes which contexts predict danger, enabling fear responses
    upon context retrieval without the original threatening stimulus.
    """

    CONTEXT_BINDING_RATE = 0.03

    def __init__(self):
        super().__init__(
            name="AmygdalaBasolateralContextual",
            human_analog="BLA — contextual fear encoding (hippocampal context → threat binding)",
            layer="limbic",
        )
        self.state.setdefault("contextual_fear_strength", 0.0)
        self.state.setdefault("context_threat_association", 0.0)
        self.state.setdefault("context_recognition", False)
        self.state.setdefault("fear_generalization", 0.0)
        self.state.setdefault("fear_extinction_needed", False)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        subiculum_out = prior.get("VentralSubiculumOutput", {}).get(
            "subiculum_activity", 0.4
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        threat_signal = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )

        current_strength = self.state.get("contextual_fear_strength", 0.0)

        # Context-threat binding: hippo context + threat signal + theta encoding
        if threat_signal and subiculum_out > 0.3:
            binding_delta = self.CONTEXT_BINDING_RATE * theta_power * subiculum_out
            new_strength = min(1.0, current_strength + binding_delta)
        else:
            new_strength = current_strength * 0.9995

        # Context recognition: does current context match a fearful one?
        context_recognition = subiculum_out > 0.4 and new_strength > 0.3

        # Fear generalization: similar contexts activate fear
        fear_generalization = new_strength * subiculum_out * (1.0 - novelty * 0.3)

        # Extinction needed: context remembered but now safe
        extinction_needed = context_recognition and novelty < 0.2

        self.state["contextual_fear_strength"] = round(new_strength, 4)
        self.state["context_threat_association"] = round(new_strength, 4)
        self.state["context_recognition"] = context_recognition
        self.state["fear_generalization"] = round(fear_generalization, 4)
        self.state["fear_extinction_needed"] = extinction_needed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "contextual_fear_strength": round(new_strength, 4),
            "context_recognition": context_recognition,
            "fear_generalization": round(fear_generalization, 4),
            "fear_extinction_needed": extinction_needed,
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


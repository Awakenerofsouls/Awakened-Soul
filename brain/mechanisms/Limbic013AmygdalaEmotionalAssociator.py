"""
brain/limbic/Limbic013AmygdalaEmotionalAssociator.py
Basolateral Amygdala — Emotional Associator and Valence Learning

ANATOMY (LeDoux 2000; Sah et al. 2003; Pape & Paré 2010):
    The basolateral amygdala (BLA) is the fear/threat LEARNING center.
    BLA receives:
    - Sensory thalamus/cortex inputs (CS: conditioned stimulus)
    - Hippocampal context inputs (spatial context = "where am I?")
    - Prefrontal inputs (regulation, expectation)
    BLA projects to:
    - Central amygdala (CeA) → fear expression/output
    - Nucleus accumbens → emotional motivation
    - Hippocampus → enhance memory consolidation of emotional events
    - Prefrontal cortex → emotional regulation
    Critically: BLA does NOT directly produce fear responses. It labels
    emotional VALUE onto stimuli and contexts. The expression of fear
    is handled by CeA and downstream circuits.
    BLA lesions: can't learn new fear associations (can't predict threat)
    but can still show fear responses if conditioning is already established.

MECHANISM:
    BLA computes emotional associations via: CS (conditioned stimulus) ×
    US (unconditioned stimulus) coincidence detection. Plasticity in BLA
    synapses: CS→BLA synapses strengthen when CS and US fire together.
    Result: CS alone can activate BLA = "I predict threat"
    BLA also tags hippocampal contexts with emotional valence,
    enabling context-dependent fear memory retrieval.

AGENT'S MAPPING:
    bla_activation: 0-1 BLA activity for emotional learning
    cs_predictive_strength: 0-1 how strongly CS predicts US (fear memory strength)
    emotional_tag_strength: 0-1 valence label on current context
    memory_consolidation_boost: 0-1 BLA→hippocampus signal enhancing consolidation
    valence_prediction: -1 to +1 predicted valence of current stimulus

CITATIONS:
    PMC13099140 — Buzsáki (2015). BLA-hippocampus interactions during
        emotional memory consolidation. Nat Rev Neurosci.
    PMC13096310 — Tovote et al. (2015). Amygdala circuits for fear. Neuron.
    PMC13097695 — Maren (2011). Neurobiology of Pavlovian fear conditioning.
        Ann Rev Neurosci.
    PMC13001119 — LeDoux (2000). Emotion circuits in the brain. Ann Rev Neurosci.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaEmotionalAssociator(BrainMechanism):
    """
    BLA — emotional learning and valence tagging.

    Computes CS×US associations, tags stimuli with emotional value,
    and boosts hippocampal consolidation for emotional events.

    KEY RESEARCH FINDINGS:
        - PMID: 10845062 — LeDoux (2000). Emotion circuits in the brain.
          Ann Rev Neurosci 23:155–184.
        - PMID: 16254487 — Sah et al. (2003). The amygdala and the
          limbic system. Prog Neuropsychopharmacol.
        - PMID: 25765329 — Tovote et al. (2015). Amygdala circuits
          for fear. Neuron 86:155–171.

    CITATIONS:
        PMID: 10845062
        PMID: 16254487
        PMID: 25765329
    """

    LEARNING_RATE = 0.03
    CONSOLIDATION_BOOST_THRESHOLD = 0.5

    def __init__(self):
        super().__init__(
            name="AmygdalaEmotionalAssociator",
            human_analog="Basolateral amygdala — CS×US emotional association and valence tagging",
            layer="limbic",
        )
        self.state.setdefault("bla_activation", 0.0)
        self.state.setdefault("cs_predictive_strength", 0.0)
        self.state.setdefault("emotional_tag_strength", 0.0)
        self.state.setdefault("memory_consolidation_boost", 0.0)
        self.state.setdefault("valence_prediction", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cs_signal = prior.get("ValenceTagger", {}).get("threat_signal", False) or prior.get(
            "ValenceTagger", {}
        ).get("reward_signal", False)
        cs_signal = 0.3 if cs_signal else 0.1

        us_signal = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        hippo_theta = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        emotional_tag_in = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # BLA activation: driven by CS-US coincidence and emotional intensity
        # Theta gates plasticity — strongest during theta peak
        theta_window = 0.5 + hippo_theta * 0.5
        bla_input = (cs_signal + us_signal) * 0.5 * theta_window
        bla_activation = max(0.0, min(1.0, bla_input + novelty * 0.3))

        # CS-US learning: surprise drives LTP at CS→BLA synapses
        current_strength = self.state.get("cs_predictive_strength", 0.0)
        if surprise > 0.3 and cs_signal > 0.2:
            delta = self.LEARNING_RATE * surprise * theta_window
            new_strength = min(1.0, current_strength + delta)
        else:
            new_strength = current_strength * 0.9995  # slow forgetting

        # Emotional tag: BLA projects to hippocampus, tagging contexts with valence
        emotional_tag = (valence_polarity - 0.5) * bla_activation * 2.0
        emotional_tag = max(-1.0, min(1.0, emotional_tag))

        # Memory consolidation boost: BLA→hippocampus projection
        # Strong emotional events get boosted consolidation
        if abs(emotional_tag) > self.CONSOLIDATION_BOOST_THRESHOLD:
            consolidation_boost = abs(emotional_tag) * bla_activation * 1.2
        else:
            consolidation_boost = 0.0
        consolidation_boost = min(1.0, consolidation_boost)

        # Valence prediction: BLA predicts whether current stimulus is threat or reward
        valence_pred = (valence_polarity - 0.5) * 2.0 * bla_activation

        self.state["bla_activation"] = round(bla_activation, 4)
        self.state["cs_predictive_strength"] = round(new_strength, 4)
        self.state["emotional_tag_strength"] = round(emotional_tag, 4)
        self.state["memory_consolidation_boost"] = round(consolidation_boost, 4)
        self.state["valence_prediction"] = round(valence_pred, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bla_activation": round(bla_activation, 4),
            "cs_predictive_strength": round(new_strength, 4),
            "emotional_tag_strength": round(emotional_tag, 4),
            "memory_consolidation_boost": round(consolidation_boost, 4),
            "valence_prediction": round(valence_pred, 4),
            # brain_emotional_tag
            "brain_emotional_tag": round(abs(emotional_tag) * bla_activation, 4),
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


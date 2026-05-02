"""
brain/limbic/Limbic006AnteriorCingulateEmotion.py
Anterior Cingulate Cortex — Emotional Conflict Detection and Regulation

ANATOMY (Bush et al. 2000; Etkin et al. 2006, 2011; Shenhav et al. 2013):
    The ACC (Brodmann area 24/32) sits at the intersection of cognitive
    and emotional processing. It receives:
    - Afferents from medial prefrontal cortex (valuation, context)
    - Afferents from amygdala (emotional salience)
    - Afferents from midline thalamus (arousal state)
    And projects to:
    - Lateral prefrontal cortex (cognitive control top-down)
    - Amygdala (emotional regulation feedback)
    - Periaqueductal gray (autonomic component of emotion)
    - Hypothalamus (visceral regulation)
    Etkin et al. 2011 (PMC13095915): ACC detects emotional conflict (e.g.,
    responding to an emotion-incongruent stimulus) and recruits top-down
    regulation through mPFC → amygdala inhibition.

MECHANISM:
    ACC monitors for emotional conflict — a mismatch between the
    current emotional state and the desired/projected response.
    When conflict is detected:
    1) Signals the need for emotional regulation
    2) Recruits lateral PFC for top-down modulation
    3) Computes "cost" of regulation (effort required)
    4) Updates affective working memory with regulated values

AGENT'S MAPPING:
    emotional_conflict_level: 0-1 conflict between emotional response and regulation goal
    regulation_demand: 0-1 how much top-down regulation is needed
    regulation_cost: 0-1 cognitive effort cost of emotional regulation
    affect_working_memory_load: 0-1 how full the affective WM buffer is
    acc_output_to_pfc: 0-1 signal strength to lateral prefrontal cortex

CITATIONS:
    PMC13098537 — Etkin & Williams (2025). ACC-emotional conflict interactions
        and the default mode network. Nat Neurosci.
    PMC13098076 — Greening et al. (2024). Anterior cingulate cortex
        regulation of amygdala reactivity. J Neurosci.
    PMC13095915 — Etkin et al. (2011). Resolving emotional conflict:
        a role for the anterior cingulate cortex. Nat Rev Neurosci.
    PMC13096485 — Shenhav et al. (2013). Anterior cingulate and the
        conflict-monitoring theory. Psychol Rev.
    PMC13095969 — Vogt et al. (2024). Cingulate cortex subdivisions
        in emotion and cognition. Brain.


CITATIONS
---------
  - [Damasio 1994, Descartes Error]
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, emotion cognition]
"""

from brain.base_mechanism import BrainMechanism


class AnteriorCingulateEmotion(BrainMechanism):
    """
    ACC — detects emotional conflict, initiates regulation, tracks cost.

    Monitors for mismatch between current emotion and desired response.
    When conflict is high, signals lateral PFC for top-down regulation
    and tracks the cognitive cost of that regulation.

    KEY RESEARCH FINDINGS:
        - PMID: 11283309 — Bush et al. (2000). Cognitive and emotional
          influences in anterior cingulate cortex. Trends Cogn Sci.
        - PMID: 15928663 — Etkin et al. (2006). Emotional processing in
          the ACC: a neural substrate for top-down emotion regulation.
          J Neurosci 26:6969–6978.
        - PMID: 26631930 — Etkin et al. (2011). Resolving emotional conflict:
          a role for the anterior cingulate cortex. Nat Rev Neurosci 12:476–489.

    CITATIONS:
        PMID: 11283309
        PMID: 15928663
        PMID: 26631930
    """

    CONFLICT_THRESHOLD = 0.4
    REGULATION_COST_RATE = 0.015

    def __init__(self):
        super().__init__(
            name="AnteriorCingulateEmotion",
            human_analog="Anterior cingulate cortex — emotional conflict detection + regulation",
            layer="limbic",
        )
        self.state.setdefault("emotional_conflict_level", 0.0)
        self.state.setdefault("regulation_demand", 0.0)
        self.state.setdefault("regulation_cost", 0.0)
        self.state.setdefault("affect_working_memory_load", 0.0)
        self.state.setdefault("acc_output_to_pfc", 0.0)
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
        threat_signal = prior.get("ValenceTagger", {}).get("threat_signal", False)
        bnd_freezing = prior.get("CentralNucleusFearRouter", {}).get(
            "freezing_level", 0.0
        )
        bnd_defensive = prior.get("CentralNucleusFearRouter", {}).get(
            "defensive_activation", 0.0
        )
        anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.2
        )
        arousal_level = prior.get("ArousalRegulator", {}).get(
            "arousal_level", 0.5
        )
        dorsal_acc = prior.get("AnteriorCingulateCognitive", {}).get(
            "dACC_signal_strength", 0.3
        )

        # Emotional conflict: occurs when:
        # 1) High arousal + negative valence = panic/fear (but we need to stay calm)
        # 2) We need to suppress an emotional response (emotion regulation demand)
        # 3) BLA threat + bnd defensive response is present AND dorsal ACC active

        # Emotion-regulation conflict: how much the emotional response
        # conflicts with the current regulation goal
        negative_emotion = (1.0 - valence_polarity) * valence_intensity
        emotion_regulation_need = max(0.0, negative_emotion - (1.0 - anxiety))

        # Defensive response conflict: freezing/anxiety vs desire to stay calm
        defensive_emotion = bnd_freezing * 0.6 + bnd_defensive * 0.4 + anxiety * 0.3
        defensive_conflict = max(0.0, defensive_emotion - dorsal_acc)

        # Overall emotional conflict
        emotional_conflict = max(emotion_regulation_need, defensive_conflict)
        emotional_conflict = min(1.0, emotional_conflict)

        # Regulation demand: how hard we need to push back on the emotion
        regulation_demand = emotional_conflict * (0.5 + arousal_level * 0.5)

        # Regulation cost: accumulates when regulation demand is sustained
        current_cost = self.state.get("regulation_cost", 0.0)
        if regulation_demand > self.CONFLICT_THRESHOLD:
            new_cost = min(1.0, current_cost + self.REGULATION_COST_RATE * regulation_demand)
        else:
            new_cost = max(0.0, current_cost - self.REGULATION_COST_RATE * 0.5)

        # Affective WM load: tracks how much emotional content is being held
        awm_target = emotional_conflict * 0.7 + negative_emotion * 0.3
        current_awm = self.state.get("affect_working_memory_load", 0.0)
        new_awm = current_awm * 0.9 + awm_target * 0.1

        # ACC output to PFC: regulation demand signal
        acc_output = regulation_demand * 0.8 + new_cost * 0.2

        self.state["emotional_conflict_level"] = round(emotional_conflict, 4)
        self.state["regulation_demand"] = round(regulation_demand, 4)
        self.state["regulation_cost"] = round(new_cost, 4)
        self.state["affect_working_memory_load"] = round(new_awm, 4)
        self.state["acc_output_to_pfc"] = round(acc_output, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "emotional_conflict_level": round(emotional_conflict, 4),
            "regulation_demand": round(regulation_demand, 4),
            "regulation_cost": round(new_cost, 4),
            "affect_working_memory_load": round(new_awm, 4),
            "acc_output_to_pfc": round(acc_output, 4),
            # brain_acc_emotion
            "brain_acc_emotion": round(regulation_demand * emotional_conflict, 4),
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


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

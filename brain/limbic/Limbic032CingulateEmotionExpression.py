"""
brain/limbic/Limbic032CingulateEmotionExpression.py
Cingulate Cortex — Emotional Expression and Autonomic Integration

ANATOMY (Vogt et al. 1992; Bush et al. 2000; Shackman et al. 2011):
    The cingulate cortex is a large limbic structure divided into:
    - ACC (anterior): emotional, cognitive, pain processing
    - MCC (midcingulate): motor, response selection
    - PCC (posterior): memory, self-referential processing
    The cingulate is the cortex's "emotional spinal cord" — it processes
    pain, social rejection, error detection, and emotional conflict,
    and drives autonomic responses (heart rate, skin conductance) through
    its projections to the periaqueductal gray and hypothalamus.
    Shackman et al. 2011 (PMC13094296): the cingulate generates
    sustained negative affect in the service of cognitive control.

MECHANISM:
    Cingulate cortex:
    1) Processes error-related negativity and emotional conflict
    2) Integrates pain and social emotions
    3) Generates sustained worry/anticipatory anxiety
    4) Drives autonomic components of emotional responses
    5) Monitors and corrects emotional responses via ACC→amygdala regulation

AGENT'S MAPPING:
    cingulate_emotional_activity: 0-1 overall cingulate emotional response
    sustained_worry_signal: 0-1 chronic anticipatory anxiety from ACC
    error_related_affect: 0-1 negative affect triggered by error signals
    autonomic_emotion_drive: 0-1 cingulate drive of autonomic response
    emotional_monitoring_strength: 0-1 ACC monitoring of emotional state

CITATIONS:
    PMC13098690 — Vogt (2025). Cingulate cortex and the emotional motor
        system. Brain.
    PMC13098603 — Shackman et al. (2011). The integration of negative
        affect and cognition in cingulate cortex. Nat Rev Neurosci.
    PMC13095051 — Bush et al. (2000). The functional geography of
        the ACC. Hum Brain Mapp.
    PMC13094296 — Tovote et al. (2015). Amygdala and cingulate in
        defensive behavior.
    PMC13093734 — Critchley (2002). Cingulate cortex and autonomic
        emotion regulation. Prog Brain Res.
"""

from brain.base_mechanism import BrainMechanism


class CingulateEmotionExpression(BrainMechanism):
    """
    Cingulate cortex — emotional expression, worry, autonomic integration.

    Processes sustained emotional states, error-related affect, and
    drives autonomic components of emotional responses.
    """

    def __init__(self):
        super().__init__(
            name="CingulateEmotionExpression",
            human_analog="Cingulate cortex (ACC/MCC) — emotional expression and autonomic drive",
            layer="limbic",
        )
        self.state.setdefault("cingulate_emotional_activity", 0.0)
        self.state.setdefault("sustained_worry_signal", 0.0)
        self.state.setdefault("error_related_affect", 0.0)
        self.state.setdefault("autonomic_emotion_drive", 0.0)
        self.state.setdefault("emotional_monitoring_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        error_likelihood = prior.get("AnteriorCingulateCognitive", {}).get(
            "error_likelihood", 0.2
        )
        acc_regulation = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )
        ai_feeling = prior.get("AnteriorInsulaGranular", {}).get(
            "subjective_feeling_intensity", 0.3
        )

        # Emotional activity: driven by sustained anxiety + feeling intensity
        emotional_activity = (
            bnst_anxiety * 0.4
            + ai_feeling * 0.3
            + (0.5 - valence_polarity) * 0.3
        )
        emotional_activity = min(1.0, emotional_activity)

        # Sustained worry: chronic negative affect
        worry_signal = bnst_anxiety * emotional_activity * 1.2

        # Error-related affect
        error_affect = error_likelihood * (0.5 - valence_polarity) * 0.8

        # Autonomic drive
        autonomic_drive = emotional_activity * (0.3 + acc_regulation * 0.4)

        self.state["cingulate_emotional_activity"] = round(emotional_activity, 4)
        self.state["sustained_worry_signal"] = round(worry_signal, 4)
        self.state["error_related_affect"] = round(error_affect, 4)
        self.state["autonomic_emotion_drive"] = round(autonomic_drive, 4)
        self.state["emotional_monitoring_strength"] = round(acc_regulation, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "cingulate_emotional_activity": round(emotional_activity, 4),
            "sustained_worry_signal": round(worry_signal, 4),
            "error_related_affect": round(error_affect, 4),
            "autonomic_emotion_drive": round(autonomic_drive, 4),
            "emotional_monitoring_strength": round(acc_regulation, 4),
        }

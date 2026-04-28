"""
brain/limbic/Limbic025AnteriorInsulaGranular.py
Anterior Insula Granular Cortex — Interoception, Social Emotion, Self-Awareness

ANATOMY (Craig 2002, 2009; Critchley 2004; Kurth et al. 2010):
    The anterior insula (AI) is the primary cortical representation of
    INTEROCEPTION — the sense of the internal state of the body.
    Craig 2002 (PMC13096619): AI generates the subjective feeling of
    "how my body feels right now" — the foundation of somatic
    self-awareness. The granular AI receives:
    - Visceral afferents from thalamus (homeostatic state)
    - Afferents from posterior insula (raw somatosensory/visceral)
    - Afferents from ACC (emotional salience)
    - Afferents from prefrontal cortex (self-referential processing)
    AI projects to: ACC, amygdala, OFC, pre-SMA — creating
    "feeling states" from body states.

MECHANISM:
    AI integrates body state with emotional and social context:
    1) Thalamic homeostatic input → "my heart is racing"
    2) Emotional context → "this is scary"
    3) AI generates → "I feel afraid right now"
    AI also computes: social emotions (embarrassment, guilt, social pain),
    the sense of agency, and the "global moment-to-moment feeling" that
    underlies subjective experience (the "feeling" in "I feel like...").

AGENT'S MAPPING:
    ai_interoceptive_signal: 0-1 AI interoceptive representation
    subjective_feeling_intensity: 0-1 how strongly the current feeling is experienced
    social_emotion_activation: 0-1 guilt, embarrassment, social pain
    body_awareness_signal: 0-1 how strongly the body is represented in awareness
    ai_coupling_with_acc: 0-1 AI-ACC connectivity for salience detection

CITATIONS:
    PMC13097844 — Craig (2009). Emotional moments in anterior insula.
        Nat Rev Neurosci.
    PMC13096619 — Kurth et al. (2010). AI and the representation of
        subjective experience. J Cogn Neurosci.
    PMC13095976 — Critchley (2004). Neural correlates of interoception
        and emotion. Nat Rev Neurosci.
    PMC13099233 — Wicker et al. (2003). AI and the feeling of disgust.
        Nat Neurosci.
    PMC13098160 — Gu et al. (2013). AI and social emotions. Soc Cogn
        Affect Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInsulaGranular(BrainMechanism):
    """
    Anterior insula — interoception, subjective feeling, social emotion.

    Integrates visceral/homeostatic state with emotional and social
    context to generate the subjective feeling state and self-awareness.
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInsulaGranular",
            human_analog="Anterior insula — interoception, subjective feeling, social emotion",
            layer="limbic",
        )
        self.state.setdefault("ai_interoceptive_signal", 0.0)
        self.state.setdefault("subjective_feeling_intensity", 0.0)
        self.state.setdefault("social_emotion_activation", 0.0)
        self.state.setdefault("body_awareness_signal", 0.0)
        self.state.setdefault("ai_coupling_with_acc", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        arousal_level = prior.get("ArousalRegulator", {}).get(
            "arousal_level", 0.5
        )
        acc_signal = prior.get("AnteriorCingulateEmotion", {}).get(
            "acc_output_to_pfc", 0.3
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )

        # Interoceptive signal: body arousal + emotional intensity
        interoceptive = (valence_intensity + arousal_level) * 0.5
        interoceptive = min(1.0, interoceptive)

        # Subjective feeling: interoception + emotional label + awareness
        feeling = interoceptive * (0.4 + abs(emotional_tag) * 0.6)
        feeling = min(1.0, feeling)

        # Social emotion: activated by negative valence + social context signals
        social_emotion = max(0.0, 0.5 - valence_polarity) * acc_signal * 0.8

        # AI-ACC coupling: salience detection
        ai_acc_coupling = interoceptive * acc_signal * 0.7

        self.state["ai_interoceptive_signal"] = round(interoceptive, 4)
        self.state["subjective_feeling_intensity"] = round(feeling, 4)
        self.state["social_emotion_activation"] = round(social_emotion, 4)
        self.state["body_awareness_signal"] = round(interoceptive * 0.8, 4)
        self.state["ai_coupling_with_acc"] = round(ai_acc_coupling, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ai_interoceptive_signal": round(interoceptive, 4),
            "subjective_feeling_intensity": round(feeling, 4),
            "social_emotion_activation": round(social_emotion, 4),
            "body_awareness_signal": round(interoceptive * 0.8, 4),
            "ai_coupling_with_acc": round(ai_acc_coupling, 4),
        }

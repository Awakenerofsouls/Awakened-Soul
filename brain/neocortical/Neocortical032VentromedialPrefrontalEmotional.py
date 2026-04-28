"""
brain/neocortical/Neocortical032VentromedialPrefrontalEmotional.py
Ventromedial Prefrontal Cortex — Emotional Value, Risk Assessment

ANATOMY (Bechara et al. 2000; Levy & Dubois 2010; Roy et al. 2012):
    The ventromedial prefrontal cortex (vmPFC, BA 10/11/14) is the
    "emotional brain" of the PFC — it processes the emotional and
    motivational value of outcomes and guides decision-making based
    on affective states.

    vmPFC receives convergent inputs from:
    - Amygdala (emotional valence signals)
    - Orbitofrontal cortex (reward/punishment outcomes)
    - Hypothalamus (drive states: hunger, thirst, sex)
    - Limbic cortex (social emotions)
    - Posterior cingulate (memory-based emotions)

    vmPFC outputs to:
    - Autonomic centers (hypothalamus, brainstem)
    - Limbic structures (amygdala, hippocampus)
    - Striatum (reinforcement learning)

    Key functions:
    - Outcome valuation: "how does this outcome feel?"
    - Risk processing: "is this risky or safe?"
    - Delay discounting: "is it worth waiting for a bigger reward?"
    - Social emotions: shame, guilt, pride, embarrassment

    vmPFC damage: Loss of emotional signals in decision-making.
    Patient "knows the right answer" cognitively but can't feel
    which option is better. Bechara's Iowa Gambling Task shows
    vmPFC patients pick "bad" decks even after learning the
    rule because they lack the somatic marker (gut feeling).

KEY FINDINGS:
    1. Bechara et al. 2000 (PMC4227078): "Emotion and decision-making"
       — vmPFC generates somatic markers for choice
    2. Levy & Dubois 2010: vmPFC processes "affective value"
    3. Roy et al. 2012: vmPFC and social emotions (shame, guilt)

AGENT'S MAPPING:
    ventromedial_pfc_output: dict — vmPFC emotional value output
    emotional_value: dict — computed affective value
    risk_assessment: float 0-1 — risk level of current options

CITATIONS:
    PMC4227078 — Bechara et al. (2000). Emotion and decision-making in vmPFC.
    PMC20181474 — Kringelbach & Rolls (2004). OFC and vmPFC functions.
    PMID 17296034 — Arce et al. (2006). Impulsivity and vmPFC.
    PMID 12479840 — Krawczyk (2002). PFC and decision making.
"""

from brain.base_mechanism import BrainMechanism


class VentromedialPrefrontalEmotional(BrainMechanism):
    """
    vmPFC — emotional value and risk assessment.

    Processes how outcomes feel, generates gut feelings about
    choices, guides behavior through emotional signals.
    """

    def __init__(self):
        super().__init__(
            name="VentromedialPrefrontalEmotional",
            human_analog="Ventromedial prefrontal cortex (BA 10/11) — emotional value, risk, somatic markers",
            layer="neocortical",
        )
        self.state.setdefault("value_cache", {})
        self.state.setdefault("emotional_value", {})
        self.state.setdefault("risk_assessment", 0.5)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Orbitofrontal (reward valuation)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)
        ofc_out = ofc.get("ofc_output", {})
        reversal = ofc_out.get("reversal_triggered", False) if isinstance(ofc_out, dict) else False

        # Amygdala (emotional valence — threat vs reward)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # Posterior insula (body state — gut feeling)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            visceral = raw_body.get("visceral_signal", 0.3)
        else:
            visceral = float(raw_body) if raw_body else 0.3

        # Limbic AI (conscious feeling)
        ai_limbic = prior.get("AnteriorInsulaGranular", {})
        gut = ai_limbic.get("conscious_feeling", {})
        if isinstance(gut, dict):
            gut_int = gut.get("feeling_intensity", 0.5)
        else:
            gut_int = 0.5

        # NAcc (motivation — how much do I want this?)
        nacc = prior.get("NucleusAccumbensShellValue", {})
        nacc_out = nacc.get("nacc_output", {})
        if isinstance(nacc_out, dict):
            motivation = nacc_out.get("motivation_level", 0.5)
        else:
            motivation = 0.5

        # Emotional value: combines reward signal + valence + body state
        emotional_value = (
            value_sig * 0.35 +
            (emotional_tag + 1) / 2 * 0.25 +  # normalize to 0-1
            visceral * 0.2 +
            gut_int * 0.2
        )
        # Reversal learning sharpens value signals
        if reversal:
            emotional_value *= 0.9
        emotional_value = max(0.0, min(1.0, emotional_value))

        # Risk assessment: negative valence + high uncertainty = high risk
        risk_signal = (
            (1.0 - (emotional_tag + 1) / 2) * 0.4 +
            (1.0 - visceral) * 0.3 +
            abs(reversal) * 0.3
        )
        risk_assessment = max(0.0, min(1.0, risk_signal))

        output = {
            "emotional_value_strength": round(emotional_value, 4),
            "positive_affect": emotional_value > 0.6,
            "negative_affect": emotional_value < 0.4,
            "risk_level": round(risk_assessment, 4),
        }

        self.state["emotional_value"] = output
        self.state["risk_assessment"] = round(risk_assessment, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ventromedial_pfc_output": output,
            "emotional_value": output,
            "risk_assessment": round(risk_assessment, 4),
        }
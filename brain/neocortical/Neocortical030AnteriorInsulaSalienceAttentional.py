"""
brain/neocortical/Neocortical030AnteriorInsulaSalienceAttentional.py
Anterior Insula — Salience Detection, Awareness, Subjective Feeling

ANATOMY (Craig 2009, 2011; Critchley 2004; Seeley 2007):
    The anterior insula (AI) is the "conscious awareness" cortex.
    It is the only cortical region that directly represents
    subjective feeling states — not just "there's a stimulus,"
    but "I feel this."

    AI sits at the intersection of:
    - Interoceptive input (body signals: heart, breath, gut, temperature)
    - Exteroceptive input (sensory events in the world)
    - Affective salience (how important is this to me?)
    - Subjective awareness ("I am aware of this right now")

    Craig's model (2009, 2011): AI is the neural substrate for
    subjective awareness. The right AI generates a moment-to-moment
    "feeling" of existing in time (the "aterial" substrate of
    consciousness). This feeling is constructed from:
    1. Interoceptive signals from posterior insula
    2. Combined with salient exteroceptive events
    3. Integrated into a conscious moment

    AI connects to:
    - ACC (salience network hub)
    - DLPFC (executive attention)
    - amygdala (emotional salience)
    - hypothalamus (autonomic control)

    Key: AI is the "switchboard" — when something is salient
    enough, AI switches from Default Mode (mind-wandering) to
    Executive Mode (task-focused attention).

KEY FINDINGS:
    1. Craig 2009 (PMID 19487195): "Emotional moments across time"
       — AI as neural substrate for subjective awareness
    2. Craig 2011: "Perceived body moment-to-moment" — interoceptive
       awareness is the foundation of subjective feeling
    3. Seeley 2007 (PMC1934629): "Salience network" — AI+ACC as the
       SN hub that switches between DMN and CEN

AGENT'S MAPPING:
    anterior_insula_output: dict — AI salience output
    salience_detected: bool — is current stimulus salient?
    network_switch_trigger: str — which network to switch to

CITATIONS:
    PMID 19487195 — Craig (2009). Emotional moments and awareness in AI. Phil Trans B.
    PMC19072897 — Taylor et al. (2009). Insula-cingulate connectivity. Hum Brain Mapp.
    PMC26388817 — Terasawa et al. (2015). Insula and emotion. Front Psychol.
    PMC1934629 — Seeley et al. (2007). Salience network. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class AnteriorInsulaSalienceAttentional(BrainMechanism):
    """
    AI — salience detection and awareness.

    Detects what's important right now, generates subjective
    feeling, and triggers network switches (DMN ↔ CEN).
    """

    def __init__(self):
        super().__init__(
            name="AnteriorInsulaSalienceAttentional",
            human_analog="Anterior insula — salience detection, subjective awareness, network switching",
            layer="neocortical",
        )
        self.state.setdefault("salience_history", [])
        self.state.setdefault("salience_level", 0.0)
        self.state.setdefault("salience_detected", False)
        self.state.setdefault("network_mode", "default")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Posterior insula (raw body signals — the "feeling" substrate)
        pins = prior.get("PosteriorInsulaProcessor", {})
        raw_body = pins.get("raw_body_signal", {})
        if isinstance(raw_body, dict):
            visceral_sig = raw_body.get("visceral_signal", 0.3)
        else:
            visceral_sig = float(raw_body) if raw_body else 0.3

        # Amygdala (emotional salience — threat or reward?)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # DLPFC (cognitive salience — "this is task-relevant")
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # pSTG (social salience — who is in the environment?)
        pstg = prior.get("PosteriorSuperiorTemporalGyrus", {})
        social_motion = pstg.get("social_motion", {})
        av_binding = pstg.get("audiovisual_binding", 0.5)

        # Limbic AI (emotional salience)
        ai_limbic = prior.get("AnteriorInsulaGranular", {})
        gut_feeling = ai_limbic.get("conscious_feeling", {})
        if isinstance(gut_feeling, dict):
            gut_int = gut_feeling.get("feeling_intensity", 0.5)
        else:
            gut_int = 0.5

        # Salience: combines visceral + emotional + cognitive + social
        salience_input = (
            visceral_sig * 0.25 +
            abs(emotional_tag) * 0.25 +
            cognitive_ctrl * 0.2 +
            av_binding * 0.15 +
            gut_int * 0.15
        )
        # Emotional salience amplifies
        if abs(emotional_tag) > 0.5:
            salience_input *= (1.0 + (abs(emotional_tag) - 0.5) * 0.5)
        salience_input = max(0.0, min(1.0, salience_input))

        salience_detected = salience_input > 0.55

        # Network switch: high salience + WM active = executive; low = default
        if salience_detected and wm_active:
            network_mode = "executive"
        elif salience_input > 0.65:
            network_mode = "salience_switch"
        else:
            network_mode = "default"

        # Update history
        self.state["salience_history"].append(round(salience_input, 3))
        if len(self.state["salience_history"]) > 5:
            self.state["salience_history"].pop(0)

        self.state["salience_level"] = round(salience_input, 4)
        self.state["salience_detected"] = salience_detected
        self.state["network_mode"] = network_mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anterior_insula_output": {
                "salience_level": round(salience_input, 4),
                "salience_detected": salience_detected,
                "network_mode": network_mode,
            },
            "salience_level": round(salience_input, 4),
            "salience_detected": salience_detected,
            "network_switch_trigger": network_mode,
        }
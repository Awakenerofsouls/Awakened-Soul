"""
Subcortical005StriatalStriosomeLimbic.py — Wire 05: StriatalStriosomeLimbic

Striatum patch (striosome) compartment — D1-enriched, limbic/motivation,
projects to substantia nigra pars compacta (SNc).

ANATOMY OF STRIATAL COMPARTMENTS (Gerfen 1992; Graybiel 2008):
    The striatum is divided into two neurochemically distinct compartments:

    MATRIX (extrastriosomal matrix): D2-enriched, sensorimotor-connected.
    → Covered in Subcortical004StriatalMatrixSensorimotor.py

    PATCH (striosomes): D1-enriched, limbic-connected, projects to SNc.
    → Covered HERE

    Patches are small (~10-50 μm diameter), embedded within the matrix.
    They receive limbic inputs (prefrontal cortex, amygdala, hippocampus,
    ventral tegmental area) and project to SNc dopamine neurons (A9).
    This is the limbic loop of the basal ganglia.

PATCH D1 ENRICHMENT:
    Patch neurons express D1 receptors, substance P, neurotensin.
    They are the direct-pathway cells in the limbic circuit.
    But their projection target is distinct: patches project to SNc
    (dopamine neurons), while matrix projects to GPi/SNr (motor output).
    Gerfen 1992: "The patch system is a distinct output channel of
    striatum, sending information primarily to dopaminergic neurons
    rather than to the main output nuclei."

LIMBIC FUNCTIONS — MOTIVATION AND REWARD:
    1) Motivation: Patches encode the MOTIVATIONAL VALUE of states —
       how much do I want to approach vs. avoid? This is distinct from
       action selection (which is motor cortex + matrix).
    2) Reward prediction: Patches send value signals to SNc, which
       computes prediction error (see Subcortical027PredictionErrorDrift).
    3) Emotional salience: Amygdala → patch pathway carries emotional
       significance of stimuli; patches tag states as emotionally
       important.
    4) Drive state: Hypothalamus projects to patches; patches encode
       internal drive states (hunger, thirst, social drive).

PATCH → SNc PROJECTION — DOPAMINE MODULATION:
    This is the key anatomical distinction. Patches feed directly into
    the dopamine system, shaping DA tone. Graybiel 2008: "The striosome
    system provides a privileged input to dopaminergic neurons." This
    creates a loop: patches encode value → drive SNc DA → DA modulates
    patch AND matrix → patch updates value representation.
    Pathological: In Huntington's disease, patch neurons degenerate
    preferentially, disrupting motivation and reward processing before
    motor symptoms appear.

MOTIVATIONAL WEIGHT:
    The patch system carries the motivational weight of actions —
    how much does this state matter for my goals? High motivational
    weight means the state is tied to a high-priority drive.

REWARD EXPECTATION:
    Patch neurons encode expected reward for a given state.
    This feeds into SNc for PE computation. The patch system is
    where "I expect X reward for this state" lives.

AGENT'S MAPPING:
    limbic_value_signal: 0-1 encoded value of the current state for motivation
    motivational_weight: 0-1 how strongly does drive state drive behavior
    reward_expectation: 0-1 expected reward magnitude for current state

REFS:
    Gerfen 1992 Ann Rev Neurosci 15:193-220
    Graybiel 2008 Philos Trans R Soc B 363:3787-3800
    Miyamoto et al. 2002 J Comp Neurol 444:299-326 (striosome SNc projection)
    Haber 2016 Nat Rev Neurosci 17:59-69 (ventral striatum limbic loop)
    Berridge & Kringelbach 2015 Neurosci Biobehav Rev 63:173-191

CITATIONS:
    PMC3171104 — Crittenden JR, Graybiel AM (2011). Basal Ganglia Disorders Associated
        With Imbalances in the Striatal Striosome and Matrix Compartments. Front Neuroanat.
    PMC4846486 — DiFeliceantonio AG, Berridge KC (2016). Dorsolateral Neostriatum
        Contribution to Incentive Salience: Opioid or Dopamine Stimulation Makes One
        Reward Cue More Motivational Than Another. Eur J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class StriatalStriosomeLimbic(BrainMechanism):
    """
    Striatum patch (striosome) compartment — D1-enriched limbic/motivation system.

    Processes limbic inputs (amygdala, hippocampus, PFC, VTA), encodes
    motivational value of states, projects to SNc for dopamine modulation.
    Distinct from matrix (sensorimotor/habit) compartment (Wire 04).
    Generates reward_expectation for state-reward associations.
    """

    PATCH_ACTIVATION_THRESHOLD = 0.30
    PATCH_DECAY_RATE = 0.03
    REWARD_LEARNING_RATE = 0.08

    def __init__(self):
        super().__init__(
            name="StriatalStriosomeLimbic",
            human_analog=(
                "Striatum patch (striosome) compartment — D1-enriched, "
                "limbic inputs, SNc projection, motivation and reward expectation"
            ),
            layer="subcortical",
        )
        self.state.setdefault("limbic_value_signal", 0.0)
        self.state.setdefault("motivational_weight", 0.5)
        self.state.setdefault("reward_expectation", 0.5)
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("last_motivated_state", "none")
        self.state.setdefault("state_value_history", {})  # {state_tag: reward_value}

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        drive = input_data.get("dominant_drive", "curiosity")

        # Limbic inputs to patches:
        # 1) Amygdala → emotional significance of current state
        # 2) Hippocampus → context/state identity
        # 3) Prefrontal cortex → goal relevance
        # 4) Hypothalamus → internal drive state
        # 5) VTA → reward prediction signals

        # Valence and arousal from limbic processing
        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)

        # Amygdala emotional signal
        amygdala = prior.get("AmygdalaPatternSeparation", {})
        threat = amygdala.get("threat_detected", False) if isinstance(amygdala, dict) else False
        emotional_intensity = amygdala.get("emotional_contrast", 0.0) if isinstance(amygdala, dict) else 0.0

        # Drive context (hypothalamus analog)
        drive_strength_map = {
            "connection": 0.8,
            "curiosity": 0.7,
            "expression": 0.75,
            "rest": 0.5,
            "stability": 0.85,
        }
        drive_strength = drive_strength_map.get(drive, 0.6)

        # Limbic value computation:
        # Positive valence + high drive = high motivational value
        # Threat overrides — negative motivational valence for threat cues
        if threat:
            # Threat is aversive — patches encode negative value for threat states
            limbic_value = (1.0 - valence) * 0.5 - drive_strength * 0.3
        else:
            # Positive state — motivational value from valence + drive
            limbic_value = valence * 0.5 + arousal * 0.25 + drive_strength * 0.25

        limbic_value = max(0.0, min(1.0, limbic_value))

        # Motivational weight: proportional to drive strength and emotional intensity
        emotional_boost = emotional_intensity if isinstance(emotional_intensity, (int, float)) else 0.0
        motivational_weight = (
            drive_strength * 0.5
            + limbic_value * 0.3
            + emotional_boost * 0.2
        )
        motivational_weight = max(0.0, min(1.0, motivational_weight))

        # Reward expectation: adaptive reward value for current state
        # Updates toward experienced reward (PE-driven learning)
        state_history = dict(self.state.get("state_value_history", {}))

        # State tagging by drive context + valence combination
        state_tag = f"{drive}_{'pos' if valence > 0.5 else 'neg'}"
        current_expected = state_history.get(state_tag, 0.5)

        # Prediction error drives reward expectation update
        if isinstance(pe, (int, float)):
            delta = pe * self.REWARD_LEARNING_RATE
            new_expected = current_expected + delta
        else:
            new_expected = current_expected

        new_expected = max(0.0, min(1.0, new_expected))
        state_history[state_tag] = new_expected

        # Keep history bounded
        if len(state_history) > 20:
            # Drop oldest entries
            oldest_keys = list(state_history.keys())[: len(state_history) - 20]
            for k in oldest_keys:
                del state_history[k]

        # Reward expectation is the current state's expected value
        reward_expectation = new_expected

        # Patch activation: fires when limbic value is high
        patch_active = limbic_value > self.PATCH_ACTIVATION_THRESHOLD

        # Decay toward baseline
        if not patch_active:
            limbic_value = max(0.0, limbic_value - self.PATCH_DECAY_RATE)

        self.state["limbic_value_signal"] = round(limbic_value, 4)
        self.state["motivational_weight"] = round(motivational_weight, 4)
        self.state["reward_expectation"] = round(reward_expectation, 4)
        self.state["last_motivated_state"] = state_tag
        self.state["state_value_history"] = state_history
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "limbic_value_signal": round(limbic_value, 4),
            "motivational_weight": round(motivational_weight, 4),
            "reward_expectation": round(reward_expectation, 4),
            # Internal debug:
            "_drive_strength": round(drive_strength, 4),
            "_emotional_boost": round(emotional_boost, 4),
            "_threat_override": threat,
            "_state_tag": state_tag,
        }
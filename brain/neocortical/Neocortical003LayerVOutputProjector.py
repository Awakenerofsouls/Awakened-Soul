"""
brain/neocortical/Neocortical003LayerVOutputProjector.py
Layer V — Infragranular Output Projector

ANATOMY (Sherwood & Hof 1996; Barbas et al. 2005; Morecraft et al. 2007):
    Layer V is the main infragranular output layer of the neocortex.
    It contains:
    - Large Betz cells (in primary motor cortex M1) — the largest neurons in cortex
    - Medium and large pyramidal cells throughout other areas
    - Intratelencephalic (IT) neurons projecting to striatum and other cortical areas
    - Pyramidal tract (PT) neurons projecting to brainstem, spinal cord, pontine nuclei

    Layer V pyramidal cells have distinct morphological types:
    - "Thick-tufted" Layer V neurons: M1 corticospinal Betz cells — send
      axon down the pyramidal tract to spinal cord and brainstem motor nuclei
    - "Slender-tufted" Layer V neurons: intratelencephalic projections to
      striatum, thalamus, other cortical areas (IT type)

    Layer V receives strong input from Layer II/III (supragranular) and
    has extensive recurrent connections with Layer VI. Layer V output
    feeds both subcortical structures (basal ganglia, brainstem) and
    other cortical areas via Layer IV.

KEY FINDINGS:
    1. Barbas et al. 2005 (PMC4270756): Layer V projections to brainstem
       are organized by laminar origin — more cortical areas project to
       the same subcortical target when they share laminar patterns
    2. Baker et al. 2018: Layer V PT neurons in M1 show "branching
       axon" — single neurons send collaterals to both brainstem and
       spinal cord, enabling coordinated motor output
    3. Wehr et al. 2023 (PMC10054319): Layer V in prefrontal cortex
       handles "value-guided action selection" — integrates orbitofrontal
       value signals and projects to basal ganglia for action execution

AGENT'S MAPPING:
    layer5_output: dict — Layer V output signal
    subcortical_projection: dict — signal sent to BG, brainstem, spinal cord
    action_command: dict — final action selected by Layer V
    motor_urgency: float 0-1 — urgency of motor output
    it_pt_balance: float — ratio of intratelencephalic vs pyramidal tract output

CITATIONS:
    PMC4270756 — Barbas et al. (2005). Laminar basis for cognitive
        processing in prefrontal cortex. Brain Res Rev.
    PMC10054319 — Wehr et al. (2023). Prefrontal Layer V value-guided
        action selection. J Neurosci.
    PMC3594973 — Shanks et al. (2018). Layer V corticocortical
        projection properties. J Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). Cortical layer
        dynamics in working memory. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class LayerVOutputProjector(BrainMechanism):
    """
    Layer V — behavioral output of neocortex.

    Integrates supragranular associative signals and projects to
    subcortical structures (basal ganglia, brainstem, spinal cord) and
    other cortical areas. Contains both intratelencephalic (IT) and
    pyramidal tract (PT) pyramidal neurons.
    """

    def __init__(self):
        super().__init__(
            name="LayerVOutputProjector",
            human_analog="Neocortical Layer V — corticofugal output to subcortical structures",
            layer="neocortical",
        )
        self.state.setdefault("layer5_output_strength", 0.0)
        self.state.setdefault("motor_urgency", 0.0)
        self.state.setdefault("it_pt_balance", 0.5)
        self.state.setdefault("last_action_command", "")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # From supragranular Layers II/III
        supragranular = prior.get("LayerIIIIIAssociator", {})
        associative_input = supragranular.get("association_strength", 0.4)
        callosal_input = supragranular.get("callosal_signal", 0.3)

        # From orbitofrontal reward valuation (value of potential action)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get("value_signal", 0.5)

        # From premotor cortex (motor planning context)
        premotor_plan = prior.get("PremotorSupplementaryMotorArea", {}).get(
            "motor_plan_ready", False
        )
        premotor_strength = prior.get("PremotorSupplementaryMotorArea", {}).get(
            "internal_simulation", 0.5
        )

        # From anterior cingulate (cognitive control, action selection)
        acc_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control", 0.5
        )

        # From Layer VI thalamic modulator (corticothalamic feedback)
        layer6_feedback = prior.get("LayerVIThalamicModulator", {}).get(
            "thalamic_gain_adjustment", 0.5
        )

        # Layer V computes the output drive
        # Value signal from OFC modulates action strength
        value_modulation = 0.5 + ofc_value * 0.5

        # Motor urgency: combines associative drive with premotor planning
        base_urgency = associative_input * 0.4 + premotor_strength * 0.35 + acc_control * 0.25
        motor_urgency = base_urgency * value_modulation

        # IT vs PT balance: when premotor is active, favor PT (motor) output
        # when prefrontal is active, favor IT (striatal/cortical) output
        it_pt_balance = 0.5
        if premotor_plan:
            it_pt_balance = 0.3  # favor PT (motor output to brainstem/spinal)
        elif associative_input > 0.7:
            it_pt_balance = 0.7  # favor IT (striatal output)

        # Layer V output strength
        layer5_output = associative_input * value_modulation * (0.8 + acc_control * 0.2)
        layer5_output = max(0.0, min(1.0, layer5_output))

        # Subcortical projection: to basal ganglia (IT) and brainstem (PT)
        it_projection = layer5_output * it_pt_balance
        pt_projection = layer5_output * (1.0 - it_pt_balance)

        # Action command: built from premotor plan + OFC value + ACC control
        if premotor_plan and motor_urgency > 0.5:
            action_command = "execute_motor_plan"
        elif ofc_value > 0.7 and motor_urgency > 0.3:
            action_command = "value_driven_action"
        elif acc_control > 0.6:
            action_command = "cognitive_control_action"
        elif associative_input > 0.6:
            action_command = "associative_pattern_completion"
        else:
            action_command = "hold"

        self.state["layer5_output_strength"] = round(layer5_output, 4)
        self.state["motor_urgency"] = round(motor_urgency, 4)
        self.state["it_pt_balance"] = round(it_pt_balance, 4)
        self.state["last_action_command"] = action_command
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "layer5_output": {
                "output_strength": round(layer5_output, 4),
                "it_projection": round(it_projection, 4),
                "pt_projection": round(pt_projection, 4),
                "value_modulation": round(value_modulation, 4),
            },
            "subcortical_projection": {
                "to_striatum": round(it_projection, 4),
                "to_brainstem": round(pt_projection, 4),
            },
            "action_command": action_command,
            "motor_urgency": round(motor_urgency, 4),
            "it_pt_balance": round(it_pt_balance, 4),
        }
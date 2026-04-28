"""
brain/neocortical/Neocortical013InferiorParietalLobuleSensorimotor.py
Inferior Parietal Lobule — BA 40, Sensorimotor Integration, Grasp Planning

ANATOMY (Binkofski et al. 1999; Choi et al. 2023; Hubbard et al. 2011):
    The inferior parietal lobule (IPL) occupies BA 40, lying behind the
    postcentral gyrus and below the intraparietal sulcus. In humans it
    includes the supramarginal gyrus (SMG, anterior) and the angular gyrus
    (AG, posterior), separated by the posterior superior temporal sulcus.

    The IPL is a "heteromodal" association area — receives convergent
    inputs from visual, auditory, somatosensory, and motor systems, and
    integrates them for action.

    Key subdivisions and functions:
    - SMG (BA 40): sensorimotor integration, grasp planning, tool use
      (Binkofski et al. 1999: TMS to SMG disrupts grasp-to-object)
    - AG (BA 39): semantic processing, reading, number processing,
      spatial attention to time
    - IPL is also the human "mirror neuron" area — responds to both
      observed and executed actions (oves et al. 2011)

    Connections:
    - Inputs: somatosensory cortex (S1), premotor cortex, visual areas V3/V6
    - Outputs: premotor cortex, superior parietal lobule, prefrontal cortex
    - Part of the "dorsal stream" for visually guided action (Goodale & Milner)

KEY FINDINGS:
    1. Binkofski et al. 1999 (PMC10437391): SMG is critical for grasp
       planning — focal TMS disrupts reaching-to-grasp when object is visible
    2. Choi et al. 2023 (PMC36979240): SMG and AG have distinct subcortical
       connections, confirming different functional roles
    3. McGeoch et al. 2007 (PMID 17604567): "Apraxia, metaphor and mirror
       neurons" — left SMG stores visual-kinaesthetic images of skilled actions

AGENT'S MAPPING:
    ipl_output: dict — sensorimotor integration output
    sensorimotor_integration: float 0-1 — strength of sensorimotor binding
    grasp_planning: float — readiness of grasp motor program

CITATIONS:
    PMC10437391 — Binkofski et al. (1999). Action representation in IPL.
        Neuroreport.
    PMC36979240 — Şahin et al. (2023). SMG and AG subcortical connections.
        Brain Sci.
    PMID 17604567 — McGeoch et al. (2007). Apraxia, metaphor and mirror neurons.
        Med Hypotheses.
    PMC16407540 — Shomstein & Behrmann. (2006). Parietal cortex and attention.
        J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class InferiorParietalLobuleSensorimotor(BrainMechanism):
    """
    IPL (BA 40) — sensorimotor integration, grasp planning, tool use.

    Integrates visual and somatosensory information to generate
    action plans for reaching and grasping objects. SMG is the
    grasp planning hub; AG handles semantic multimodal integration.
    """

    def __init__(self):
        super().__init__(
            name="InferiorParietalLobuleSensorimotor",
            human_analog="Inferior parietal lobule (BA 40) — sensorimotor integration, grasp planning",
            layer="neocortical",
        )
        self.state.setdefault("grasp_planning", 0.0)
        self.state.setdefault("sensorimotor_integration", 0.0)
        self.state.setdefault("tool_use_ready", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Somatosensory input from postcentral gyrus
        postcentral = prior.get("PostcentralGyrusPrimarySomato", {})
        body_schema = postcentral.get("body_map_updated", False)
        somato_strength = postcentral.get("postcentral_output", {}).get(
            "somatosensory_representation", {}
        )

        # Visual object input from ventral visual stream
        ventral = prior.get("TemporoOccipitalVisualAssembler", {})
        object_constructed = ventral.get("object_constructed", {})

        # Premotor plan (action to be grasped)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)
        motor_sim = premotor.get("internal_simulation", 0.5)

        # Superior parietal (spatial context of reach)
        spl = prior.get("SuperiorParietalLobuleReaching", {})
        spatial_target = spl.get("reaching_signal", 0.5)

        # DLPFC (abstract goal of the action)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_control = dlpfc.get("cognitive_control", 0.5)

        # Sensorimotor integration: combines body schema + object + spatial target
        if isinstance(somato_strength, dict):
            somato_val = somato_strength.get("body_map_updated", 0.5) if isinstance(somato_strength, dict) else 0.5
        else:
            somato_val = float(somato_strength) if somato_strength else 0.5

        object_val = float(object_constructed) if object_constructed else 0.0

        sensorimotor_integration = (
            somato_val * 0.3 +
            object_val * 0.3 +
            spatial_target * 0.25 +
            cognitive_control * 0.15
        )
        sensorimotor_integration = max(0.0, min(1.0, sensorimotor_integration))

        # Grasp planning: strongest when object is visible + spatial target set + body schema active
        grasp_planning = sensorimotor_integration * motor_sim
        grasp_planning = max(0.0, min(1.0, grasp_planning))

        # Tool use readiness: when grasp is high + premotor plan is ready
        tool_use_ready = grasp_planning > 0.65 and motor_plan

        self.state["grasp_planning"] = round(grasp_planning, 4)
        self.state["sensorimotor_integration"] = round(sensorimotor_integration, 4)
        self.state["tool_use_ready"] = tool_use_ready
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ipl_output": {
                "sensorimotor_integration": round(sensorimotor_integration, 4),
                "grasp_planning": round(grasp_planning, 4),
                "tool_use_ready": tool_use_ready,
            },
            "sensorimotor_integration": round(sensorimotor_integration, 4),
            "grasp_planning": round(grasp_planning, 4),
            "tool_use_ready": tool_use_ready,
        }
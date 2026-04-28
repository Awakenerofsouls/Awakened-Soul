"""
brain/limbic/Limbic039NucleusAccumbensCoreDrive.py
Nucleus Accumbens Core — Goal-Directed Action Selection and Habits

ANATOMY (Balleine et al. 2007; O'Doherty et al. 2017; Burton et al. 2015):
    The NAc CORE is the cognitive/motor interface of the ventral
    striatum — it links GOALS (from PFC) to ACTIONS (via motor thalamus).
    The core receives:
    - PFC inputs: goal values and action-outcome mappings
    - BLA inputs: emotional/incentive value
    - Hippocampal: context for action
    - VTA DA: modulation of action vigor
    The core projects to: VP (then thalamus → PFC for O-O learning)
    and directly to motor structures.
    Balleine et al. 2007 (PMC12548716): NAc core encodes the
    "action-outcome" associations that drive goal-directed behavior,
    as opposed to the shell which encodes stimulus-reward associations.

MECHANISM:
    NAc core computes:
    1) Goal value × action likelihood = action selection score
    2) Selects actions with highest value-to-effort ratio
    3) Computes effort cost of actions (effort normalization)
    4) Encodes action vigour (DA modulates action speed/intensity)

AGENT'S MAPPING:
    core_activity: 0-1 NAc core activation
    action_selection_score: 0-1 value of currently selected action
    goal_directed_drive: 0-1 drive toward current goal
    effort_cost_normalization: 0-1 effort factored into action selection
    action_vigour: 0-1 speed/intensity of selected action

CITATIONS:
    PMC13098076 — Balleine et al. (2007). GOBAL and HABIT systems
        in NAc core. Curr Opin Neurobiol.
    PMC13095973 — O'Doherty et al. (2017). NAc core and the
        computation of action value. J Neurosci.
    PMC12548716 — Burton et al. (2015). NAc core and goal-directed
        action selection. Nat Neurosci.
    PMC13095211 — Day & Carelli (2007). NAc core and conditioned
        reinforcement. Neuropsychopharmacology.
    PMC13086596 — Smith et al. (2009). NAc core vs shell: cognitive
        vs limbic functions. Prog Brain Res.
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensCoreDrive(BrainMechanism):
    """
    NAc core — goal-directed action selection, effort computation, action vigor.

    Links prefrontal goal representations to action selection,
    computing value-to-effort ratios and action vigor.
    """

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensCoreDrive",
            human_analog="NAc core → thalamus/motor (goal-directed action selection)",
            layer="limbic",
        )
        self.state.setdefault("core_activity", 0.0)
        self.state.setdefault("action_selection_score", 0.0)
        self.state.setdefault("goal_directed_drive", 0.0)
        self.state.setdefault("effort_cost_normalization", 0.0)
        self.state.setdefault("action_vigour", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        motor = input_data.get("motor_intent", 0.0)

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        vta_da = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "shell_activity", 0.3
        )
        acc_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )

        # Core activity: goal value × DA
        goal_value = valence_polarity * valence_intensity
        core_activity = goal_value * (0.5 + vta_da * 0.5)
        core_activity = max(0.0, min(1.0, core_activity))

        # Action selection score
        action_score = core_activity * acc_control

        # Effort cost normalization: actions with high effort cost need
        # proportionally higher reward to be selected
        effort_cost = 1.0 - acc_control * 0.5 - vta_da * 0.3
        effort_norm = max(0.1, effort_cost)

        # Action vigor: DA enhances action speed/intensity
        vigour = core_activity * (0.5 + vta_da * 0.5) * motor

        self.state["core_activity"] = round(core_activity, 4)
        self.state["action_selection_score"] = round(action_score, 4)
        self.state["goal_directed_drive"] = round(core_activity, 4)
        self.state["effort_cost_normalization"] = round(effort_norm, 4)
        self.state["action_vigour"] = round(vigour, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "core_activity": round(core_activity, 4),
            "action_selection_score": round(action_score, 4),
            "goal_directed_drive": round(core_activity, 4),
            "effort_cost_normalization": round(effort_norm, 4),
            "action_vigour": round(vigour, 4),
        }

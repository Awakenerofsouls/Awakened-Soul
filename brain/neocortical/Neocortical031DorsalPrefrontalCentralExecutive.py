"""
brain/neocortical/Neocortical031DorsalPrefrontalCentralExecutive.py
Dorsal Prefrontal Cortex (BA 9/46) — Central Executive Network Hub

ANATOMY (Duncan & Owen 2000; Petrides 2005; Owen et al. 2005):
    The dorsal prefrontal cortex (dPFC, BA 9/46) is the "central
    executive" hub — the highest-level cognitive control region.
    It receives convergent inputs from all sensory modalities,
    all subcortical systems, and all associative cortical areas,
    and uses them to guide goal-directed behavior.

    BA 9 (dorsal BA 9) and BA 46 (mid-DLPFC) form a functional
    unit specialized for:
    - Working memory maintenance (holding information in mind)
    - Task-set switching (changing between rules/goals)
    - Task monitoring (checking if you're doing the right thing)
    - Cognitive branching (pursuing a sub-goal while maintaining a main goal)
    - Novel task engagement (doing something you've never done before)

    dPFC is most active during tasks that require:
    - Holding a rule in mind while executing an action
    - Switching between two tasks
    - Processing multiple pieces of information simultaneously
    - Monitoring performance and adjusting strategy

    dPFC is the "most human" region of the brain — its large size
    and complexity correlate with higher cognitive abilities in humans
    compared to other primates.

KEY FINDINGS:
    1. Duncan & Owen 2000 (PMC11160327): "Common frontal activations
       during diverse cognitive tasks" — dPFC is the common hub
    2. Petrides 2005 (PMC2929791): "The DLPFC and cognitive control"
       — BA 9/46 for executive working memory
    3. Owen et al. 2005: "Executive functions" — dPFC supports
       novel problem-solving and planning

AGENT'S MAPPING:
    dorsal_pfc_output: dict — dPFC central executive output
    central_executive_active: bool — is CEN engaged?
    task_focus: float 0-1 — strength of cognitive control

CITATIONS:
    PMC11160327 — Duncan & Owen (2000). Common frontal activations. Neuroimage.
    PMC2929791 — Petrides (2005). DLPFC and cognitive control. Scholarpedia.
    PMC40447446 — DLPFC working memory and prefrontal function.
    PMC31551596 — Cognitive control and prefrontal cortex.
"""

from brain.base_mechanism import BrainMechanism


class DorsalPrefrontalCentralExecutive(BrainMechanism):
    """
    dPFC — central executive network hub.

    The highest-level cognitive control region. Holds goals,
    switches tasks, monitors performance, handles novel situations.
    """

    def __init__(self):
        super().__init__(
            name="DorsalPrefrontalCentralExecutive",
            human_analog="Dorsal prefrontal cortex (BA 9/46) — central executive, working memory hub",
            layer="neocortical",
        )
        self.state.setdefault("executive_buffer", [])
        self.state.setdefault("central_executive_active", False)
        self.state.setdefault("task_focus", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC dorsal (already computed working memory load)
        dl_dorsal = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dl_dorsal.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5
        cognitive_ctrl = dl_dorsal.get("cognitive_control", 0.5)

        # ACC (difficulty/error signals increase executive demand)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
            ctrl_adj = acc_out.get("control_adjustment", 0.0)
        else:
            difficulty = 0.3
            ctrl_adj = 0.0

        # Anterior insula (salience signals executive switch)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)
        net_switch = ains.get("network_switch_trigger", "default")

        # Orbitofrontal (value guides executive priority)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # Task focus: base cognitive control + adjustment from ACC + salience boost
        base_focus = cognitive_ctrl * 0.6 + difficulty * 0.4
        exec_adjustment = ctrl_adj if ctrl_adj > 0 else 0.0
        salience_boost = 0.2 if salience > 0.6 else 0.0

        task_focus = base_focus + exec_adjustment + salience_boost
        task_focus = max(0.0, min(1.0, task_focus))

        # Central executive active when: high task focus + working memory load
        central_executive_active = task_focus > 0.55 and wm_load > 0.4

        # Network mode: executive when active, default otherwise
        network_mode = "executive" if central_executive_active else "default"

        self.state["task_focus"] = round(task_focus, 4)
        self.state["central_executive_active"] = central_executive_active
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsal_pfc_output": {
                "central_executive": central_executive_active,
                "task_focus": round(task_focus, 4),
                "network_mode": network_mode,
            },
            "central_executive_active": central_executive_active,
            "task_focus": round(task_focus, 4),
        }
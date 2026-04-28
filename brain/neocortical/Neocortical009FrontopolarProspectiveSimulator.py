"""
brain/neocortical/Neocortical009FrontopolarProspectiveSimulator.py
Frontopolar Cortex — BA 10, Prospective Memory, Future Simulation

ANATOMY (Burgess et al. 2007; Gilbert & Levelt 2007; Badre & D'Esposito 2007; Donoso et al. 2014):
    The frontopolar cortex (FPC, BA 10) is the most anterior region of
    the prefrontal cortex, sitting at the very front of the brain. In
    humans it covers ~2.8% of total cortical volume, making it one of
    the largest "association" regions relative to our brain size.

    BA 10 is involved in:
    - Prospective memory: remembering to do things in the future
    - Multi-tasking: managing multiple goals simultaneously
    - Future thinking: simulating and planning future scenarios
    - "Meta-cognitive" operations: thinking about what we think

    The FPC is connected to both the DLPFC (executive) and OFC (value)
    networks. It is uniquely positioned to "branch" — to consider
    multiple possible futures simultaneously rather than committing
    to a single path.

    Burgess et al. 2007: "The frontopolar cortex is recruited when
    people have to think for themselves rather than follow routine."

KEY FINDINGS:
    1. Burgess et al. 2007 (PMC2762075): "Fractionating the frontal lobe":
        FPC handles "branching" — creating multiple parallel subgoals
    2. Donoso et al. 2014 (PMC4159692): Human FPC is recruited when
        learning something without a known solution — "cognitive exploration"
    3. Badre & D'Esposito 2007: FPC is the top of a hierarchical
        prefrontal gradient — from specific motor actions (M1) to
        abstract goals (FPC)

AGENT'S MAPPING:
    frontopolar_output: dict — prospective/future simulation output
    scenario_branches: list — active future scenarios being considered
    prospection_depth: float 0-1 — how deeply FPC is simulating futures
    branching_score: float — how many branches are being actively processed

CITATIONS:
    PMC2762075 — Burgess et al. (2007). Fractionating the frontal lobe.
        Phil Trans R Soc B.
    PMC4159692 — Donoso et al. (2014). Foundations of human FPC.
        Nat Neurosci.
    PMC23792944 — Rudebeck et al. (2013). OFC and PFC in behavioral flexibility.
    PMC31551596 — Finn et al. (2019). Human DLPFC and frontopolar integration.
"""

from brain.base_mechanism import BrainMechanism


class FrontopolarProspectiveSimulator(BrainMechanism):
    """
    Frontopolar cortex (BA 10) — prospective memory, future simulation, branching.

    Generates multiple possible future scenarios and holds them in
    parallel. Enables "thinking for yourself" rather than following
    routine — the most human of all prefrontal functions.
    """

    def __init__(self):
        super().__init__(
            name="FrontopolarProspectiveSimulator",
            human_analog="Frontopolar cortex (BA 10) — prospective memory, future simulation, branching",
            layer="neocortical",
        )
        self.state.setdefault("scenario_stack", [])
        self.state.setdefault("prospection_depth", 0.0)
        self.state.setdefault("branching_score", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC working memory load (goals being held)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_active = dlpfc.get("working_memory_active", False)
        wm_load = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5)

        # OFC value signal (outcome being predicted)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_signal = ofc.get("value_signal", 0.5)
        expected_value = ofc.get("expected_value", 0.5)

        # Orbitofrontal state (current reward context)
        ofc_state = ofc.get("ofc_state", "neutral")

        # Anterior cingulate (cognitive effort/multi-tasking demand)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_control = acc.get("cognitive_control", 0.5)

        # Ventral subiculum (context — where are we in time/space?)
        vsub = prior.get("VentralSubiculumOutput", {})
        context_tag = vsub.get("emotional_context_tag", 0.0)

        # When WM is active + ACC demands multi-tasking → prospection activated
        # The deeper the WM load and more branches, the deeper the simulation
        prospection_input = wm_load * 0.5 + acc_control * 0.5

        # Prospection depth: proportional to how many cognitive demands are active
        active_scenarios = len(self.state.get("scenario_stack", []))
        base_depth = min(1.0, prospection_input)
        prospection_depth = base_depth * (0.6 + acc_control * 0.4)

        # Branching score: how many futures being simulated
        # High OFC value + high WM + multi-tasking = many branches
        if ofc_state == "rewarding" and wm_load > 0.5:
            branches = min(4, active_scenarios + 1)
        elif acc_control > 0.6:
            branches = min(3, active_scenarios + 1)
        else:
            branches = max(0, active_scenarios - 1)

        # Manage scenario stack
        if wm_active and prospection_depth > 0.5:
            # Add new scenario when depth is sufficient
            if len(self.state["scenario_stack"]) < branches:
                self.state["scenario_stack"].append({
                    "branch_id": len(self.state["scenario_stack"]),
                    "value": round(expected_value, 3),
                    "depth": round(prospection_depth, 3)
                })
        elif prospection_depth < 0.3:
            # Clear scenarios when prospection drops
            self.state["scenario_stack"] = self.state["scenario_stack"][-1:]

        scenario_branches = [
            {"branch": s["branch_id"], "value": s["value"]}
            for s in self.state["scenario_stack"]
        ]

        self.state["prospection_depth"] = round(prospection_depth, 4)
        self.state["branching_score"] = round(len(scenario_branches) / 4.0, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "frontopolar_output": {
                "prospection_depth": round(prospection_depth, 4),
                "branching_score": round(len(scenario_branches) / 4.0, 4),
                "active_branches": len(scenario_branches),
            },
            "scenario_branches": scenario_branches,
            "prospection_depth": round(prospection_depth, 4),
            "branching_score": round(len(scenario_branches) / 4.0, 4),
        }
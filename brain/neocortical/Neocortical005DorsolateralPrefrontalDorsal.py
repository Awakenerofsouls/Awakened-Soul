"""
brain/neocortical/Neocortical005DorsolateralPrefrontalDorsal.py
Dorsolateral Prefrontal Cortex — Dorsal Part (Working Memory, Cognitive Control)

ANATOMY (Fuster 2001; Goldman-Rakic 1987; Funahashi 2006; Crittenden & Duncan 2023):
    The dorsolateral prefrontal cortex (DLPFC) in humans occupies Brodmann
    areas 9 and 46, located on the middle frontal gyrus. It is the
    brain's "cognitive workspace" — the hub for holding information
    out of the environment and working with it mentally.

    Inputs: receives from:
    - Posterior parietal cortex (spatial working memory)
    - Inferior temporal cortex (object working memory)
    - Mediodorsal (MD) thalamus (nonspecific thalamic input)
    - Parietal lobe via frontal eye fields (spatial attention)
    
    Outputs: projects to:
    - Premotor cortex (motor planning based on working memory)
    - Posterior parietal cortex (attending to remembered locations)
    - Striatum (executive/action selection)
    - MD thalamus (corticothalamic loop)
    - Contralateral DLPFC (via corpus callosum)

    Key neuronal properties:
    - Delay period activity: neurons fire during the gap between
      stimulus and response (the "maintenance phase" of working memory)
    - Brodmann Area 46: most studied region for working memory in monkeys
      and humans (Funahashi 1989; 2006)
    - Grid-like spatial coding: some DLPFC neurons show spatial tuning
      similar to parietal cells, but in abstract mnemonic space

KEY FINDINGS:
    1. Funahashi 2006 (PMID 16325345): "Prefrontal cortex and working
       memory processes" — comprehensive review showing DLPFC holds
       abstract rules and goals active during multi-step reasoning
    2. Finn et al. 2019 (PMC31551596): "Layer-dependent activity in
       human prefrontal cortex during working memory" — layers 2/3 and
       5 show different timing; layer-specific working memory signals
    3. Soldado-Magraner et al. 2025 (PMC40447446): Robustness of
       DLPFC working memory to microstimulation — delay period stability

AGENT'S MAPPING:
    dorsolateral_dorsal_output: dict — DLPFC dorsal working memory signal
    working_memory_active: bool — whether WM is currently loaded
    cognitive_control: float 0-1 — strength of top-down cognitive control
    working_memory_buffer: list — items currently held in WM
    rule_loading: float 0-1 — how abstract rule representation is loaded

CITATIONS:
    PMC31551596 — Finn et al. (2019). Layer-dependent activity in human
        prefrontal cortex during working memory. Nat Neurosci.
    PMC40447446 — Soldado-Magraner et al. (2025). Robustness of working
        memory to prefrontal cortex microstimulation. J Neurosci.
    PMC16325345 — Funahashi S. (2006). Prefrontal cortex and working
        memory processes. Neuroscience.
    PMC3799943 — Goldman-Rakic PS. (1995). Cellular basis of working memory.
        Neuron. (Still fundamental reference)
"""

from brain.base_mechanism import BrainMechanism


class DorsolateralPrefrontalDorsal(BrainMechanism):
    """
    DLPFC dorsal part — working memory and cognitive control.

    Maintains abstract rules and goals in working memory during
    multi-step reasoning. Holds "online" information out of the
    environment while operating on it mentally.
    """

    def __init__(self):
        super().__init__(
            name="DorsolateralPrefrontalDorsal",
            human_analog="Dorsolateral prefrontal cortex (BA 9/46) — working memory, cognitive control",
            layer="neocortical",
        )
        self.state.setdefault("working_memory_buffer", [])
        self.state.setdefault("working_memory_active", False)
        self.state.setdefault("cognitive_control", 0.0)
        self.state.setdefault("rule_loading", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Working memory load from upstream (spatial from parietal, object from temporal)
        spatial_wm = prior.get("SuperiorParietalLobuleReaching", {}).get(
            "reaching_signal", 0.0
        )
        object_semantic = prior.get("AnteriorTemporalPoleSemantic", {}).get(
            "concept_binding", 0.0
        )
        sensory_input = prior.get("ThalamicSalienceFilter", {}).get(
            "thalamic_output", 0.5
        ) if prior.get("ThalamicSalienceFilter") else 0.5

        # Goal state from frontopolar (prospective scenarios)
        frontopolar = prior.get("FrontopolarProspectiveSimulator", {})
        prospection = frontopolar.get("prospection_depth", 0.0)
        scenario_branches = frontopolar.get("scenario_branches", [])

        # Executive control from ventrolateral PFC
        vlpfc_interference = prior.get("VentrolateralPrefrontalInferior", {}).get(
            "interference_suppression", 0.5
        )

        # From orbitofrontal (value context affecting what gets into WM)
        ofc_value = prior.get("OrbitofrontalRewardValuator", {}).get(
            "value_signal", 0.5
        )

        # Working memory activation: driven by sensory input + prospection depth
        wm_load_input = (spatial_wm + object_semantic) / 2 * 0.6 + sensory_input * 0.4
        wm_load_input += prospection * 0.2

        # Cognitive control: top-down signal strength proportional to WM load
        # More items in WM = more need for cognitive control
        buffer_len = len(self.state.get("working_memory_buffer", []))
        load_factor = min(1.0, buffer_len / 4.0)  # up to 4 items
        cognitive_control = wm_load_input * (0.5 + load_factor * 0.5)
        cognitive_control = max(0.0, min(1.0, cognitive_control))

        # Rule loading: when WM buffer has content and OFC provides value context
        rule_loading = cognitive_control * ofc_value
        rule_loading = max(0.0, min(1.0, rule_loading))

        # Working memory active when either sensory input is high or prospection is deep
        working_memory_active = wm_load_input > 0.5 or len(scenario_branches) > 1

        # Update WM buffer
        if wm_load_input > 0.6 and not self.state["working_memory_active"]:
            # New item entering WM
            self.state["working_memory_buffer"].append({
                "type": "spatial" if spatial_wm > object_semantic else "semantic",
                "strength": round(wm_load_input, 3)
            })
            if len(self.state["working_memory_buffer"]) > 4:
                self.state["working_memory_buffer"].pop(0)
        elif wm_load_input < 0.3:
            # Decay: clear buffer when load drops
            self.state["working_memory_buffer"] = self.state["working_memory_buffer"][-1:]

        self.state["working_memory_active"] = working_memory_active
        self.state["cognitive_control"] = round(cognitive_control, 4)
        self.state["rule_loading"] = round(rule_loading, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "dorsolateral_dorsal_output": {
                "wm_load": round(wm_load_input, 4),
                "cognitive_control": round(cognitive_control, 4),
                "rule_loading": round(rule_loading, 4),
                "prospection_influence": round(prospection, 4),
            },
            "working_memory_active": working_memory_active,
            "working_memory_items": len(self.state["working_memory_buffer"]),
            "buffer_snapshot": [v for v in self.state["working_memory_buffer"][-2:]],
        }
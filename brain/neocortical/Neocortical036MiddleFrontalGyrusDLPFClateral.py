"""
brain/neocortical/Neocortical036MiddleFrontalGyrusDLPFClateral.py
Middle Frontal Gyrus (BA 46) — DLPFC Proper, Working Memory, Reasoning

ANATOMY (Petrides 2005; Courtney et al. 1998; Wager & Smith 2003):
    The middle frontal gyrus (MFG, BA 46) is the "DLPFC proper" —
    the canonical working memory region. While BA 9/44/45/47 are
    also involved in prefrontal functions, BA 46 is the most
    specialized for active maintenance and manipulation of information.

    BA 46 has a posterior-to-anterior gradient:
    - Posterior BA 46: maintenance of spatial information (spatial WM)
    - Anterior BA 46: maintenance of abstract/conceptual information

    BA 46 is part of the "multiple demand" network — it activates
    whenever any task requires holding task-relevant information
    in mind. This is the "mental workspace" of consciousness.

    Key functions:
    - Active maintenance: keeping information online against decay
    - Manipulation: reorganizing WM contents (e.g., reordering a list)
    - Binding: connecting items across modalities in WM
    - Monitoring: checking what's in WM right now
    - Encoding: putting new information into WM

    Connectivity: BA 46 is the DLPFC "core" — it connects to
    parietal (attention), temporal (semantic), motor (action),
    cingulate (monitoring), and subcortical (motivation) areas.

KEY FINDINGS:
    1. Courtney et al. 1998 (PMC1850954): "Working memory for spatial
       and verbal content" — BA 46 encodes both spatial and verbal WM
    2. Wager & Smith 2003 (PMC1694805): "Meta-analysis of working
       memory" — DLPFC (BA 46) is the consistent WM hub
    3. Petrides 2005 (PMC2929791): "DLPFC and cognitive control"

AGENT'S MAPPING:
    mfg_output: dict — MFG DLPFC output
    reasoning_active: bool — is abstract reasoning engaged?
    working_memory_maintained: list — items currently in WM

CITATIONS:
    PMC1850954 — Courtney et al. (1998). WM for spatial and verbal content. Cereb Cortex.
    PMC1694805 — Wager & Smith (2003). WM meta-analysis. Neuroimage.
    PMC2929791 — Petrides (2005). DLPFC and cognitive control.
    PMC40447446 — DLPFC working memory function.
"""

from brain.base_mechanism import BrainMechanism


class MiddleFrontalGyrusDLPFClateral(BrainMechanism):
    """
    MFG (BA 46) — DLPFC proper, working memory, abstract reasoning.

    The canonical working memory region. Maintains and manipulates
    information across all cognitive domains.
    """

    def __init__(self):
        super().__init__(
            name="MiddleFrontalGyrusDLPFClateral",
            human_analog="MFG (BA 46) — DLPFC proper, working memory, reasoning",
            layer="neocortical",
        )
        self.state.setdefault("working_memory", [])
        self.state.setdefault("reasoning_active", False)
        self.state.setdefault("reasoning_strength", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # DLPFC dorsal (already computed WM load)
        dl_dorsal = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_out = dl_dorsal.get("dorsolateral_dorsal_output", {})
        wm_load = wm_out.get("wm_load", 0.5) if isinstance(wm_out, dict) else 0.5

        # ACC (difficulty signals need for more WM)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_out = acc.get("acc_dorsal_output", {})
        if isinstance(acc_out, dict):
            difficulty = acc_out.get("difficulty_signal", 0.3)
        else:
            difficulty = 0.3

        # Anterior insula (salience signals to boost WM)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Angular gyrus (semantic content entering WM)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_bind = angular.get("multimodal_binding", 0.5)

        # SMG (phonological content in WM)
        smg = prior.get("SupramarginalGyrusManipulation", {})
        manip = smg.get("manipulation_executed", False)

        # Orbitofrontal (value guides what enters WM)
        ofc = prior.get("OrbitofrontalRewardValuator", {})
        value_sig = ofc.get("value_signal", 0.5)

        # WM update: items enter WM based on value × salience
        if salience > 0.55 and value_sig > 0.5:
            new_item = f"semantic_{round(sem_bind, 2)}"
            if new_item not in self.state["working_memory"]:
                self.state["working_memory"].append(new_item)

        # Reasoning: when WM is loaded + semantic content is present + difficulty high
        reasoning_strength = (
            wm_load * 0.4 +
            sem_bind * 0.3 +
            difficulty * 0.3
        )
        # Salience boosts reasoning
        if salience > 0.6:
            reasoning_strength *= (1.0 + (salience - 0.6) * 0.3)
        reasoning_strength = max(0.0, min(1.0, reasoning_strength))

        reasoning_active = reasoning_strength > 0.55

        # WM maintenance: decay over time, stronger with continuous relevance
        if wm_load < 0.3:
            if self.state["working_memory"]:
                self.state["working_memory"].pop(0)

        working_memory_maintained = self.state["working_memory"][-3:] if self.state["working_memory"] else []

        self.state["reasoning_active"] = reasoning_active
        self.state["reasoning_strength"] = round(reasoning_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "mfg_output": {
                "reasoning_active": reasoning_active,
                "reasoning_strength": round(reasoning_strength, 4),
                "wm_items_held": len(working_memory_maintained),
            },
            "reasoning_active": reasoning_active,
            "working_memory_maintained": working_memory_maintained,
        }
"""
brain/neocortical/Neocortical024PosteriorCingulateMemoryAttention.py
Posterior Cingulate Cortex — Memory Retrieval, Attention, Default Mode

ANATOMY (Leech & Sharp 2014; Buckner & Carroll 2007; Brewer et al. 2013):
    The posterior cingulate cortex (PCC, BA 23/31) lies in the
    cingulate sulcus, posterior to the central gyrus. It is one of
    the most metabolically active regions in the brain at rest
    (accounting for ~10% of cerebral glucose consumption at rest),
    and is a core hub of the Default Mode Network (DMN).

    PCC has two functional zones:
    - ventral PCC: memory retrieval — "what should I pay attention to from memory?"
    - dorsal PCC: attentional control — supports task-focused attention

    Key finding: PCC is active during:
    - Mind-wandering and internally-directed thought
    - Memory retrieval (episodic and autobiographical)
    - Self-referential processing (thinking about yourself)
    - Prospection (thinking about the future)

    PCC is DECOUPLED during task-focused attention (e.g., during
    difficult working memory tasks) — this is the "PCC deactivation"
    seen in fMRI during external tasks.

    Connections: hippocampus (memory), precuneus (self), mPFC (self),
    lateral parietal (attention), temporal lobe (semantic).

KEY FINDINGS:
    1. Leech & Sharp 2014 (PMC23869106): "Role of PCC in cognition
       and disease" — comprehensive review of PCC as DMN hub
    2. Brewer et al. 2013 (PMID 24106472): "What the self is in PCC"
       — PCC processes self-referential information
    3. Buckner & Carroll 2007 (PMC18279990): DMN and self-projection
       — PCC, precuneus, mPFC as self-projection network

AGENT'S MAPPING:
    posterior_cingulate_output: dict — PCC output
    memory_attention_integration: float 0-1 — memory retrieval + attention binding
    self_referential: float 0-1 — self-related processing strength

CITATIONS:
    PMC23869106 — Leech & Sharp (2014). Role of PCC in cognition and disease. Brain.
    PMID 24106472 — Brewer et al. (2013). Self in PCC.
    PMC18279990 — Buckner & Carroll (2007). Self-projection and DMN.
"""

from brain.base_mechanism import BrainMechanism


class PosteriorCingulateMemoryAttention(BrainMechanism):
    """
    PCC — memory retrieval, attention, and default mode processing.

    The "memory-attention nexus" — decides what to pay attention
    to from memory, supports mind-wandering and self-referential thought.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorCingulateMemoryAttention",
            human_analog="Posterior cingulate cortex (BA 23/31) — memory, attention, default mode",
            layer="neocortical",
        )
        self.state.setdefault("retrieved_memory", {})
        self.state.setdefault("attention_signal", 0.0)
        self.state.setdefault("default_mode_active", True)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Hippocampal CA1 (episodic memory retrieval)
        hippo_ca1 = prior.get("HippocampalCA1Output", {})
        ca1_out = hippo_ca1.get("ca1_output", {})
        if isinstance(ca1_out, dict):
            consolidation = ca1_out.get("consolidation_signal", 0.3)
        else:
            consolidation = 0.3

        # Precuneus (self-referential imagery)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        precuneus_out = precuneus.get("precuneus_output", {})
        if isinstance(precuneus_out, dict):
            self_rep = precuneus_out.get("self_representation", {}).get("self_clarity", 0.5)
        else:
            self_rep = 0.5

        # Angular gyrus (semantic memory access)
        angular = prior.get("AngularGyrusMultimodal", {})
        sem_access = angular.get("semantic_access", {})
        if isinstance(sem_access, dict):
            sem_strength = sem_access.get("semantic_depth", 0.5)
        else:
            sem_strength = 0.5

        # DLPFC (task-focused mode suppresses PCC)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        task_focus = dlpfc.get("cognitive_control", 0.5)
        wm_active = dlpfc.get("working_memory_active", False)

        # Ventral tegmental area (motivation affects DMN)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            vta_signal = vta_out.get("motivation_signal", 0.5)
        else:
            vta_signal = 0.5

        # Memory-attention integration: when memory retrieval is strong + DMN active
        memory_input = consolidation * 0.4 + sem_strength * 0.3 + vta_signal * 0.3

        # Task suppression: strong DLPFC activity deactivates PCC (DMN suppression)
        task_suppression = task_focus * 0.7 if wm_active else 0.0

        memory_attention_integration = max(0.0, memory_input - task_suppression)
        memory_attention_integration = max(0.0, min(1.0, memory_attention_integration))

        # Self-referential: when memory + self overlap
        self_referential = (memory_attention_integration + self_rep) / 2

        # Default mode: PCC is active when NOT in heavy task mode
        default_mode_active = not wm_active or memory_attention_integration > 0.6

        attention_signal = memory_attention_integration * (1.5 - task_suppression)
        attention_signal = max(0.0, min(1.0, attention_signal))

        self.state["retrieved_memory"] = {"consolidation": consolidation, "semantic": sem_strength}
        self.state["attention_signal"] = round(attention_signal, 4)
        self.state["default_mode_active"] = default_mode_active
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_cingulate_output": {
                "memory_attention": round(memory_attention_integration, 4),
                "self_referential": round(self_referential, 4),
                "default_mode": default_mode_active,
            },
            "memory_attention_integration": round(memory_attention_integration, 4),
            "self_referential": round(self_referential, 4),
        }
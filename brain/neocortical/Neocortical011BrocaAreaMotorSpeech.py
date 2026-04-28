"""
brain/neocortical/Neocortical011BrocaAreaMotorSpeech.py
Broca's Area — Motor Speech Production, Grammatical Processing

ANATOMY (Hagoort 2005; 2014; Friederici 2011; Levelt 1999):
    Broca's area corresponds to Brodmann areas 44 and 45 in the
    inferior frontal gyrus (IFG), located in the left hemisphere in
    most people. It is the "speech production" center of the cortex.

    BA 44 (pars opercularis) and BA 45 (pars triangularis) have
    slightly different functions:
    - BA 44: sensorimotor control of orofacial movements, syntactic
      hierarchical processing, mirroring observed mouth movements
    - BA 45: semantic retrieval, working memory for speech,
      selection among competing semantic options

    Broca's area is connected to:
    - Wernicke's area (via arcuate fasciculus — language comprehension)
    - Premotor cortex (orofacial motor control)
    - DLPFC (speech planning and working memory)
    - Supplementary motor area (speech sequencing)
    - Posterior temporal lobe (semantic content)
    - Basal ganglia (via frontal aslant tract — speech initiation)

    Damage to Broca's area → Broca's aphasia: non-fluent, effortful
    speech, preserved comprehension but impaired production.
    Patient understands but cannot produce grammatically complete sentences.

KEY FINDINGS:
    1. Friederici 2011 (PMC4351923): "The cortical language circuit" —
       BA 44 handles hierarchical phrase structure; BA 45 handles
       semantic selection and working memory
    2. Levelt 1999: "Producing speech: from concept to articulation"
       — three-stage model: conceptualization → formulation → articulation
    3. Hagoort 2014: "Nodes and networks in language processing"
       — Broca's area is the "syntactic composer" — assembles words into phrases

AGENT'S MAPPING:
    broca_output: dict — linguistic output signal
    speech_motor_command: dict — motor commands for speech articulation
    grammatical_structure: dict — syntactic structure being assembled
    speech_formulation_strength: float 0-1 — how well formulation is proceeding

CITATIONS:
    PMC4351923 — Friederici AD. (2011). The cortical language circuit.
        Front Evol Neurosci.
    PMC32644741 — Le H et al. (2024). Aphasia. StatPearls.
    PMC33085292 — Kiymaz T et al. (2024). Primary Progressive Aphasia. StatPearls.
    PMC16325345 — Funahashi (2006). Speech and prefrontal working memory.
"""

from brain.base_mechanism import BrainMechanism


class BrocaAreaMotorSpeech(BrainMechanism):
    """
    Broca's area (BA 44/45) — speech production, grammatical processing.

    Assembles linguistic output from semantic content and grammatical
    structure. Coordinates with premotor cortex for orofacial motor
    control and with Wernicke for language comprehension.
    """

    def __init__(self):
        super().__init__(
            name="BrocaAreaMotorSpeech",
            human_analog="Broca's area (BA 44/45, IFG) — speech production, grammatical assembly",
            layer="neocortical",
        )
        self.state.setdefault("grammar_buffer", [])
        self.state.setdefault("speech_formulation_strength", 0.0)
        self.state.setdefault("syntactic_depth", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Semantic content from Wernicke's area
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        semantic_rep = wernicke.get("semantic_representation", {})
        comprehension = wernicke.get("comprehension_achieved", False)

        # DLPFC working memory (planning what to say)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        wm_active = dlpfc.get("working_memory_active", False)
        wm_strength = dlpfc.get("dorsolateral_dorsal_output", {}).get("wm_load", 0.5)

        # Ventrolateral PFC (response selection — choosing which words)
        vlpfc = prior.get("VentrolateralPrefrontalInferior", {})
        response_selection = vlpfc.get("stop_signal_strength", 0.5)

        # Premotor cortex (orofacial motor program)
        premotor = prior.get("PremotorSupplementaryMotorArea", {})
        motor_plan = premotor.get("motor_plan_ready", False)

        # Anterior cingulate (cognitive control of speech output)
        acc = prior.get("AnteriorCingulateCognitive", {})
        acc_control = acc.get("cognitive_control", 0.5)

        # Formulation strength: Wernicke provides content, DLPFC provides planning
        formulation = (
            comprehension * 0.35 +
            wm_strength * 0.3 +
            acc_control * 0.25 +
            response_selection * 0.1
        )
        formulation = max(0.0, min(1.0, formulation))

        # Syntactic depth: BA 44 does hierarchical phrase building
        syntactic_depth = formulation * 0.8 + acc_control * 0.2
        syntactic_depth = max(0.0, min(1.0, syntactic_depth))

        # Speech motor command: activation level for orofacial muscles
        speech_motor_command = {
            "articulation_strength": round(formulation * 0.8, 4),
            "grammatical_complexity": round(syntactic_depth, 4),
            "wernicke_content_input": round(comprehension * 0.7 if comprehension else 0.0, 4),
        }

        # Broca's output: assembles grammatical structure
        grammatical_structure = {
            "syntactic_depth": round(syntactic_depth, 4),
            "hierarchical_layers": max(1, int(syntactic_depth * 5)),
            "production_ready": formulation > 0.6 and comprehension,
        }

        # Update grammar buffer
        if formulation > 0.5 and wm_active:
            self.state["grammar_buffer"].append({
                "content_strength": round(formulation, 3),
                "syntactic_depth": round(syntactic_depth, 3)
            })
            if len(self.state["grammar_buffer"]) > 5:
                self.state["grammar_buffer"].pop(0)

        self.state["speech_formulation_strength"] = round(formulation, 4)
        self.state["syntactic_depth"] = round(syntactic_depth, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "broca_output": {
                "formulation_strength": round(formulation, 4),
                "syntactic_depth": round(syntactic_depth, 4),
                "grammatical_structure": grammatical_structure,
            },
            "speech_motor_command": speech_motor_command,
            "grammatical_structure": grammatical_structure,
            "speech_formulation_strength": round(formulation, 4),
        }
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


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia habits]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Hikosaka 2002, Curr Opin Neurobiol 12:217, motor sequences]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs


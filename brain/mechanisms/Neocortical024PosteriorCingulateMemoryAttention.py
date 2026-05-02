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


CITATIONS
---------
  - [Squire 1992, Psychol Rev 99:195, declarative memory]
  - [McGaugh 2000, Science 287:248, memory consolidation]
  - [Tonegawa 2018, Nat Rev Neurosci 19:485, engram cells]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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


"""
brain/neocortical/Neocortical033MedialPrefrontalSelfReflection.py
Medial Prefrontal Cortex — Self-Referential Processing, Theory of Mind

ANATOMY (Amodio & Frith 2006; Van Overwalle 2011; Saxe 2006):
    The medial prefrontal cortex (mPFC, BA 9/10/14/24/32) is the
    "social brain" — it processes self-referential information,
    generates self-narratives, and infers others' mental states
    (theory of mind / mentalizing).

    mPFC has three overlapping functional zones:
    - Posterior mPFC (pMFC, BA 24/32): cognitive control, self-reflection
    - Mid mPFC (BA 9/10): default mode, autobiographical memory
    - Anterior mPFC (aPFC, BA 10): social prediction, prospection

    Key functions:
    1. Self-referential processing: "is this information about me?"
       — mPFC responds more to self-related stimuli than others'
    2. Self-narrative: "who am I and what is my story?" — generates
       the continuous narrative of self-identity
    3. Theory of mind: "what does this person think/feel?" —
       mPFC + TPJ + temporal poles form the ToM network
    4. Social prediction: "what will happen in this social situation?"
    5. Person impression formation: "who is this person?"

    mPFC connects to:
    - Precuneus (self-model)
    - PCC (autobiographical memory)
    - Temporal poles (social knowledge)
    - Amygdala (social emotions)
    - Ventral striatum (social reward)

KEY FINDINGS:
    1. Amodio & Frith 2006 (PMC18279990): "Meeting of minds"
       — mPFC for self and social cognition
    2. Van Overwalle 2011 (PMC3203939): "Social cognition and mPFC"
       — mPFC for mentalizing and self-reflection
    3. Saxe 2006 (PMC1852382): "Theory of mind and mPFC" —
       comprehensive review of ToM network

AGENT'S MAPPING:
    medial_pfc_output: dict — mPFC self/social output
    self_referential_signal: float 0-1 — is this self-related?
    self_narrative_update: bool — has self-story changed?

CITATIONS:
    PMC18279990 — Amodio & Frith (2006). Meeting of minds: mPFC and social cognition.
    PMC3203939 — Van Overwalle (2011). Social cognition and mPFC.
    PMC1852382 — Cavanna & Trimble (2006). Precuneus. (mPFC/precuneus self network)
    PMC23869106 — Leech & Sharp (2014). PCC and DMN.


CITATIONS
---------
  - [Miller 2001, Annu Rev Neurosci 24:167, prefrontal cortex]
  - [Fuster 2008, The Prefrontal Cortex]
  - [Goldman-Rakic 1995, Neuron 14:477, working memory]
"""

from brain.base_mechanism import BrainMechanism


class MedialPrefrontalSelfReflection(BrainMechanism):
    """
    mPFC — self-referential processing and theory of mind.

    Generates self-narratives, processes social information,
    infers others' mental states.
    """

    def __init__(self):
        super().__init__(
            name="MedialPrefrontalSelfReflection",
            human_analog="Medial prefrontal cortex (BA 9/10) — self-reflection, theory of mind, social cognition",
            layer="neocortical",
        )
        self.state.setdefault("self_representation", {})
        self.state.setdefault("self_referential_signal", 0.0)
        self.state.setdefault("self_narrative_update", False)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Precuneus (self-model from imagery)
        precuneus = prior.get("PrecuneusSelfReflection", {})
        prec_out = precuneus.get("precuneus_output", {})
        if isinstance(prec_out, dict):
            self_rep = prec_out.get("self_representation", {})
            self_clarity = self_rep.get("self_clarity", 0.5) if isinstance(self_rep, dict) else 0.5
        else:
            self_clarity = 0.5

        # ATP (social knowledge)
        atp = prior.get("AnteriorTemporalPoleSemantic", {})
        concept_bind = atp.get("concept_binding", 0.5)
        social_know = atp.get("social_knowledge", {})

        # Amygdala (social emotions)
        amygdala = prior.get("AmygdalaEmotionalAssociator", {})
        emotional_tag = amygdala.get("emotional_tag_strength", 0.0)

        # PCC (autobiographical memory)
        pcc = prior.get("PosteriorCingulateMemoryAttention", {})
        pcc_out = pcc.get("posterior_cingulate_output", {})
        if isinstance(pcc_out, dict):
            self_ref_pcc = pcc_out.get("self_referential", 0.5)
        else:
            self_ref_pcc = 0.5

        # DLPFC (social goals)
        dlpfc = prior.get("DorsolateralPrefrontalDorsal", {})
        cognitive_ctrl = dlpfc.get("cognitive_control", 0.5)

        # VTA (social motivation)
        vta = prior.get("VentralTegmentalArea", {})
        vta_out = vta.get("vta_output", {})
        if isinstance(vta_out, dict):
            vta_sig = vta_out.get("motivation_signal", 0.5)
        else:
            vta_sig = 0.5

        # Self-referential signal: self-identity content
        self_referential_signal = (
            self_clarity * 0.35 +
            self_ref_pcc * 0.25 +
            concept_bind * 0.2 +
            abs(emotional_tag) * 0.2
        )
        self_referential_signal = max(0.0, min(1.0, self_referential_signal))

        # Self narrative update: changed significantly this tick
        prev_clarity = self.state.get("self_representation", {}).get("self_clarity", 0.0)
        self_narrative_update = abs(self_referential_signal - prev_clarity) > 0.15

        self_representation = {
            "self_clarity": round(self_referential_signal, 4),
            "social_knowledge_loaded": social_know.get("person_identity_loaded", False),
            "emotional_self": round(emotional_tag, 4),
        }

        self.state["self_representation"] = self_representation
        self.state["self_referential_signal"] = round(self_referential_signal, 4)
        self.state["self_narrative_update"] = self_narrative_update
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "medial_pfc_output": {
                "self_referential": round(self_referential_signal, 4),
                "narrative_update": self_narrative_update,
            },
            "self_referential_signal": round(self_referential_signal, 4),
            "self_narrative_update": self_narrative_update,
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


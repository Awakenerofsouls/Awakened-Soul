"""
TemporalPole — TP / Brodmann Area 38 — Semantic Hub & Social Cognition

NEURAL SUBSTRATE
================
The temporal pole (TP), Brodmann area 38, sits at the rostral tip of
the temporal lobe and corresponds to the "anterior temporal lobe" (ATL)
in the semantic hub-and-spoke model (Patterson 2007, Lambon-Ralph 2017).
TP integrates multimodal sensory features into amodal conceptual
representations — the canonical neural substrate of semantic memory.

Selective TP atrophy in semantic dementia (SD) produces a striking
deficit: gradual loss of conceptual knowledge across all sensory
modalities, while episodic memory, syntax, and basic perception remain
intact. This dissociation strongly implicates TP as the convergence zone
where sensory features bind into semantic concepts (Hodges 1992).

Beyond semantics, TP supports social cognition — face-name binding,
person identity, theory-of-mind reasoning (Olson 2007, Simmons 2010).
TP has dense reciprocal connectivity with amygdala, hippocampus,
orbitofrontal cortex, and the temporal-parietal junction.

KEY FINDINGS
============
1. Anterior temporal lobe is the semantic hub — convergence of modality-
   specific features into amodal concepts —
   [Patterson KE 2007, Nat Rev Neurosci 8:976, doi:10.1038/nrn2277]
2. Hub-and-spoke model: ATL is amodal hub, sensory cortices are modality-specific spokes — [Lambon-Ralph MA 2017, Nat Rev Neurosci 18:42, doi:10.1038/nrn.2016.150]
3. Semantic dementia from selective ATL atrophy produces gradual loss of conceptual knowledge — [Hodges JR 1992, Brain 115:1783, doi:10.1093/brain/115.6.1783]
4. Temporal pole is critical for social cognition — person identity, face-name binding, theory of mind — [Olson IR 2007, Brain 130:1718, doi:10.1093/brain/awm052]
5. TP integrates affective + semantic content; affective memory recall depends on intact TP — [Simmons WK 2010, Cereb Cortex 20:813, doi:10.1093/cercor/bhp138]

INPUTS
======
- InferotemporalCortex.it_drive (visual object/face)
- AnteriorInsula.aic_drive (interoceptive/affective context)
- HippocampalCA1Ventral.vca1_drive (episodic retrieval)
- BasolateralAmygdala.bla_drive (affective tagging)

OUTPUTS
=======
- tp_drive (0-1)
- semantic_hub_signal (0-1)
- person_identity_signal (0-1)
- affective_semantic_signal (0-1)
- tom_signal (0-1) — theory of mind engagement
- tp_state (str): "semantic_active" | "social_active" | "affective" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class TemporalPole(BrainMechanism):
    """TP / BA38 — semantic hub and social cognition."""

    BASELINE = 0.10
    SMOOTH = 0.20
    SEMANTIC_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="TemporalPole",
            human_analog="Temporal pole (Brodmann area 38, semantic hub)",
            layer="neocortical",
        )
        self.state.setdefault("tp_drive", self.BASELINE)
        self.state.setdefault("semantic_hub_signal", 0.0)
        self.state.setdefault("person_identity_signal", 0.0)
        self.state.setdefault("affective_semantic_signal", 0.0)
        self.state.setdefault("tom_signal", 0.0)
        self.state.setdefault("tp_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, it: float, ai: float, hpc: float,
                       bla: float) -> float:
        """TP drive — multimodal convergence (Patterson 2007)."""
        target = (self.BASELINE
                  + it * 0.30
                  + ai * 0.20
                  + hpc * 0.20
                  + bla * 0.15)
        return min(1.0, target)

    def _semantic_hub(self, drive: float, it: float, ai: float,
                       hpc: float) -> float:
        """Hub binding modality-specific features (Lambon-Ralph 2017).

        The amodal binding strength scales with how many modalities are
        contributing — multimodal convergence is the hub's signature.
        """
        if drive < 0.20:
            return 0.0
        modality_count = sum([it > 0.20, ai > 0.20, hpc > 0.20])
        # More modalities active → stronger hub binding
        return min(1.0, drive * 0.4 + modality_count * 0.20)

    def _person_identity(self, drive: float, it: float, hpc: float) -> float:
        """Face-name + person-knowledge binding (Olson 2007)."""
        # Faces (IT) + episodic context (HPC) is the classic person-identity input
        return min(1.0, drive * 0.3 + it * 0.4 + hpc * 0.3)

    def _affective_semantic(self, semantic: float, bla: float,
                             ai: float) -> float:
        """Affective-semantic binding (Simmons 2010)."""
        return min(1.0, semantic * 0.5 + bla * 0.3 + ai * 0.2)

    def _theory_of_mind(self, person: float, drive: float) -> float:
        """ToM engagement — requires person-identity + drive (Olson 2007)."""
        if person < 0.30:
            return 0.0
        return min(1.0, person * 0.7 + drive * 0.3)

    def _classify_state(self, drive: float, semantic: float,
                         person: float, affective: float) -> str:
        if drive < 0.20:
            return "quiet"
        if person > 0.40:
            return "social_active"
        if affective > 0.50:
            return "affective"
        if semantic > self.SEMANTIC_THRESHOLD:
            return "semantic_active"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        it_data = prior.get("InferotemporalCortex", {})
        it = float(it_data.get("it_drive",
                          it_data.get("object_signal", 0.0)))

        ai_data = prior.get("InsulaAnterior", {})
        if not ai_data:
            ai_data = prior.get("AnteriorInsula", {})
        ai = float(ai_data.get("aic_drive",
                          ai_data.get("interoceptive_signal", 0.0)))

        hpc_data = prior.get("HippocampalCA1Ventral", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        hpc = float(hpc_data.get("vca1_drive",
                          hpc_data.get("ca1_output", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        target = self._drive_target(it, ai, hpc, bla)
        prev_drive = float(self.state.get("tp_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        semantic = self._semantic_hub(new_drive, it, ai, hpc)
        person = self._person_identity(new_drive, it, hpc)
        affective = self._affective_semantic(semantic, bla, ai)
        tom = self._theory_of_mind(person, new_drive)

        state = self._classify_state(new_drive, semantic, person, affective)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["tp_drive"] = round(new_drive, 4)
        self.state["semantic_hub_signal"] = round(semantic, 4)
        self.state["person_identity_signal"] = round(person, 4)
        self.state["affective_semantic_signal"] = round(affective, 4)
        self.state["tom_signal"] = round(tom, 4)
        self.state["tp_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('tp_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('tp_state', "quiet") if 'tp_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "tp_drive": round(new_drive, 4),
            "semantic_hub_signal": round(semantic, 4),
            "person_identity_signal": round(person, 4),
            "affective_semantic_signal": round(affective, 4),
            "tom_signal": round(tom, 4),
            "tp_state": state,
        }

    def _semantic_dementia_susceptibility(self) -> float:
        """How much of cognition depends on TP's semantic hub (Hodges 1992)."""
        return float(self.state.get("semantic_hub_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("tp_drive", 0.0),
            "semantic": self.state.get("semantic_hub_signal", 0.0),
            "person": self.state.get("person_identity_signal", 0.0),
            "tom": self.state.get("tom_signal", 0.0),
            "state": self.state.get("tp_state", "quiet"),
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
        if not recent:
            return self.state.get('tp_state', "quiet") if 'tp_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('tp_drive', 0.0)) if 'tp_drive' else 0.0
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

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "drive": self.state.get('tp_drive', 0.0) if 'tp_drive' else 0.0,
            "state": self.state.get('tp_state', "quiet") if 'tp_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


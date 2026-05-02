"""
FrontalPole — FP / Brodmann Area 10 — Meta-Cognition & Branching

NEURAL SUBSTRATE
================
The frontal pole (FP), corresponding to Brodmann area 10, is the most
anterior portion of human prefrontal cortex and the largest cytoarchitectonic
region of frontal cortex (Ramnani & Owen 2004 — disproportionately
expanded in humans). FP supports the highest level of cognitive
control: the ability to hold a primary goal "in escrow" while pursuing a
secondary subgoal — Koechlin et al. 1999 termed this "branching" or
cognitive multi-tasking.

Two functional subdivisions: medial FP (BA10m) is engaged by self-
referential and prospective cognition (mentalizing about future events,
imagining possibilities), while lateral FP (BA10l) supports relational
integration of multiple cognitive operations and counterfactual
reasoning. Burgess 2007 demonstrated FP critically supports prospective
memory — remembering to execute future intentions.

Fleming 2010 extended this to meta-cognition proper: FP grey matter
predicts introspective accuracy — how well a subject can rate their own
confidence in perceptual judgments. FP is thus the cortical substrate
of "thinking about thinking."

KEY FINDINGS
============
1. Frontal pole supports cognitive branching — holding pending goals while executing subordinate ones — [Koechlin EM 1999, Nature 399:148, doi:10.1038/20178]
2. Frontal pole BA10 is the cortical substrate of prospective memory and future-directed cognition — [Burgess PW 2007, Trends Cogn Sci 11:290, doi:10.1016/j.tics.2007.05.004]
3. Anterior PFC grey matter predicts introspective accuracy — meta-cognitive substrate — [Fleming SM 2010, Science 329:1541, doi:10.1126/science.1191883]
4. FP is disproportionately expanded in humans relative to other primates — [Ramnani NA 2004, Nat Rev Neurosci 5:184, doi:10.1038/nrn1343]
5. Frontopolar lateral activity reflects relational integration of multiple cognitive operations — [Tsujimoto SO 2011, Trends Cogn Sci 15:169, doi:10.1016/j.tics.2011.02.001]

INPUTS
======
- DorsolateralPrefrontalCortex.dlpfc_drive (current task)
- HippocampalCA1Ventral.vca1_drive (autobiographical retrieval)
- VentromedialPrefrontalCortex.vmpfc_drive (self-reference)
- CingulateAnterior.acc_drive (conflict monitor)

OUTPUTS
=======
- fp_drive (0-1)
- branching_signal (0-1) — pending-goal maintenance
- prospection_signal (0-1) — future simulation
- metacognitive_confidence (0-1)
- relational_integration_signal (0-1)
- fp_state (str): "branching" | "prospecting" | "metacog" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class FrontalPole(BrainMechanism):
    """FP / BA10 — meta-cognition, branching, prospection."""

    BASELINE = 0.10
    SMOOTH = 0.18  # slower than typical — FP integrates over longer timescales
    BRANCHING_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="FrontalPole",
            human_analog="Frontal pole (Brodmann area 10)",
            layer="neocortical",
        )
        self.state.setdefault("fp_drive", self.BASELINE)
        self.state.setdefault("branching_signal", 0.0)
        self.state.setdefault("prospection_signal", 0.0)
        self.state.setdefault("metacognitive_confidence", 0.0)
        self.state.setdefault("relational_integration_signal", 0.0)
        self.state.setdefault("pending_goal_buffer", 0.0)
        self.state.setdefault("fp_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, dlpfc: float, hpc: float, vmpfc: float,
                       acc: float) -> float:
        """FP drive (Ramnani 2004 — convergence of high-level inputs)."""
        target = (self.BASELINE
                  + dlpfc * 0.30
                  + hpc * 0.20
                  + vmpfc * 0.20
                  + acc * 0.15)
        return min(1.0, target)

    def _branching(self, drive: float, prev_buffer: float, acc: float) -> float:
        """Pending-goal maintenance during subgoal execution (Koechlin 1999).

        Branching builds when ACC signals need to switch focus while
        maintaining the previous goal in escrow.
        """
        if drive < 0.20:
            return prev_buffer * 0.92  # decay
        return min(1.0, prev_buffer * 0.85 + drive * 0.20 + acc * 0.10)

    def _prospection(self, drive: float, hpc: float, vmpfc: float) -> float:
        """Future simulation — engages with HPC retrieval + vmPFC self (Burgess 2007)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + hpc * 0.3 + vmpfc * 0.3)

    def _metacognition(self, drive: float, prev: float) -> float:
        """Metacognitive confidence — slow integrator (Fleming 2010)."""
        # Confidence builds with sustained, stable drive
        return min(1.0, prev * 0.92 + drive * 0.10)

    def _relational_integration(self, drive: float, branching: float,
                                  prospection: float) -> float:
        """Multi-operation relational binding (Tsujimoto 2011)."""
        return min(1.0, drive * 0.3 + branching * 0.4 + prospection * 0.3)

    def _classify_state(self, drive: float, branching: float,
                         prospection: float, metacog: float) -> str:
        if drive < 0.20:
            return "quiet"
        if branching > self.BRANCHING_THRESHOLD:
            return "branching"
        if prospection > 0.40:
            return "prospecting"
        if metacog > 0.30:
            return "metacog"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive",
                            dlpfc_data.get("working_memory_signal", 0.0)))

        hpc_data = prior.get("HippocampalCA1Ventral", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        hpc = float(hpc_data.get("vca1_drive",
                          hpc_data.get("ca1_output", 0.0)))

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive",
                            vmpfc_data.get("self_reference_signal", 0.0)))

        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive",
                          acc_data.get("conflict_signal", 0.0)))

        target = self._drive_target(dlpfc, hpc, vmpfc, acc)
        prev_drive = float(self.state.get("fp_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        prev_buffer = float(self.state.get("pending_goal_buffer", 0.0))
        branching = self._branching(new_drive, prev_buffer, acc)

        prospection = self._prospection(new_drive, hpc, vmpfc)

        prev_metacog = float(self.state.get("metacognitive_confidence", 0.0))
        metacog = self._metacognition(new_drive, prev_metacog)

        relational = self._relational_integration(new_drive, branching, prospection)

        state = self._classify_state(new_drive, branching, prospection, metacog)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["fp_drive"] = round(new_drive, 4)
        self.state["branching_signal"] = round(branching, 4)
        self.state["pending_goal_buffer"] = round(branching, 4)
        self.state["prospection_signal"] = round(prospection, 4)
        self.state["metacognitive_confidence"] = round(metacog, 4)
        self.state["relational_integration_signal"] = round(relational, 4)
        self.state["fp_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
                # extension: track primary drive + state history
        rd = list(self.state.get("recent_drives", []))
        rd.append(float(self.state.get('fp_drive', 0.0)))
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        rs = list(self.state.get("recent_states", []))
        rs.append(self.state.get('fp_state', "quiet") if 'fp_state' else "quiet")
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs

        self.persist_state()

        return {
            "fp_drive": round(new_drive, 4),
            "branching_signal": round(branching, 4),
            "prospection_signal": round(prospection, 4),
            "metacognitive_confidence": round(metacog, 4),
            "relational_integration_signal": round(relational, 4),
            "fp_state": state,
        }

    def _multi_task_capacity(self) -> float:
        """Capacity to hold multiple goals (Koechlin 1999)."""
        return float(self.state.get("branching_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("fp_drive", 0.0),
            "branching": self.state.get("branching_signal", 0.0),
            "prospection": self.state.get("prospection_signal", 0.0),
            "metacog": self.state.get("metacognitive_confidence", 0.0),
            "state": self.state.get("fp_state", "quiet"),
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
            return self.state.get('fp_state', "quiet") if 'fp_state' else "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return float(self.state.get('fp_drive', 0.0)) if 'fp_drive' else 0.0
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
            "drive": self.state.get('fp_drive', 0.0) if 'fp_drive' else 0.0,
            "state": self.state.get('fp_state', "quiet") if 'fp_state' else "quiet",
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }


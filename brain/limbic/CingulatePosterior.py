"""
CingulatePosterior -- PCC / Default Mode + Autobiographical Recall

NEURAL SUBSTRATE
================
Posterior cingulate cortex (PCC, Brodmann 23/31) is a core hub of the
default mode network (DMN). Distinct from anterior cingulate which is
cognitive control. PCC is most active during self-referential
processing, autobiographical recall, mind-wandering, and rest.

Buckner 2008 mapped DMN as a coherent network with PCC as central hub,
along with mPFC, angular gyrus, hippocampal formation. Vogt 2005
identified PCC as the autobiographical recall subdivision of cingulate.

Connectivity: dense reciprocal connections with hippocampus, mPFC, RSC,
inferior parietal lobule, precuneus.

KEY FINDINGS
============
1. PCC is a core hub of default mode network (DMN); most active during
   rest, mind-wandering, self-referential processing --
   [Buckner 2008, Ann NY Acad Sci 1124:1, doi:10.1196/annals.1440.011]
2. Cingulate four-region map: PCC dedicated to autobiographical
   memory + self-monitoring, distinct from ACC cognitive control --
   [Vogt 2005, Nat Rev Neurosci 6:533, doi:10.1038/nrn1704]
3. PCC activates during autobiographical memory retrieval; lesion
   produces specific deficits in self-referential recall --
   [Maddock 2001, Hippocampus 11:577, PMID 11732710]
4. PCC is the highest-metabolism region at rest in human brain;
   "default" baseline activity -- [Raichle 2001, Proc Natl Acad Sci
   98:676, doi:10.1073/pnas.98.2.676]
5. PCC connectivity disrupted in Alzheimer's; early biomarker --
   [Greicius 2004, Proc Natl Acad Sci 101:4637, doi:10.1073/pnas.0308627101]

INPUTS
======
- HippocampalCA1Output.ca1_drive (autobiographical retrieval)
- RetrosplenialCortexProxy.rsc_drive
- PrelimbicCortex.pl_drive (mPFC self-referential)
- AngularGyrusProxy.ag_drive (default 0)
- ArousalRegulator.tonic_level (rest-vs-task gate)

OUTPUTS
=======
- pcc_drive (0-1)
- default_mode_signal (0-1)
- autobiographical_recall_signal (0-1)
- self_referential_signal (0-1)
- mind_wandering_signal (0-1)
- pcc_state (str): "default_mode" | "autobiographical_recall" |
  "self_reference" | "task_engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class CingulatePosterior(BrainMechanism):
    """PCC -- default mode network hub + autobiographical recall."""

    BASELINE = 0.20  # PCC is high-baseline at rest (Raichle 2001)
    SMOOTH = 0.20
    DEFAULT_MODE_THRESHOLD = 0.40
    RECALL_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="CingulatePosterior",
            human_analog="Posterior cingulate (default mode + autobiographical)",
            layer="limbic",
        )
        self.state.setdefault("pcc_drive", self.BASELINE)
        self.state.setdefault("default_mode_signal", 0.0)
        self.state.setdefault("autobiographical_recall_signal", 0.0)
        self.state.setdefault("self_referential_signal", 0.0)
        self.state.setdefault("mind_wandering_signal", 0.0)
        self.state.setdefault("pcc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ca1: float, rsc: float, pl: float,
                       ag: float, arousal: float) -> float:
        """PCC firing -- high at rest (Raichle 2001), suppressed by task.

        Default high baseline reflects "default mode" -- rest activity.
        Task-driven arousal suppresses default mode.
        """
        # Rest-default state
        target = self.BASELINE + ca1 * 0.20 + rsc * 0.20 + pl * 0.15 + ag * 0.15

        # Task-engagement (high arousal) suppresses default mode (Raichle 2001)
        if arousal > 0.65:
            target *= 0.6  # task engagement suppresses
        return min(1.0, target)

    def _default_mode_signal(self, drive: float, arousal: float) -> float:
        """Default mode signal -- strong when at rest, weak during task."""
        if arousal > 0.65:
            return drive * 0.3
        return min(1.0, drive * 1.1)

    def _autobiographical_recall(self, ca1: float, drive: float) -> float:
        """Autobiographical memory retrieval (Maddock 2001).
        Strong when CA1 is recalling + PCC active.
        """
        if ca1 < 0.30:
            return 0.0
        return min(1.0, drive * 0.5 + ca1 * 0.5)

    def _self_referential(self, pl: float, drive: float, arousal: float) -> float:
        """Self-referential processing -- PCC + mPFC coactivation."""
        if pl < 0.20 or arousal > 0.65:
            return 0.0
        return min(1.0, drive * 0.5 + pl * 0.5)

    def _mind_wandering(self, drive: float, arousal: float, pl: float) -> float:
        """Mind-wandering signal -- high default mode + low task arousal."""
        if arousal > 0.60:
            return 0.0
        return min(1.0, drive * 0.6 + (1.0 - arousal) * 0.4 - pl * 0.2)

    def _classify_state(self, default_mode: float, recall: float,
                          self_ref: float, arousal: float) -> str:
        if arousal > 0.65:
            return "task_engaged"
        if recall > self.RECALL_THRESHOLD:
            return "autobiographical_recall"
        if self_ref > 0.30:
            return "self_reference"
        if default_mode > self.DEFAULT_MODE_THRESHOLD:
            return "default_mode"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        rsc_data = prior.get("RetrosplenialCortexProxy", {})
        rsc = float(rsc_data.get("rsc_drive", 0.0))

        pl_data = prior.get("PrelimbicCortex", {})
        pl = float(pl_data.get("pl_drive", 0.0))

        ag_data = prior.get("AngularGyrusProxy", {})
        ag = float(ag_data.get("ag_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        target = self._drive_target(ca1, rsc, pl, ag, arousal)
        prev_drive = float(self.state.get("pcc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        default_mode = self._default_mode_signal(new_drive, arousal)
        recall = self._autobiographical_recall(ca1, new_drive)
        self_ref = self._self_referential(pl, new_drive, arousal)
        wandering = self._mind_wandering(new_drive, arousal, pl)

        state = self._classify_state(default_mode, recall, self_ref, arousal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pcc_drive"] = round(new_drive, 4)
        self.state["default_mode_signal"] = round(default_mode, 4)
        self.state["autobiographical_recall_signal"] = round(recall, 4)
        self.state["self_referential_signal"] = round(self_ref, 4)
        self.state["mind_wandering_signal"] = round(wandering, 4)
        self.state["pcc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pcc_drive": round(new_drive, 4),
            "default_mode_signal": round(default_mode, 4),
            "autobiographical_recall_signal": round(recall, 4),
            "self_referential_signal": round(self_ref, 4),
            "mind_wandering_signal": round(wandering, 4),
            "pcc_state": state,
        }

    def _resting_state_baseline(self) -> float:
        """Resting-state baseline activity (Raichle 2001 default mode)."""
        return self.state.get("default_mode_signal", 0.0)

    def _episodic_retrieval_confidence(self, recall: float,
                                          default_mode: float) -> float:
        """Episodic retrieval confidence -- DMN activation during
        recall suggests strong autobiographical memory retrieval.
        Buckner 2008: PCC is hub for episodic memory confidence."""
        if recall < 0.20:
            return 0.0
        return min(1.0, recall * (1.0 - default_mode * 0.3))

    def _default_mode_connectivity(self, pcc_drive: float,
                                    default_mode: float) -> float:
        """Default mode connectivity -- PCC is central node in DMN.
        Returns connectivity strength based on PCC drive + DMN signal."""
        if pcc_drive < 0.20:
            return 0.0
        return min(1.0, pcc_drive * default_mode * 1.2)

    def _self_referential_processing_strength(self, emotional: float,
                                              recall: float) -> float:
        """Self-referential processing -- PCC activates for self-
        referential stimuli. Higher when emotional + recall both
        active (self-related emotional memories)."""
        if emotional < 0.20:
            return 0.0
        return min(1.0, emotional * recall * 1.5)

    def _memory_consolidation_trigger(self, recall: float,
                                      wandering: float) -> float:
        """Memory consolidation trigger -- off-task mind wandering
        (DMN) during recall may trigger consolidation of
        recently retrieved memories."""
        if recall < 0.20 or wandering < 0.20:
            return 0.0
        return min(1.0, recall * wandering * 0.8)


    def _autobiographical_memory_clarity(self, recall: float,
                                         emotional: float) -> float:
        """Autobiographical memory clarity -- emotional
        autobiographical memories are recalled with higher
        sensory detail. PCC engagement reflects this clarity."""
        if recall < 0.20:
            return 0.0
        return min(1.0, recall * (1.0 + emotional * 0.5))

    def _prospection_signal(self, recall: float,
                            default_mode: float) -> float:
        """Prospection signal -- DMN PCC fires during future
        thinking and imagination. Returns prospection
        strength (0-1) based on DMN + recall co-activation."""
        if recall < 0.20:
            return 0.0
        return min(1.0, default_mode * recall * 1.2)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pcc_drive", 0.0),
            "default_mode": self.state.get("default_mode_signal", 0.0),
            "recall": self.state.get("autobiographical_recall_signal", 0.0),
            "state": self.state.get("pcc_state", "quiet"),
        }

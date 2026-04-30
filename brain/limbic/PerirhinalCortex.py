"""
PerirhinalCortex -- PRH / Object Recognition + Familiarity Memory

NEURAL SUBSTRATE
================
Perirhinal cortex (PRH, Brodmann areas 35/36) is the principal MTL
parahippocampal region for object-level recognition memory. Distinct
from postrhinal (POR -- context/scene memory) and entorhinal cortex
(EC -- gateway to hippocampus).

Burwell 2001 established PRH/POR cytoarchitectural boundaries. PRH
processes object/item information; POR processes spatial/context
information. Both project to hippocampus via lateral and medial
entorhinal cortex respectively, providing dual streams that bind into
context-dependent episodic memory.

KEY FINDINGS
============
1. Perirhinal + postrhinal cortex distinct cytoarchitecture; PRH
   processes object info, POR processes spatial info -- anatomical +
   functional dissociation -- [Burwell 2001, J Comp Neurol 437:17,
   doi:10.1002/cne.1267]
2. PRH is necessary + sufficient for object familiarity / recency
   memory; selective lesion impairs object recognition without
   spatial deficits -- [Brown 2001, Hippocampus 11:467, PMID 11530851]
3. Repetition-suppression in PRH neurons signals familiarity; novel
   objects elicit strong response, repeated objects show reduction --
   [Xiang 1998, Neuropharmacology 37:657, PMID 9707378]
4. PRH->lateral EC->hippocampus is the canonical "what" stream; POR->
   medial EC->hippocampus is the "where" stream -- convergent on
   hippocampus -- [Eichenbaum 2007, Annu Rev Neurosci 30:123,
   doi:10.1146/annurev.neuro.30.051606.094328]
5. PRH lesion impairs object-in-context discrimination; intact PRH
   required for binding object identity to context --
   [Norman 2003, Hippocampus 13:299, PMID 12699335]

INPUTS
======
- VentralPosteromedialThalamus.vpm_relay (sensory input)
- LateralGeniculateNucleus.lgn_relay (visual)
- HippocampalCA1Output.ca1_drive (memory feedback)
- LocusCoeruleusCore.lc_phasic_burst (novelty consolidation)
- SensoryConvergenceProxy.object_signal (placeholder)

OUTPUTS
=======
- prh_drive (0-1)
- familiarity_signal (0-1) -- high for familiar, low for novel
- novelty_signal (0-1) -- opposite of familiarity
- object_identity_code (0-1) -- encoded item info to lateral EC
- prh_state (str): "novel_object" | "familiar_object" |
  "memory_recall" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PerirhinalCortex(BrainMechanism):
    """PRH -- object/familiarity memory hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    NOVEL_THRESHOLD = 0.50
    FAMILIAR_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="PerirhinalCortex",
            human_analog="Perirhinal cortex (object familiarity memory)",
            layer="limbic",
        )
        self.state.setdefault("prh_drive", self.BASELINE)
        self.state.setdefault("familiarity_signal", 0.5)
        self.state.setdefault("novelty_signal", 0.0)
        self.state.setdefault("object_identity_code", 0.0)
        self.state.setdefault("prh_state", "quiet")
        self.state.setdefault("recent_objects", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vpm: float, lgn: float, ca1: float,
                       object_sig: float, lc: float) -> float:
        """PRH firing -- sensory + memory + LC novelty consolidation."""
        target = self.BASELINE + vpm * 0.20 + lgn * 0.20 + object_sig * 0.30
        target += ca1 * 0.20 + lc * 0.10
        return min(1.0, target)

    def _familiarity(self, object_sig: float, recent_objects: list) -> float:
        """Familiarity signal -- repetition suppression analog (Xiang 1998).
        Object recently seen = high familiarity; novel = low."""
        if object_sig < 0.20:
            return 0.5  # Neutral baseline
        if not recent_objects:
            return 0.10  # No history = novel
        # Match against recent objects (simplified: signal-similarity
        # based on rounded magnitude)
        similar_count = sum(1 for o in recent_objects[-30:]
                              if abs(o - object_sig) < 0.15)
        if similar_count == 0:
            return 0.10
        return min(1.0, 0.30 + similar_count * 0.05)

    def _novelty(self, familiarity: float) -> float:
        """Novelty = inverse of familiarity (Brown 2001)."""
        return max(0.0, 1.0 - familiarity)

    def _object_identity_code(self, prh_drive: float, object_sig: float) -> float:
        """Object identity code -> lateral EC -> hippocampus (Eichenbaum 2007)."""
        return min(1.0, prh_drive * 0.5 + object_sig * 0.5)

    def _classify_state(self, novelty: float, familiarity: float,
                          ca1: float, drive: float) -> str:
        if drive < 0.15:
            return "quiet"
        if novelty > self.NOVEL_THRESHOLD:
            return "novel_object"
        if ca1 > 0.40:
            return "memory_recall"
        if familiarity > self.FAMILIAR_THRESHOLD:
            return "familiar_object"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vpm_data = prior.get("VentralPosteromedialThalamus", {})
        vpm = float(vpm_data.get("vpm_relay", 0.0))

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        lgn = float(lgn_data.get("lgn_relay", lgn_data.get("v1_relay", 0.0)))

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        sensory_data = prior.get("SensoryConvergenceProxy", {})
        object_sig = float(sensory_data.get("object_signal", lgn))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc = float(lc_data.get("lc_phasic_burst", 0.0))

        target = self._drive_target(vpm, lgn, ca1, object_sig, lc)
        prev_drive = float(self.state.get("prh_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        recent = list(self.state.get("recent_objects", []))
        familiarity = self._familiarity(object_sig, recent)
        novelty = self._novelty(familiarity)
        identity_code = self._object_identity_code(new_drive, object_sig)

        # Track recent object signals for familiarity
        if object_sig > 0.20:
            recent.append(round(object_sig, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        state = self._classify_state(novelty, familiarity, ca1, new_drive)

        self.state["prh_drive"] = round(new_drive, 4)
        self.state["familiarity_signal"] = round(familiarity, 4)
        self.state["novelty_signal"] = round(novelty, 4)
        self.state["object_identity_code"] = round(identity_code, 4)
        self.state["prh_state"] = state
        self.state["recent_objects"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "prh_drive": round(new_drive, 4),
            "familiarity_signal": round(familiarity, 4),
            "novelty_signal": round(novelty, 4),
            "object_identity_code": round(identity_code, 4),
            "prh_state": state,
        }

    def _what_stream_output(self, identity_code: float) -> float:
        """PRH -> lateral EC "what" stream output (Eichenbaum 2007)."""
        return min(1.0, identity_code * 0.85)

    def _recognition_confidence(self, familiarity: float,
                                novelty: float) -> float:
        """Recognition confidence -- how confident is PRH that
        this object has been seen before? High familiarity + low
        novelty = high confidence; high novelty = low confidence."""
        if familiarity < 0.20 and novelty < 0.20:
            return 0.5
        return 1.0 - novelty * 0.7 + familiarity * 0.3

    def _associative_binding_strength(self, familiarity: float,
                                      novelty: float) -> float:
        """Associative binding strength -- PRH binds object
        identity with context. Novel objects form new associations
        more readily (Martin 2001)."""
        if novelty < 0.20:
            return 0.0
        return min(1.0, novelty * 0.6 + familiarity * 0.2)

    def _semantic_consolidation_trigger(self, familiarity: float,
                                         novelty: float,
                                         tick_count: int) -> float:
        """Semantic consolidation trigger -- repeated exposure
        to familiar objects gradually consolidates them into
        semantic (not episodic) memory over many repetitions."""
        if familiarity < 0.30:
            return 0.0
        if tick_count < 50:
            return 0.0
        consolidation = (tick_count - 50) / 1000.0
        return min(1.0, consolidation * familiarity)

    def _perirhinal_piriform_interface(self, object_sig: float,
                                       familiarity: float) -> float:
        """Perirhinal-piriform interface -- PRH and Piriform
        cortex share object identity processing. Strong object
        signal + low familiarity may drive olfactory-object
        associative learning (Haberly 2001)."""
        if object_sig < 0.20:
            return 0.0
        return min(1.0, object_sig * (1.0 - familiarity * 0.5))

    def _object_work_memory_load(self, recent_objects: list,
                                 novelty: float) -> float:
        """Object working memory load -- how many distinct
        objects are currently held in PRH short-term buffer.
        High load reduces encoding of new objects."""
        if not recent_objects:
            return 0.0
        distinct = len(set(round(x, 2) for x in recent_objects[-20:]))
        load = distinct / 10.0
        if novelty > 0.50:
            load *= 1.3
        return min(1.0, load)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("prh_drive", 0.0),
            "familiarity": self.state.get("familiarity_signal", 0.5),
            "novelty": self.state.get("novelty_signal", 0.0),
            "state": self.state.get("prh_state", "quiet"),
        }

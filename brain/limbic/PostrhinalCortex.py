"""
PostrhinalCortex -- POR / Spatial Context + Scene Memory

NEURAL SUBSTRATE
================
Postrhinal cortex (POR, rodent homolog of primate parahippocampal cortex)
is the principal MTL parahippocampal region for spatial context + scene
memory. Distinct from PRH which processes object/item information.

POR is densely connected with retrosplenial cortex, visual cortex, and
medial entorhinal cortex (MEC). It feeds spatial information into MEC →
hippocampus, providing the "where" stream of the dual-stream MTL model
(Eichenbaum 2007). Critical for context-dependent memory and scene
recognition.

Furtak 2007 demonstrated POR is necessary for context-fear learning
beyond the contribution of hippocampus alone.

KEY FINDINGS
============
1. PRH/POR cytoarchitectural and connectional dissociation; POR is
   the spatial/context counterpart to PRH object/item function --
   [Burwell 2001, J Comp Neurol 437:17, doi:10.1002/cne.1267]
2. POR neurons encode spatial scene + context information; respond to
   place + scene structure, not specific objects --
   [Furtak 2007, Cereb Cortex 17:1577, doi:10.1093/cercor/bhl069]
3. POR→medial EC→hippocampus is the canonical "where" stream;
   complements PRH→lateral EC "what" stream -- [Eichenbaum 2007,
   Annu Rev Neurosci 30:123, doi:10.1146/annurev.neuro.30.051606.094328]
4. POR lesion impairs context-fear conditioning beyond what
   hippocampus alone supports -- [Bucci 2002, Hippocampus 12:447,
   PMID 12184185]
5. POR processes panoramic visual scenes; primate parahippocampal
   place area (PPA) is functional homolog --
   [Aguirre 1998, Neuron 21:373, PMID 9728920]

INPUTS
======
- LateralGeniculateNucleus.lgn_relay (visual)
- RetrosplenialCortexProxy.rsc_drive (default 0; spatial integration)
- HippocampalCA1Output.ca1_drive (memory feedback)
- SuperiorColliculusOrient.orienting_command (saccade-driven scene change)

OUTPUTS
=======
- por_drive (0-1)
- context_signal (0-1) -- encoded spatial context
- scene_recognition_signal (0-1)
- mec_command (0-1) -- output to medial entorhinal "where" stream
- por_state (str): "novel_context" | "familiar_context" |
  "context_recall" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PostrhinalCortex(BrainMechanism):
    """POR -- spatial context / scene memory hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    NOVEL_CONTEXT_THRESHOLD = 0.50
    FAMILIAR_THRESHOLD = 0.30

    def __init__(self):
        super().__init__(
            name="PostrhinalCortex",
            human_analog="Postrhinal cortex (spatial context + scene)",
            layer="limbic",
        )
        self.state.setdefault("por_drive", self.BASELINE)
        self.state.setdefault("context_signal", 0.0)
        self.state.setdefault("scene_recognition_signal", 0.0)
        self.state.setdefault("mec_command", 0.0)
        self.state.setdefault("por_state", "quiet")
        self.state.setdefault("recent_contexts", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, lgn: float, rsc: float, ca1: float,
                       sc: float) -> float:
        """POR firing -- visual scene + retrosplenial spatial integration."""
        target = self.BASELINE + lgn * 0.30 + rsc * 0.25 + ca1 * 0.20
        target += sc * 0.15
        return min(1.0, target)

    def _context_signal(self, drive: float, lgn: float, rsc: float) -> float:
        """Context signal -- combined visual scene + spatial integration."""
        return min(1.0, drive * 0.4 + lgn * 0.3 + rsc * 0.3)

    def _scene_recognition(self, context: float, recent_contexts: list) -> float:
        """Scene recognition -- match current context against recent
        contexts (Furtak 2007 scene recognition)."""
        if context < 0.20 or not recent_contexts:
            return 0.10
        recent = recent_contexts[-30:]
        if not recent:
            return 0.10
        similar = sum(1 for c in recent if abs(c - context) < 0.15)
        return min(1.0, 0.30 + similar * 0.05)

    def _mec_command(self, context: float, drive: float) -> float:
        """POR → MEC "where" stream output (Eichenbaum 2007)."""
        return min(1.0, context * 0.5 + drive * 0.5)

    def _classify_state(self, context: float, scene_rec: float,
                          ca1: float, drive: float) -> str:
        if drive < 0.15:
            return "quiet"
        if context > self.NOVEL_CONTEXT_THRESHOLD and scene_rec < 0.20:
            return "novel_context"
        if ca1 > 0.40:
            return "context_recall"
        if scene_rec > self.FAMILIAR_THRESHOLD:
            return "familiar_context"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        lgn = float(lgn_data.get("lgn_relay", lgn_data.get("v1_relay", 0.0)))

        rsc_data = prior.get("RetrosplenialCortexProxy", {})
        rsc = float(rsc_data.get("rsc_drive", 0.0))

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        sc_data = prior.get("SuperiorColliculusOrient", {})
        sc = float(sc_data.get("orienting_command",
                          sc_data.get("sc_orienting_command", 0.0)))

        target = self._drive_target(lgn, rsc, ca1, sc)
        prev_drive = float(self.state.get("por_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        context = self._context_signal(new_drive, lgn, rsc)

        recent = list(self.state.get("recent_contexts", []))
        scene_rec = self._scene_recognition(context, recent)

        mec_cmd = self._mec_command(context, new_drive)

        if context > 0.20:
            recent.append(round(context, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        state = self._classify_state(context, scene_rec, ca1, new_drive)

        self.state["por_drive"] = round(new_drive, 4)
        self.state["context_signal"] = round(context, 4)
        self.state["scene_recognition_signal"] = round(scene_rec, 4)
        self.state["mec_command"] = round(mec_cmd, 4)
        self.state["por_state"] = state
        self.state["recent_contexts"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "por_drive": round(new_drive, 4),
            "context_signal": round(context, 4),
            "scene_recognition_signal": round(scene_rec, 4),
            "mec_command": round(mec_cmd, 4),
            "por_state": state,
        }

    def _where_stream_output(self, context: float, mec_cmd: float) -> float:
        """POR → MEC "where" stream (Eichenbaum 2007)."""
        return min(1.0, context * 0.5 + mec_cmd * 0.5)

    def _context_change_detection(self, current_context: float,
                                     recent_contexts: list) -> float:
        """Detect rapid context change (e.g., entering new room).
        Returns magnitude of context shift."""
        if not recent_contexts or len(recent_contexts) < 3:
            return 0.0
        prev_avg = sum(recent_contexts[-3:]) / 3
        return min(1.0, abs(current_context - prev_avg) * 2.0)

    def _spatial_context_familiarity(self, context_signal: float,
                                        recent_contexts: list) -> float:
        """Familiarity of current spatial context -- high when current
        context matches recent history, low for novel environments."""
        if not recent_contexts or context_signal < 0.20:
            return 0.0
        recent_avg = sum(recent_contexts[-20:]) / max(1, len(recent_contexts[-20:]))
        familiarity = 1.0 - min(1.0, abs(context_signal - recent_avg) * 2.0)
        return familiarity

    def _viewpoint_invariance_strength(self, scene_rec: float,
                                       context_signal: float) -> float:
        """Viewpoint invariance -- POR can recognize scenes from novel
        viewpoints due to invariant spatial layout coding (Aguirre 1998)."""
        if scene_rec < 0.20:
            return 0.0
        return min(1.0, scene_rec * context_signal * 1.2)

    def _scene_object_binding_strength(self, scene_rec: float,
                                       context_signal: float) -> float:
        """Scene-object binding -- POR integrates spatial layout with
        object identity for scene recognition."""
        if scene_rec < 0.20 or context_signal < 0.20:
            return 0.0
        return min(1.0, (scene_rec + context_signal) * 0.6)

    def _navigation_goal_signal(self, context_signal: float,
                                 recall: float) -> float:
        """Navigation goal signal -- episodic memory can retrieve
        navigation goals from scene context."""
        if recall < 0.20 or context_signal < 0.20:
            return 0.0
        return min(1.0, context_signal * recall * 1.5)


    def _allocentric_spatial_code(self, context_signal: float) -> float:
        """Allocentric spatial code -- POR represents spatial
        relationships independent of current viewpoint (Furtak 2007).
        Returns strength of allocentric spatial representation."""
        if context_signal < 0.20:
            return 0.0
        return min(1.0, context_signal * 0.85)

    def _environmental_affordance_signal(self, scene_rec: float,
                                          context_signal: float) -> float:
        """Environmental affordance -- scenes afford actions. POR
        integrates scene recognition with spatial layout to signal
        available actions in current environment."""
        if scene_rec < 0.20:
            return 0.0
        return min(1.0, scene_rec * context_signal * 1.2)

    def _context_sequence_prediction(self, recent_contexts: list,
                                     context_signal: float) -> float:
        """Context sequence prediction -- POR can predict next
        context based on sequence history. High when context
        sequence is highly predictable."""
        if len(recent_contexts) < 5 or context_signal < 0.20:
            return 0.0
        recent_avg = sum(recent_contexts[-5:]) / 5
        predictability = 1.0 - min(1.0, abs(context_signal - recent_avg) * 3.0)
        return predictability

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("por_drive", 0.0),
            "context": self.state.get("context_signal", 0.0),
            "scene_rec": self.state.get("scene_recognition_signal", 0.0),
            "state": self.state.get("por_state", "quiet"),
        }

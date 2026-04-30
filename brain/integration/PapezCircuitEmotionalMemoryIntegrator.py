"""
PapezCircuitEmotionalMemoryIntegrator — Full Papez Loop Closure

NEURAL SUBSTRATE
================
The Papez circuit, first proposed by James Papez in 1937 and refined by
MacLean's limbic system formulation, is the canonical anatomical loop
linking emotional and episodic memory:

  Hippocampus (subiculum) → fornix → mammillary bodies →
  mammillothalamic tract → anterior thalamic nuclei (AV/AD/AM) →
  cingulum → cingulate cortex → entorhinal cortex → hippocampus

The full circuit closes back on itself, creating a reverberatory loop
that supports the consolidation of episodic context with affective
content. Aggleton 2010 reviewed the circuit as central to anterograde
amnesia syndromes — damage to ANY node (mammillary, anterior thalamus,
cingulate, hippocampus, fornix) produces memory impairment specific
to spatial/episodic content.

Functional model: Papez closure binds (1) hippocampal what/where, (2)
anterior-thalamic head-direction, (3) cingulate context-emotion, (4)
mammillary timing-prediction into a coherent episodic memory trace.
The closure rate determines how strongly memory traces consolidate.

Vann 2009 demonstrated mammillary body lesion alone produces
catastrophic memory deficits — establishing mammillary as not just a
relay but a critical computational node. Bubb 2017 emphasized that
the cingulum bundle (Papez return arm) is the most-disrupted tract
in early Alzheimer's.

KEY FINDINGS
============
1. Papez circuit links hippocampus, mammillary bodies, anterior thalamus, and cingulate cortex; substrate for episodic memory consolidation — [Aggleton JP 2010, Behav Brain Res 215:197, doi:10.1016/j.bbr.2010.04.023]
2. Mammillary body lesion alone produces severe anterograde amnesia; not merely a relay but critical computational node — [Vann SD 2009, Hippocampus 19:1192, doi:10.1002/hipo.20614]
3. Cingulum bundle (Papez return arm) most-disrupted tract in early Alzheimer's; tract-level signature — [Bubb EJ 2017, Brain 140:e44, doi:10.1093/brain/awx153]
4. Modern update: cortico-limbo-thalamo-cortical circuit revises Papez with bidirectional thalamocingulate connectivity — [Catani M 2023, Brain Topogr 36:371, doi:10.1007/s10548-023-00955-y]
5. James Papez 1937 proposal of cingulate-mammillary-thalamic loop as substrate of emotion + memory; foundational anatomical formulation — [Papez JW 1937, Arch Neurol Psychiatry 38:725, doi:10.1001/archneurpsyc.1937.02260220069003]

INPUTS (from prior_results)
============================
- HippocampalCA1Dorsal.subicular_output (or SubiculumDorsal)
- MammillaryBody / Foundational053 — fornix relay
- AnteroVentralThalamus.atn_drive (Papez thalamic node)
- AnteroDorsalThalamus.head_direction_signal
- CingulateAnterior.acc_drive
- CingulatePosterior.pcc_drive
- EntorhinalCortexGridCells.ec_output (return arm)

OUTPUTS (to brain_runner enrichment)
=====================================
- papez_drive (0-1)
- loop_closure_strength (0-1) — full circuit reverberation
- consolidation_signal (0-1) — episodic memory consolidation index
- amnesic_node_failure (0-1) — proxy for which node, if any, breaks
- thalamocingulate_signal (0-1) — Papez output arm
- papez_state (str): "consolidating" | "partial_loop" |
  "amnesic_break" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PapezCircuitEmotionalMemoryIntegrator(BrainMechanism):
    """Papez circuit — full loop closure for episodic-emotional memory."""

    BASELINE = 0.0
    SMOOTH = 0.20
    CONSOLIDATION_THRESHOLD = 0.45
    LOOP_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="PapezCircuitEmotionalMemoryIntegratorVariant",
            human_analog="Papez circuit (episodic-emotional memory loop)",
            layer="integration",
        )
        self.state.setdefault("papez_drive", 0.0)
        self.state.setdefault("loop_closure_strength", 0.0)
        self.state.setdefault("consolidation_signal", 0.0)
        self.state.setdefault("amnesic_node_failure", 0.0)
        self.state.setdefault("thalamocingulate_signal", 0.0)
        self.state.setdefault("papez_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("consolidation_accumulator", 0.0)
        self.state.setdefault("tick_count", 0)

    def _node_health(self, hpc: float, mam: float, atn: float,
                       cing: float, ec: float) -> float:
        """Health of weakest Papez node — Vann 2009 showed mammillary
        lesion alone breaks the circuit; the loop is only as strong as
        its weakest link."""
        nodes = [hpc, mam, atn, cing, ec]
        return min(nodes)

    def _amnesic_break(self, hpc: float, mam: float, atn: float,
                         cing: float, ec: float) -> float:
        """Detect node failure — if any node is critically below input
        threshold while others are active, it's a 'break' point.
        Aggleton 2010 — any node damage produces anterograde amnesia."""
        nodes = {"hpc": hpc, "mam": mam, "atn": atn,
                  "cing": cing, "ec": ec}
        active_nodes = sum(1 for v in nodes.values() if v > 0.20)
        if active_nodes < 2:
            return 0.0  # circuit not engaged at all
        # Find the gap between max and min when most are active
        active_vals = [v for v in nodes.values() if v > 0.05]
        if not active_vals:
            return 0.0
        max_v = max(active_vals)
        min_v = min(active_vals)
        if max_v - min_v > 0.50 and active_nodes >= 3:
            # Big gap — one node is failing while others fire
            return min(1.0, (max_v - min_v) * 1.2)
        return 0.0

    def _loop_closure(self, hpc: float, mam: float, atn: float,
                        cing: float, ec: float) -> float:
        """Full circuit closure — product across nodes (multiplicative
        because failure at any node breaks the loop)."""
        product = hpc * mam * atn * cing * ec
        # Take the 5th root to normalize to comparable scale
        if product <= 0:
            return 0.0
        return min(1.0, product ** 0.2 * 1.4)

    def _thalamocingulate(self, atn: float, cing: float) -> float:
        """Anterior thalamic → cingulate output arm (Catani 2023)."""
        return min(1.0, atn * 0.55 + cing * 0.45)

    def _consolidation(self, prev_accum: float, closure: float) -> float:
        """Slow consolidation accumulator — builds with sustained loop
        closure. Aggleton 2010 — episodic consolidation requires
        repeated traversal."""
        if closure < 0.30:
            return prev_accum * 0.97  # slow decay if loop weak
        return min(1.0, prev_accum * 0.97 + closure * 0.04)

    def _drive_target(self, closure: float, hpc: float,
                       cing: float) -> float:
        """Papez drive — primarily closure, with anchor on entry/exit
        nodes."""
        return min(1.0, closure * 0.6 + hpc * 0.2 + cing * 0.2)

    def _classify_state(self, drive: float, closure: float,
                          consolidation: float, amnesic: float) -> str:
        if drive < 0.10:
            return "quiet"
        if amnesic > 0.40:
            return "amnesic_break"
        if consolidation > self.CONSOLIDATION_THRESHOLD:
            return "consolidating"
        if closure > self.LOOP_THRESHOLD:
            return "consolidating"
        return "partial_loop"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        hpc_data = prior.get("HippocampalCA1Dorsal", {})
        if not hpc_data:
            hpc_data = prior.get("SubiculumDorsal", {})
        if not hpc_data:
            hpc_data = prior.get("HippocampalCA1", {})
        hpc = float(hpc_data.get("subicular_output",
                          hpc_data.get("ca1d_drive",
                            hpc_data.get("dsub_drive", 0.0))))

        mam_data = prior.get("MammillaryBody", {})
        if not mam_data:
            mam_data = prior.get("Foundational053MammillaryBodyOutput", {})
        mam = float(mam_data.get("mammillary_drive",
                          mam_data.get("mam_drive", 0.0)))

        atn_data = prior.get("AnteroVentralThalamus", {})
        if not atn_data:
            atn_data = prior.get("AnteriorThalamicPapez", {})
        atn = float(atn_data.get("atn_drive",
                          atn_data.get("anterior_thalamic_drive", 0.0)))

        cing_data = prior.get("CingulateAnterior", {})
        cing_a = float(cing_data.get("acc_drive", 0.0))
        cing_p_data = prior.get("CingulatePosterior", {})
        cing_p = float(cing_p_data.get("pcc_drive", 0.0))
        cing = max(cing_a, cing_p)

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        if not ec_data:
            ec_data = prior.get("EntorhinalLayer3", {})
        ec = float(ec_data.get("ec_output",
                          ec_data.get("temporoammonic_signal",
                            ec_data.get("ec3_drive", 0.0))))

        closure = self._loop_closure(hpc, mam, atn, cing, ec)
        amnesic = self._amnesic_break(hpc, mam, atn, cing, ec)
        thalamocingulate = self._thalamocingulate(atn, cing)

        target = self._drive_target(closure, hpc, cing)
        prev_drive = float(self.state.get("papez_drive", 0.0))
        new_drive = self._smooth(prev_drive, target)

        prev_accum = float(self.state.get("consolidation_accumulator", 0.0))
        consolidation = self._consolidation(prev_accum, closure)

        state = self._classify_state(new_drive, closure, consolidation,
                                       amnesic)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["papez_drive"] = round(new_drive, 4)
        self.state["loop_closure_strength"] = round(closure, 4)
        self.state["consolidation_signal"] = round(consolidation, 4)
        self.state["consolidation_accumulator"] = round(consolidation, 4)
        self.state["amnesic_node_failure"] = round(amnesic, 4)
        self.state["thalamocingulate_signal"] = round(thalamocingulate, 4)
        self.state["papez_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "papez_drive": round(new_drive, 4),
            "loop_closure_strength": round(closure, 4),
            "consolidation_signal": round(consolidation, 4),
            "amnesic_node_failure": round(amnesic, 4),
            "thalamocingulate_signal": round(thalamocingulate, 4),
            "papez_state": state,
        }

    def _alzheimer_signature(self, recent_states: list) -> float:
        """Sustained amnesic_break = Alzheimer/Korsakoff signature
        (Bubb 2017 cingulum disruption)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        a = sum(1 for s in win if s == "amnesic_break")
        return a / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("papez_drive", 0.0),
            "closure": self.state.get("loop_closure_strength", 0.0),
            "consolidation": self.state.get("consolidation_signal", 0.0),
            "state": self.state.get("papez_state", "quiet"),
        }

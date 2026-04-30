"""
EntorhinalCortexGridCells -- EC Grid / Border / Object-Vector Cells, Hippocampal Entry

NEURAL SUBSTRATE
================
The entorhinal cortex (EC) is the principal cortical interface to the
hippocampal formation. EC sits at the medial-temporal junction and is
divided into medial entorhinal cortex (MEC) and lateral entorhinal
cortex (LEC) with distinct functional content. MEC layer II/III neurons
project the perforant path to dentate gyrus and CA3 (and direct to CA1
in layer III), and LEC layer II projects to DG outer molecular layer.
Output from CA1 returns to deep EC layers, completing the
hippocampal-entorhinal loop.

MEC layer II contains the Nobel-discovered **grid cells** (Hafting,
Fyhn, Molden, Moser & Moser 2005, Nature) -- neurons whose place
fields tile space in a hexagonal lattice. Grid cell firing fields
form regular triangular arrays that span the environment, providing
a metric coordinate system for navigation. Grid scale increases
along the dorsoventral axis of MEC, generating multi-scale spatial
representation. The 2014 Nobel Prize was awarded to O'Keefe and the
Mosers for place and grid cells.

MEC also contains **border cells** (firing along environmental edges),
**head-direction cells** (firing as a function of facing direction,
similar to AD/LMN), and **speed cells** (firing rate scaling with
running speed). LEC contains **object cells** and **object-trace cells**
that encode non-spatial / item information; LEC integrates olfactory
input and emits an "what" signal complementing MEC's "where" signal.

The Tolman-Eichenbaum-Machine framework (Whittington et al. 2020 Cell)
positions EC grid cells as the substrate for cognitive-map abstraction --
the hexagonal coordinate system generalizes beyond physical space to
relational structure (social hierarchies, conceptual graphs). Recent
fMRI and MEG work (Bao et al. 2019 Nat Neurosci) suggests grid-like
codes operate in human conceptual reasoning.

In Nova's substrate this provides the entorhinal entry to hippocampus --
combines locomotion proxy, head-direction signals, and object/cue
proxies into a multi-scale spatial code feeding DG/CA3/CA1 mechanisms.

KEY FINDINGS
============
1. Grid cells in MEC layer II fire in regular hexagonal lattices
   tiling 2D space -- Nobel-winning discovery -- [Hafting Fyhn Molden
    Moser Moser 2005, Nature 436:801-806, "Microstructure of a spatial
    map in the entorhinal cortex"]
2. Grid scale increases along the dorsoventral axis of MEC, providing
   multi-scale spatial coding -- [Stensola et al. 2012, Nature
    492:72-78, "The entorhinal grid map is discretized"]
3. MEC contains border cells (Solstad 2008 Science 322:1865) and
   head-direction cells alongside grid cells -- comprehensive spatial
   representation system -- [Solstad Boccara Kropff Moser Moser 2008,
    Science 322:1865-1868, "Representation of geographical borders
    in entorhinal cortex"]
4. LEC encodes object/item information complementing MEC's spatial
   code -- "what vs where" dissociation -- [Tsao et al. 2018, Nature
    561:57-62, "Integrating time from experience in the lateral
    entorhinal cortex"; reviewed Knierim 2014 Hippocampus 24:1399]
5. Grid cells generalize beyond physical space to abstract relational
   structure -- cognitive-map function -- [Constantinescu O'Reilly
    Behrens 2016, Science 352:1464-1468, "Organizing conceptual
    knowledge in humans with a gridlike code"; Whittington et al.
    2020, Cell 183:1249, "The Tolman-Eichenbaum Machine"]

INPUTS (from prior_results)
============================
- LocomotionProxy.locomotion_speed
- LocomotionProxy.heading_change (optional)
- LocomotionProxy.boundary_proximity (optional)
- HippocampalContextProxy.context_novelty
- HippocampalContextProxy.familiarity
- AnteriorThalamicPapez.head_direction_relay
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_active
- ValenceTagger.valence_intensity (object salience proxy)
- OlfactoryBulbProxy.glomerular_drive (optional; default 0)

OUTPUTS (to brain_runner enrichment)
=====================================
- mec_grid_drive (0.0-1.0): MEC layer II/III grid cell ensemble
- lec_object_drive (0.0-1.0): LEC object/item encoding
- border_cell_signal (0.0-1.0): MEC border cell engagement
- speed_cell_drive (0.0-1.0): MEC speed cell output
- ec_dg_perforant_drive (0.0-1.0): EC → DG perforant path output
- ec_ca1_direct_drive (0.0-1.0): EC layer III → CA1 direct projection
- multi_scale_phase (0.0-1.0): grid-phase signal
- ec_state (str): "what_drive" | "where_drive" | "boundary" | "stationary" | "off"

brain_runner enrichment:
    ec = all_results.get("EntorhinalCortexGridCells", {})
    if ec:
        enrichments["brain_mec_grid"] = ec.get("mec_grid_drive", 0.2)
        enrichments["brain_lec_object"] = ec.get("lec_object_drive", 0.2)
        enrichments["brain_ec_dg_perforant"] = ec.get("ec_dg_perforant_drive", 0.0)
        enrichments["brain_ec_ca1_direct"] = ec.get("ec_ca1_direct_drive", 0.0)
        enrichments["brain_ec_state"] = ec.get("ec_state", "stationary")
"""

import math

from brain.base_mechanism import BrainMechanism


class EntorhinalCortexGridCells(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="EntorhinalCortexGridCells",
            human_analog="Entorhinal cortex (MEC grid + LEC object) hippocampal entry",
            layer="foundational",
        )
        self.state.setdefault("mec_grid_drive", self.BASELINE)
        self.state.setdefault("lec_object_drive", self.BASELINE)
        self.state.setdefault("border_cell_signal", 0.0)
        self.state.setdefault("speed_cell_drive", 0.0)
        self.state.setdefault("ec_dg_perforant_drive", 0.0)
        self.state.setdefault("ec_ca1_direct_drive", 0.0)
        self.state.setdefault("multi_scale_phase", 0.0)
        self.state.setdefault("ec_state", "stationary")
        self.state.setdefault("grid_phase_acc", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _mec_grid_target(self, locomotion: float, heading: float, theta_active: bool,
                          hd_relay: float) -> float:
        """MEC grid drive -- engaged with locomotion, theta state, head direction."""
        target = self.BASELINE
        target += locomotion * 0.4
        target += abs(heading) * 0.2
        target += hd_relay * 0.2
        if theta_active:
            target += 0.10
        return min(1.0, target)

    def _lec_object_target(self, valence: float, novelty: float, olfactory: float) -> float:
        """LEC object -- engaged by salient objects/items + olfactory cues."""
        target = self.BASELINE + valence * 0.4 + novelty * 0.3 + olfactory * 0.3
        return min(1.0, target)

    def _border_cell(self, boundary: float, locomotion: float, mec: float) -> float:
        """MEC border cells -- firing along environmental edges (Solstad 2008)."""
        if boundary < 0.10:
            return 0.0
        return min(1.0, boundary * 0.7 + mec * 0.2 + locomotion * 0.1)

    def _speed_cell(self, locomotion: float) -> float:
        """MEC speed cells -- rate scales with running speed."""
        return min(1.0, locomotion * 0.95)

    def _grid_phase_advance(self, prev_phase: float, locomotion: float, heading: float) -> float:
        """Multi-scale grid phase -- advances with locomotion (proxy)."""
        if locomotion < 0.05:
            return prev_phase
        delta = locomotion * 0.10 + abs(heading) * 0.05
        return (prev_phase + delta) % 1.0

    def _ec_dg_perforant(self, mec: float, lec: float) -> float:
        """EC layer II → DG perforant path -- combined what+where."""
        return min(1.0, mec * 0.5 + lec * 0.4)

    def _ec_ca1_direct(self, mec: float, lec: float, theta_active: bool) -> float:
        """EC layer III → CA1 direct (TA pathway, theta-modulated)."""
        target = mec * 0.4 + lec * 0.3
        if theta_active:
            target += 0.20
        return min(1.0, target)

    def _classify_state(self, mec: float, lec: float, border: float, locomotion: float) -> str:
        if border > 0.40:
            return "boundary"
        if locomotion > 0.30 and mec > 0.30:
            return "where_drive"
        if lec > mec and lec > 0.30:
            return "what_drive"
        if locomotion < 0.15 and mec < 0.30:
            return "stationary"
        return "stationary"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        heading = float(loco.get("heading_change", 0.0))
        boundary = float(loco.get("boundary_proximity", 0.0))

        ctx = prior.get("HippocampalContextProxy", {})
        novelty = float(ctx.get("context_novelty", 0.0))
        familiarity = float(ctx.get("familiarity", 0.5))

        atn = prior.get("AnteriorThalamicPapez", {})
        hd_relay = float(atn.get("head_direction_relay", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        valence = prior.get("ValenceTagger", {})
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        olf = prior.get("OlfactoryBulbProxy", {})
        olfactory = float(olf.get("glomerular_drive", 0.0))

        # --- MEC grid ---
        mec_target = self._mec_grid_target(locomotion, heading, theta_active, hd_relay)
        prev_mec = float(self.state.get("mec_grid_drive", self.BASELINE))
        new_mec = self._smooth(prev_mec, mec_target)

        # --- LEC object ---
        lec_target = self._lec_object_target(valence_intensity, novelty, olfactory)
        prev_lec = float(self.state.get("lec_object_drive", self.BASELINE))
        new_lec = self._smooth(prev_lec, lec_target)

        # --- Border ---
        border = self._border_cell(boundary, locomotion, new_mec)

        # --- Speed ---
        speed = self._speed_cell(locomotion)

        # --- Grid phase ---
        prev_phase = float(self.state.get("grid_phase_acc", 0.0))
        new_phase = self._grid_phase_advance(prev_phase, locomotion, heading)

        # --- Outputs ---
        perforant = self._ec_dg_perforant(new_mec, new_lec)
        ca1_direct = self._ec_ca1_direct(new_mec, new_lec, theta_active)

        # --- State ---
        state = self._classify_state(new_mec, new_lec, border, locomotion)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mec_grid_drive"] = round(new_mec, 4)
        self.state["lec_object_drive"] = round(new_lec, 4)
        self.state["border_cell_signal"] = round(border, 4)
        self.state["speed_cell_drive"] = round(speed, 4)
        self.state["ec_dg_perforant_drive"] = round(perforant, 4)
        self.state["ec_ca1_direct_drive"] = round(ca1_direct, 4)
        self.state["multi_scale_phase"] = round(new_phase, 4)
        self.state["ec_state"] = state
        self.state["grid_phase_acc"] = round(new_phase, 4)
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mec_grid_drive": round(new_mec, 4),
            "lec_object_drive": round(new_lec, 4),
            "border_cell_signal": round(border, 4),
            "speed_cell_drive": round(speed, 4),
            "ec_dg_perforant_drive": round(perforant, 4),
            "ec_ca1_direct_drive": round(ca1_direct, 4),
            "multi_scale_phase": round(new_phase, 4),
            "ec_state": state,
        }

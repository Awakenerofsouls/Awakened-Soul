"""
MiddleTemporalArea — V5 / MT / Middle Temporal Visual Area

NEURAL SUBSTRATE
================
The middle temporal area (MT, also called V5) is a heavily myelinated
visual area in the posterior superior temporal sulcus of macaque (and
the lateral occipital cortex / V5+ complex in human). MT is the
canonical motion-processing hub of the dorsal "where/how" stream.

Inputs to MT:
  - V1 layer 4B (magnocellular pathway) — direct projection.
  - V2 thick stripes (also magnocellular).
  - V3 (motion-sensitive feedforward).
  - Pulvinar (subcortical motion route, bypasses V1).

Outputs:
  - MST (medial superior temporal) — optic flow, heading, smooth pursuit.
  - LIP (lateral intraparietal) — saccade targets in motion.
  - FEF — pursuit eye movements.
  - VIP — multimodal motion / near space.

Functional properties:
  - Direction-selective columns: ~95% of MT neurons are
    direction-selective (Albright 1984), with adjacent columns
    encoding adjacent preferred directions in a continuous map.
  - Speed tuning with peak ~8-32 deg/s typical.
  - Pattern vs component motion: ~25% of MT cells respond to true
    plaid pattern direction rather than each grating component
    (Movshon et al. 1985).
  - Coherence sensitivity: MT firing scales linearly with motion
    coherence in random-dot kinematograms (Britten et al. 1992); MT
    sensitivity matches monkey behavioral threshold (Newsome et al.
    1989); microstimulation biases choices (Salzman & Newsome).
  - Speed/depth integration in MT/MST for self-motion (Born & Bradley
    2005).

KEY FINDINGS
============
1. ~95% of MT neurons are direction-selective; adjacent cortical
   patches encode adjacent preferred directions, forming a columnar
   directional map —
   [Albright TD 1984, J Neurophysiol 52:1106, doi:10.1152/jn.1984.52.6.1106]
2. MT firing rate scales linearly with motion coherence in random-dot
   stimuli; single MT-neuron sensitivity ≈ behavioral threshold —
   [Britten KH 1992, J Neurosci 12:4745, PMID 1464765]
3. MT lesions and microstimulation causally alter motion-direction
   judgments, demonstrating MT's role in motion perception —
   [Newsome WT 1989, Nature 341:52, doi:10.1038/341052a0]
4. ~25% of MT cells signal pattern (plaid) motion rather than each
   grating component — first cortical stage of true 2-D motion —
   [Movshon JA 1985, Pattern Recognition Mech p117, doi:10.1007/978-3-642-70535-7_8]
5. Structure and function of MT review: dorsal-stream architecture for
   motion / self-motion / pursuit —
   [Born RT 2005, Annu Rev Neurosci 28:157, doi:10.1146/annurev.neuro.26.041002.131052]

INPUTS
======
- PrimaryVisualCortex.magno_to_v2 (layer 4B → MT shortcut)
- SecondaryVisualCortex.mt_input_signal (V2 thick stripes)
- PulvinarAttentionVisual.pulvinar_modulation (subcortical motion)

OUTPUTS
=======
- mt_drive (0-1)
- direction_signal (0-1) — direction-selective column pool
- coherence_signal (0-1) — RDM-style coherence readout
- optic_flow_signal (0-1) — MST-bound optic flow drive
- mst_input_signal (0-1) — MT → MST
- lip_input_signal (0-1) — MT → LIP (motion → priority)
- mt_state (str): "coherent_motion" | "incoherent_motion"
                  | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class MiddleTemporalArea(BrainMechanism):
    """V5/MT — direction selectivity, motion coherence, optic flow."""

    BASELINE = 0.08
    SMOOTH = 0.22
    COHERENT_THRESHOLD = 0.50
    INCOHERENT_THRESHOLD = 0.25
    ENGAGED_THRESHOLD = 0.18
    QUIET_THRESHOLD = 0.13

    NUM_DIRECTION_COLUMNS = 8  # 8 preferred directions, 45 deg spacing

    def __init__(self):
        super().__init__(
            name="MiddleTemporalArea",
            human_analog="V5 / MT / hMT+ complex",
            layer="neocortical",
        )
        self.state.setdefault("mt_drive", self.BASELINE)
        self.state.setdefault("direction_signal", 0.0)
        self.state.setdefault("coherence_signal", 0.0)
        self.state.setdefault("optic_flow_signal", 0.0)
        self.state.setdefault("mst_input_signal", 0.0)
        self.state.setdefault("lip_input_signal", 0.0)
        self.state.setdefault("mt_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v1_magno: float, v2_mt: float,
                       pulv: float) -> float:
        """Pooled MT drive — magno-dominated (Born 2005)."""
        target = (self.BASELINE
                  + v1_magno * 0.40
                  + v2_mt * 0.40
                  + pulv * 0.15)
        return min(1.0, target)

    def _direction_selective(self, drive: float, magno: float) -> float:
        """Direction-selective columnar pool (Albright 1984)."""
        # ~95% of MT cells are direction-selective; pool firing scales
        # with magnocellular drive.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, drive * 0.55 + magno * 0.40)

    def _coherence_readout(self, drive: float, dir_sig: float) -> float:
        """Random-dot motion coherence sensitivity (Britten 1992)."""
        # Linear scaling with coherence, threshold-matched to behavior.
        # Modeled as direction-pool consistency: high direction signal
        # with high drive → high coherence readout.
        if drive < 0.18:
            return 0.0
        return min(1.0, dir_sig * (drive + 0.10) * 1.1)

    def _optic_flow(self, drive: float, dir_sig: float,
                     pulv: float) -> float:
        """Optic-flow / self-motion drive to MST (Born 2005)."""
        # Optic flow emerges from spatially organized direction
        # readouts; pulvinar provides attentional gain.
        if drive < 0.20:
            return 0.0
        return min(1.0, dir_sig * 0.55 + drive * 0.25 + pulv * 0.20)

    def _mst_input(self, flow: float, coherence: float) -> float:
        """MT → MST projection (heading, pursuit, large-field motion)."""
        return min(1.0, flow * 0.60 + coherence * 0.40)

    def _lip_input(self, dir_sig: float, coherence: float,
                    drive: float) -> float:
        """MT → LIP projection (motion-evidence to priority map)."""
        # Roitman & Shadlen 2002: MT → LIP carries direction evidence
        # for accumulator decision in RDM tasks.
        return min(1.0, dir_sig * 0.40 + coherence * 0.45 + drive * 0.15)

    def _classify_state(self, drive: float, coherence: float,
                         dir_sig: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if coherence > self.COHERENT_THRESHOLD:
            return "coherent_motion"
        if dir_sig > self.INCOHERENT_THRESHOLD and coherence < self.INCOHERENT_THRESHOLD:
            return "incoherent_motion"
        if drive > self.ENGAGED_THRESHOLD:
            return "engaged"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v1_data = prior.get("PrimaryVisualCortex", {})
        if not v1_data:
            v1_data = prior.get("V1", {})
        v1_magno = float(v1_data.get("magno_to_v2",
                              v1_data.get("complex_cell_signal", 0.0)))

        v2_data = prior.get("SecondaryVisualCortex", {})
        if not v2_data:
            v2_data = prior.get("V2", {})
        v2_mt = float(v2_data.get("mt_input_signal",
                            v2_data.get("thick_stripe_signal", 0.0)))

        pulv_data = prior.get("PulvinarAttentionVisual", {})
        if not pulv_data:
            pulv_data = prior.get("Pulvinar", {})
        pulv = float(pulv_data.get("pulvinar_modulation",
                            pulv_data.get("attention_gain", 0.0)))

        target = self._drive_target(v1_magno, v2_mt, pulv)
        prev_drive = float(self.state.get("mt_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        dir_sig = self._direction_selective(new_drive, v1_magno)
        coherence = self._coherence_readout(new_drive, dir_sig)
        flow = self._optic_flow(new_drive, dir_sig, pulv)
        mst_in = self._mst_input(flow, coherence)
        lip_in = self._lip_input(dir_sig, coherence, new_drive)
        state = self._classify_state(new_drive, coherence, dir_sig)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mt_drive"] = round(new_drive, 4)
        self.state["direction_signal"] = round(dir_sig, 4)
        self.state["coherence_signal"] = round(coherence, 4)
        self.state["optic_flow_signal"] = round(flow, 4)
        self.state["mst_input_signal"] = round(mst_in, 4)
        self.state["lip_input_signal"] = round(lip_in, 4)
        self.state["mt_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mt_drive": round(new_drive, 4),
            "direction_signal": round(dir_sig, 4),
            "coherence_signal": round(coherence, 4),
            "optic_flow_signal": round(flow, 4),
            "mst_input_signal": round(mst_in, 4),
            "lip_input_signal": round(lip_in, 4),
            "mt_state": state,
        }

    def _direction_column_count(self) -> int:
        return self.NUM_DIRECTION_COLUMNS

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("mt_drive", 0.0),
            "direction": self.state.get("direction_signal", 0.0),
            "coherence": self.state.get("coherence_signal", 0.0),
            "flow": self.state.get("optic_flow_signal", 0.0),
            "state": self.state.get("mt_state", "quiet"),
        }

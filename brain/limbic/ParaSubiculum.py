"""
ParaSubiculum — PaSb / Parahippocampal Border Zone

NEURAL SUBSTRATE
================
The parasubiculum (PaSb) is a narrow strip of cortex along the
medial border of the entorhinal cortex, between presubiculum and
medial entorhinal cortex (MEC). PaSb hosts a mixture of grid cells,
head-direction cells, and theta-modulated cells — a "shoulder" between
the spatial PrPS/MEC computation. PaSb pyramidal cells project to MEC
layers I-II and provide both HD and theta signals to grid cell circuits.

Boccara 2010 demonstrated grid cells in parasubiculum (alongside MEC),
showing that grid coding extends beyond MEC. PaSb additionally provides
a strong source of theta-pacing input to MEC stellate cells, supporting
their grid-cell oscillatory coding mechanism.

KEY FINDINGS
============
1. Grid cells exist in parasubiculum alongside medial entorhinal
   cortex; PaSb is part of grid-cell network —
   [Boccara 2010, Nat Neurosci 13:987, doi:10.1038/nn.2602]
2. PaSb projects strongly to MEC layer II stellate cells; provides
   theta and HD pacing —
   [Caballero-Bleda 1993, J Comp Neurol 339:341, doi:10.1002/cne.903390306]
3. PaSb pyramidal cells exhibit theta-modulated firing essential for
   downstream MEC oscillatory coding —
   [Tang 2016, Cell Reports 14:2607, doi:10.1016/j.celrep.2016.02.063]
4. PaSb is a major source of HD-modulated drive into MEC,
   complementing presubicular HD input —
   [Boccara 2010, Nat Neurosci 13:987, doi:10.1038/nn.2602]
5. Selective parasubicular lesion impairs spatial learning + reduces
   MEC grid-cell stability —
   [Liu 2018, eLife 7:e29473, doi:10.7554/eLife.29473]

INPUTS
======
- PrePresubiculum.head_direction_signal
- MedialSeptum.theta_signal (or DiagonalBandBroca.theta_drive)
- AnteriorThalamicPapez.atn_drive

OUTPUTS
=======
- pasb_drive (0-1)
- mec_theta_pacing (0-1)
- mec_hd_input (0-1)
- grid_supportive_signal (0-1)
- pasb_state (str): "theta_pacing" | "hd_active" | "grid_supporting" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ParaSubiculum(BrainMechanism):
    """PaSb — parasubicular grid/HD/theta border zone."""

    BASELINE = 0.10
    SMOOTH = 0.20
    GRID_SUPPORT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="ParaSubiculum",
            human_analog="Parasubiculum (parahippocampal border)",
            layer="limbic",
        )
        self.state.setdefault("pasb_drive", self.BASELINE)
        self.state.setdefault("mec_theta_pacing", 0.0)
        self.state.setdefault("mec_hd_input", 0.0)
        self.state.setdefault("grid_supportive_signal", 0.0)
        self.state.setdefault("pasb_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, hd: float, theta: float, atn: float) -> float:
        """PaSb drive (Boccara 2010)."""
        target = (self.BASELINE
                  + hd * 0.35
                  + theta * 0.30
                  + atn * 0.20)
        return min(1.0, target)

    def _theta_pacing(self, drive: float, theta: float) -> float:
        """PaSb→MEC theta pacing (Tang 2016)."""
        if theta < 0.15:
            return drive * 0.20
        return min(1.0, drive * 0.5 + theta * 0.5)

    def _hd_input(self, drive: float, hd: float) -> float:
        """PaSb→MEC HD input (Boccara 2010)."""
        if hd < 0.15:
            return drive * 0.20
        return min(1.0, drive * 0.4 + hd * 0.6)

    def _grid_support(self, theta_pace: float, hd_in: float) -> float:
        """Grid coding support = theta * hd convergence (Liu 2018)."""
        return min(1.0, theta_pace * hd_in * 1.6)

    def _classify_state(self, drive: float, theta_pace: float,
                         hd_in: float, grid_support: float) -> str:
        if drive < 0.20:
            return "quiet"
        if grid_support > self.GRID_SUPPORT_THRESHOLD:
            return "grid_supporting"
        if theta_pace > 0.40:
            return "theta_pacing"
        if hd_in > 0.40:
            return "hd_active"
        return "theta_pacing"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        prps_data = prior.get("PrePresubiculum", {})
        if not prps_data:
            prps_data = prior.get("Postsubiculum", {})
        hd = float(prps_data.get("head_direction_signal",
                          prps_data.get("prps_drive", 0.0)))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        atn_data = prior.get("AnteriorThalamicPapez", {})
        atn = float(atn_data.get("atn_drive",
                          atn_data.get("anterior_thalamic_drive", 0.0)))

        target = self._drive_target(hd, theta, atn)
        prev_drive = float(self.state.get("pasb_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        theta_pace = self._theta_pacing(new_drive, theta)
        hd_in = self._hd_input(new_drive, hd)
        grid_support = self._grid_support(theta_pace, hd_in)

        state = self._classify_state(new_drive, theta_pace, hd_in,
                                      grid_support)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pasb_drive"] = round(new_drive, 4)
        self.state["mec_theta_pacing"] = round(theta_pace, 4)
        self.state["mec_hd_input"] = round(hd_in, 4)
        self.state["grid_supportive_signal"] = round(grid_support, 4)
        self.state["pasb_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pasb_drive": round(new_drive, 4),
            "mec_theta_pacing": round(theta_pace, 4),
            "mec_hd_input": round(hd_in, 4),
            "grid_supportive_signal": round(grid_support, 4),
            "pasb_state": state,
        }

    def _grid_stability_index(self) -> float:
        """How well PaSb supports MEC grid stability (Liu 2018)."""
        return float(self.state.get("grid_supportive_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pasb_drive", 0.0),
            "theta": self.state.get("mec_theta_pacing", 0.0),
            "hd": self.state.get("mec_hd_input", 0.0),
            "state": self.state.get("pasb_state", "quiet"),
        }

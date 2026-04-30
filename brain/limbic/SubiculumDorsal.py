"""
SubiculumDorsal — dSub / Spatial Output of Hippocampus

NEURAL SUBSTRATE
================
The dorsal subiculum (dSub) is the principal output structure of the
dorsal hippocampus, receiving CA1 projections and broadcasting to
mammillary bodies, anterior thalamic nuclei, retrosplenial cortex, and
EC-V. dSub pyramidal cells include "boundary vector cells" (Lever 2009),
"axis cells", and grid-cell-modulated projection neurons. Output is
critical for spatial navigation and the Papez circuit (anterior thalamus
→ cingulate → entorhinal).

Two cell-type populations: regular-spiking and burst-firing pyramids,
with distinct projection targets (Kim 2012). dSub bursting neurons
project to mammillary bodies and contribute to head-direction signal
generation; regular-spiking neurons project to anterior thalamus.

KEY FINDINGS
============
1. Subiculum pyramidal cells project to mammillary bodies, anterior
   thalamus, retrosplenial cortex — Papez circuit gateway —
   [Aggleton 1986, J Comp Neurol 243:409, doi:10.1002/cne.902430310]
2. Boundary vector cells (BVCs) in subiculum encode distance + direction
   to environmental boundaries; geometric coding —
   [Lever 2009, J Neurosci 29:9771, doi:10.1523/JNEUROSCI.1319-09.2009]
3. Subicular pyramids divide into burst-firing vs regular-spiking
   populations with distinct projection targets —
   [Kim 2012, Hippocampus 22:693, doi:10.1002/hipo.20931]
4. Subiculum lesion impairs allocentric navigation while sparing simple
   spatial discrimination —
   [Morris 1990, Eur J Neurosci 2:1016, PMID 12106084]
5. Subiculum neurons exhibit theta-coupled firing essential for
   hippocampal-cortical synchrony —
   [Anderson 2001, Hippocampus 11:439, doi:10.1002/hipo.1059]

INPUTS
======
- HippocampalCA1Dorsal.ca1d_drive (or subicular_output)
- EntorhinalCortexGridCells.ec_output (perforant path)
- MedialSeptum.theta_signal

OUTPUTS
=======
- dsub_drive (0-1)
- mammillary_body_drive (0-1)
- anterior_thalamic_drive (0-1)
- ec5_drive_signal (0-1)
- boundary_vector_signal (0-1)
- dsub_state (str): "boundary_active" | "burst_firing" | "papez_engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SubiculumDorsal(BrainMechanism):
    """dSub — spatial hippocampal output / Papez gateway."""

    BASELINE = 0.10
    SMOOTH = 0.20
    BURST_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="SubiculumDorsal",
            human_analog="Dorsal subiculum (Papez gateway)",
            layer="limbic",
        )
        self.state.setdefault("dsub_drive", self.BASELINE)
        self.state.setdefault("mammillary_body_drive", 0.0)
        self.state.setdefault("anterior_thalamic_drive", 0.0)
        self.state.setdefault("ec5_drive_signal", 0.0)
        self.state.setdefault("boundary_vector_signal", 0.0)
        self.state.setdefault("dsub_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ca1: float, ec: float, theta: float) -> float:
        """Subicular pyramid drive (Aggleton 1986)."""
        target = (self.BASELINE
                  + ca1 * 0.50
                  + ec * 0.25
                  + theta * 0.10)
        return min(1.0, target)

    def _mammillary(self, drive: float, theta: float) -> float:
        """Burst-firing → mammillary bodies (Kim 2012)."""
        if drive < self.BURST_THRESHOLD:
            return 0.0
        return min(1.0, drive * 0.7 + theta * 0.2)

    def _anterior_thalamic(self, drive: float, ca1: float) -> float:
        """Regular-spiking → anterior thalamic nuclei (Aggleton 1986)."""
        return min(1.0, drive * 0.55 + ca1 * 0.35)

    def _boundary_vector(self, drive: float, ec: float) -> float:
        """BVC activity (Lever 2009) — depends on EC grid input."""
        if drive < 0.20 or ec < 0.20:
            return 0.0
        return min(1.0, drive * ec * 1.5)

    def _ec5_drive(self, drive: float) -> float:
        """Subicular → EC-V output."""
        return min(1.0, drive * 0.85)

    def _classify_state(self, drive: float, mammillary: float,
                         bvc: float, theta: float) -> str:
        if drive < 0.20:
            return "quiet"
        if mammillary > 0.40:
            return "burst_firing"
        if bvc > 0.30:
            return "boundary_active"
        if theta > 0.40:
            return "papez_engaged"
        return "papez_engaged"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ca1_data = prior.get("HippocampalCA1Dorsal", {})
        if not ca1_data:
            ca1_data = prior.get("HippocampalCA1", {})
        ca1 = float(ca1_data.get("ca1d_drive",
                          ca1_data.get("subicular_output",
                            ca1_data.get("ca1_output", 0.0))))

        ec_data = prior.get("EntorhinalCortexGridCells", {})
        ec = float(ec_data.get("ec_output",
                          ec_data.get("grid_cell_signal", 0.0)))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        target = self._drive_target(ca1, ec, theta)
        prev_drive = float(self.state.get("dsub_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        mammillary = self._mammillary(new_drive, theta)
        ant_thal = self._anterior_thalamic(new_drive, ca1)
        bvc = self._boundary_vector(new_drive, ec)
        ec5 = self._ec5_drive(new_drive)

        state = self._classify_state(new_drive, mammillary, bvc, theta)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dsub_drive"] = round(new_drive, 4)
        self.state["mammillary_body_drive"] = round(mammillary, 4)
        self.state["anterior_thalamic_drive"] = round(ant_thal, 4)
        self.state["ec5_drive_signal"] = round(ec5, 4)
        self.state["boundary_vector_signal"] = round(bvc, 4)
        self.state["dsub_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dsub_drive": round(new_drive, 4),
            "sub_drive": round(new_drive, 4),  # alias
            "mammillary_body_drive": round(mammillary, 4),
            "anterior_thalamic_drive": round(ant_thal, 4),
            "ec5_drive_signal": round(ec5, 4),
            "boundary_vector_signal": round(bvc, 4),
            "dsub_state": state,
        }

    def _papez_drive_strength(self) -> float:
        """Papez circuit engagement (Aggleton 1986)."""
        return float(self.state.get("anterior_thalamic_drive", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("dsub_drive", 0.0),
            "mammillary": self.state.get("mammillary_body_drive", 0.0),
            "thalamic": self.state.get("anterior_thalamic_drive", 0.0),
            "state": self.state.get("dsub_state", "quiet"),
        }

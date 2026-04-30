"""
PrimaryVisualCortex — V1 / Striate Cortex (Brodmann Area 17)

NEURAL SUBSTRATE
================
V1 (primary visual cortex / striate cortex / area 17 / area OC) occupies
the calcarine sulcus of the occipital lobe. It is the first cortical
recipient of visual information from the retina via the lateral
geniculate nucleus (LGN). V1 has a six-layer laminar organization with
distinct cytoarchitectonic features: a prominent layer 4 subdivided
into 4A, 4B, 4Cα (magnocellular input) and 4Cβ (parvocellular input),
plus the stria of Gennari (myelinated band in layer 4B that gives
"striate" cortex its name).

V1 is organized as a precise retinotopic map: the central visual field
is heavily over-represented (cortical magnification factor) at the
occipital pole, with peripheral vision mapped further anteriorly along
the calcarine sulcus. Within each ~1 mm² of cortex, V1 contains
orientation columns, ocular dominance columns, and color blobs (the
cytochrome-oxidase blobs in layers 2/3) — Hubel & Wiesel's "ice cube"
hypercolumn architecture.

Functionally, V1 contains:
  - Simple cells: oriented receptive fields with separate ON/OFF
    subregions, linear summation, sensitive to position.
  - Complex cells: orientation-selective but position-invariant within
    receptive field, often direction-selective.
  - Hypercomplex / end-stopped cells: sensitive to length / line ends.
  - Blob cells: color-opponent (parvo input), unoriented, in CO blobs.

V1 outputs split into two parallel streams via V2: the ventral
("what") stream toward V4 → IT for object/form/color, and the dorsal
("where/how") stream via thick stripes toward V5/MT → posterior
parietal cortex for motion and spatial vision (Ungerleider & Mishkin
1982).

KEY FINDINGS
============
1. Hubel & Wiesel discovered orientation-selective simple and complex
   cells in cat striate cortex; receptive fields differ from concentric
   retinal/LGN type —
   [Hubel DH 1962, J Physiol 160:106, doi:10.1113/jphysiol.1962.sp006837]
2. Functional architecture of monkey striate cortex: orientation
   columns and ocular dominance columns form a regular hypercolumn
   tiling —
   [Hubel DH 1968, J Physiol 195:215, doi:10.1113/jphysiol.1968.sp008455]
3. Sparse-coding learning on natural images yields V1-like localized,
   oriented, bandpass simple-cell receptive fields, predicting V1's
   role in efficient coding —
   [Olshausen BA 1996, Nature 381:607, doi:10.1038/381607a0]
4. Mouse V1 contains orientation-selective neurons with sharp tuning
   and salt-and-pepper map (no columns), establishing rodent V1 as a
   tractable model —
   [Niell CM 2008, J Neurosci 28:7520, doi:10.1523/JNEUROSCI.0623-08.2008]
5. Normalization model of V1 explains contrast gain control,
   cross-orientation suppression, and surround suppression as
   canonical cortical computation —
   [Carandini M 2012, Nat Rev Neurosci 13:51, doi:10.1038/nrn3136]

INPUTS
======
- LateralGeniculateNucleus.lgn_drive (LGN relay; magno + parvo + konio)
- LateralGeniculateNucleus.magno_signal (magnocellular)
- LateralGeniculateNucleus.parvo_signal (parvocellular)
- PulvinarAttentionVisual.pulvinar_modulation (cortico-pulvino-cortical)

OUTPUTS
=======
- v1_drive (0-1) — overall V1 activation
- simple_cell_signal (0-1) — oriented simple-cell pool
- complex_cell_signal (0-1) — phase-invariant complex-cell pool
- orientation_tuning (0-1) — sharpness of orientation selectivity
- magno_to_v2 (0-1) — feeds V2 thick stripes → dorsal stream
- parvo_to_v2 (0-1) — feeds V2 thin/inter stripes → ventral stream
- retinotopy_signal (0-1) — retinotopic map activation
- v1_state (str): "high_contrast" | "oriented_active" | "low_contrast"
                  | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrimaryVisualCortex(BrainMechanism):
    """V1 — orientation columns, simple/complex cells, retinotopic map."""

    BASELINE = 0.08
    SMOOTH = 0.22
    HIGH_CONTRAST_THRESHOLD = 0.55
    ORIENTED_THRESHOLD = 0.30
    QUIET_THRESHOLD = 0.15

    # Hubel & Wiesel hypercolumn parameters
    NUM_ORIENTATIONS = 8  # 0, 22.5, 45, ..., 157.5 degrees
    NUM_OCULAR_COLUMNS = 2  # left/right eye

    def __init__(self):
        super().__init__(
            name="PrimaryVisualCortex",
            human_analog="V1 / Striate cortex (Brodmann area 17)",
            layer="neocortical",
        )
        self.state.setdefault("v1_drive", self.BASELINE)
        self.state.setdefault("simple_cell_signal", 0.0)
        self.state.setdefault("complex_cell_signal", 0.0)
        self.state.setdefault("orientation_tuning", 0.0)
        self.state.setdefault("magno_to_v2", 0.0)
        self.state.setdefault("parvo_to_v2", 0.0)
        self.state.setdefault("retinotopy_signal", 0.0)
        self.state.setdefault("v1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("contrast_history", [])

    def _drive_target(self, lgn: float, magno: float, parvo: float,
                       pulv: float) -> float:
        """Pooled V1 drive — LGN dominates, pulvinar gates (Hubel 1962)."""
        # LGN is the main feedforward source; magno + parvo summed give
        # full bandwidth. Pulvinar provides modulatory gain.
        target = (self.BASELINE
                  + lgn * 0.35
                  + magno * 0.20
                  + parvo * 0.20
                  + pulv * 0.15)
        return min(1.0, target)

    def _simple_cell_response(self, drive: float, parvo: float) -> float:
        """Simple cells: oriented, linear, parvo-driven (Hubel 1962)."""
        # Simple cells in 4Cβ receive parvo input; linear summation of
        # ON/OFF subregions yields position-sensitive oriented response.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, drive * 0.55 + parvo * 0.45)

    def _complex_cell_response(self, drive: float, magno: float,
                                 simple: float) -> float:
        """Complex cells: phase-invariant pool of simple cells."""
        # Complex cells pool over simple cells with similar orientation
        # but different positions — yields position invariance within RF.
        # Layer 4B complex cells receive magno drive (motion-sensitive).
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, simple * 0.55 + magno * 0.30 + drive * 0.15)

    def _orientation_tuning(self, drive: float, simple: float) -> float:
        """Sharpness of orientation tuning (Carandini 2012 normalization)."""
        # Tuning sharpens with contrast via divisive normalization;
        # cross-orientation suppression yields ~30-40 deg HWHH typical.
        if drive < 0.10:
            return 0.0
        # Normalization: tuning rises with simple/complex pool activity
        norm = drive + 0.20  # semi-saturation
        return min(1.0, simple / norm * 0.85)

    def _magno_to_v2(self, complex_sig: float, magno: float) -> float:
        """V1 → V2 thick stripe / dorsal stream (motion, depth)."""
        # Layer 4B → V2 thick stripes → MT/V5
        return min(1.0, complex_sig * 0.50 + magno * 0.50)

    def _parvo_to_v2(self, simple: float, parvo: float) -> float:
        """V1 → V2 thin/inter stripes / ventral stream (form, color)."""
        # Layers 2/3 blobs (color) + interblobs (form) → V2 → V4 → IT
        return min(1.0, simple * 0.55 + parvo * 0.45)

    def _retinotopy(self, drive: float) -> float:
        """Retinotopic map activation (precise visual field mapping)."""
        # V1 has the most precise retinotopy of any cortical area;
        # cortical magnification heavily favors fovea.
        return min(1.0, drive * 0.95)

    def _classify_state(self, drive: float, simple: float,
                         complex_sig: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if drive > self.HIGH_CONTRAST_THRESHOLD:
            return "high_contrast"
        if simple > self.ORIENTED_THRESHOLD or complex_sig > self.ORIENTED_THRESHOLD:
            return "oriented_active"
        return "low_contrast"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        if not lgn_data:
            lgn_data = prior.get("LGN", {})
        lgn = float(lgn_data.get("lgn_drive",
                          lgn_data.get("relay_signal", 0.0)))
        magno = float(lgn_data.get("magno_signal",
                            lgn_data.get("magnocellular", 0.0)))
        parvo = float(lgn_data.get("parvo_signal",
                            lgn_data.get("parvocellular", 0.0)))

        pulv_data = prior.get("PulvinarAttentionVisual", {})
        if not pulv_data:
            pulv_data = prior.get("Pulvinar", {})
        pulv = float(pulv_data.get("pulvinar_modulation",
                            pulv_data.get("attention_gain", 0.0)))

        target = self._drive_target(lgn, magno, parvo, pulv)
        prev_drive = float(self.state.get("v1_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        simple = self._simple_cell_response(new_drive, parvo)
        complex_sig = self._complex_cell_response(new_drive, magno, simple)
        tuning = self._orientation_tuning(new_drive, simple)
        magno_v2 = self._magno_to_v2(complex_sig, magno)
        parvo_v2 = self._parvo_to_v2(simple, parvo)
        retinotopy = self._retinotopy(new_drive)
        state = self._classify_state(new_drive, simple, complex_sig)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        contrast_hist = list(self.state.get("contrast_history", []))
        contrast_hist.append(round(new_drive, 4))
        if len(contrast_hist) > 30:
            contrast_hist = contrast_hist[-30:]

        self.state["v1_drive"] = round(new_drive, 4)
        self.state["simple_cell_signal"] = round(simple, 4)
        self.state["complex_cell_signal"] = round(complex_sig, 4)
        self.state["orientation_tuning"] = round(tuning, 4)
        self.state["magno_to_v2"] = round(magno_v2, 4)
        self.state["parvo_to_v2"] = round(parvo_v2, 4)
        self.state["retinotopy_signal"] = round(retinotopy, 4)
        self.state["v1_state"] = state
        self.state["recent_states"] = recent
        self.state["contrast_history"] = contrast_hist
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "v1_drive": round(new_drive, 4),
            "simple_cell_signal": round(simple, 4),
            "complex_cell_signal": round(complex_sig, 4),
            "orientation_tuning": round(tuning, 4),
            "magno_to_v2": round(magno_v2, 4),
            "parvo_to_v2": round(parvo_v2, 4),
            "retinotopy_signal": round(retinotopy, 4),
            "v1_state": state,
        }

    def _hypercolumn_count(self) -> int:
        """Number of hypercolumns (orientations × ocular)."""
        return self.NUM_ORIENTATIONS * self.NUM_OCULAR_COLUMNS

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("v1_drive", 0.0),
            "simple": self.state.get("simple_cell_signal", 0.0),
            "complex": self.state.get("complex_cell_signal", 0.0),
            "tuning": self.state.get("orientation_tuning", 0.0),
            "state": self.state.get("v1_state", "quiet"),
        }

"""
SecondaryVisualCortex — V2 / Brodmann Area 18 (Prestriate Cortex)

NEURAL SUBSTRATE
================
V2 surrounds V1 anteriorly and is the second cortical visual area in
the hierarchy. Cytochrome-oxidase staining of V2 reveals a striking
parallel-stripe organization perpendicular to the V1/V2 border:
  - Thin (CO-dense) stripes — receive V1 blob input → process color,
    project to V4.
  - Thick (CO-dense) stripes — receive V1 layer 4B input → process
    disparity, motion, project to V5/MT (dorsal stream).
  - Pale interstripes (CO-light) — receive V1 interblob input → process
    form/orientation, project to V4 (ventral stream).
This stripe architecture (Sincich & Horton 2002, Livingstone & Hubel
1988) is the anatomical substrate for the early bifurcation of the
ventral ("what") and dorsal ("where/how") streams (Ungerleider &
Mishkin 1982).

V2 neurons exhibit emergent properties absent (or weak) in V1:
  - Border-ownership coding: a single V2 neuron fires differently for
    the same local edge depending on which side of the edge belongs to
    the foreground figure (Zhou et al. 2000) — first neural correlate
    of figure/ground assignment.
  - Illusory contour responses: V2 cells respond to subjective contours
    (Kanizsa-figure type) where no luminance edge exists in the RF (von
    der Heydt et al. 1984).
  - Complex orientation combinations: angles, curves, junctions (Anzai
    et al. 2007).
  - Disparity tuning across larger ranges than V1.

V2 thus performs early mid-level vision: surface segmentation,
figure/ground, contour completion — bridging local V1 features and
object-level V4/IT representations.

KEY FINDINGS
============
1. Border-ownership cells in V2 (and V4) signal which side of an edge
   owns the contour; >50% of V2 cells modulated by figure side —
   [Zhou H 2000, J Neurosci 20:6594, PMID 10964965]
2. Neurons in V2 (area 18) of alert monkeys respond to illusory
   contours (Kanizsa-square edges) as if real — V1 does not —
   [Heydt R 1984, Science 224:1260, PMID 6539501]
3. V2 stripe architecture: thin / thick / pale interstripes are
   distinct anatomical compartments with parallel V1 input and
   downstream targets —
   [Sincich LC 2002, J Neurosci 22:5684, PMID 12097520]
4. V2 neurons exhibit selectivity for combinations of orientations
   (angles and curves), an intermediate-level shape representation
   absent in V1 —
   [Anzai A 2007, Nat Neurosci 10:1313, doi:10.1038/nn1975]
5. Two cortical visual systems: ventral occipitotemporal "what" stream
   and dorsal occipitoparietal "where" stream split through V2 —
   [Mishkin M 1983, Trends Neurosci 6:414, doi:10.1016/0166-2236(83)90190-X]

INPUTS
======
- PrimaryVisualCortex.v1_drive (general V1 activation)
- PrimaryVisualCortex.magno_to_v2 (→ thick stripes / dorsal)
- PrimaryVisualCortex.parvo_to_v2 (→ thin & pale stripes / ventral)
- PrimaryVisualCortex.complex_cell_signal (V1 layer 4B / 2/3 output)

OUTPUTS
=======
- v2_drive (0-1)
- thick_stripe_signal (0-1) — dorsal-bound (motion/disparity)
- thin_stripe_signal (0-1) — ventral-bound color
- pale_stripe_signal (0-1) — ventral-bound form
- border_ownership_signal (0-1) — figure/ground assignment
- illusory_contour_signal (0-1) — subjective contour detection
- v4_input_signal (0-1) — V2 → V4 (ventral stream)
- mt_input_signal (0-1) — V2 → MT (dorsal stream)
- v2_state (str): "border_active" | "illusory_active" | "engaged" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SecondaryVisualCortex(BrainMechanism):
    """V2 — border-ownership, illusory contours, V1 → ventral/dorsal split."""

    BASELINE = 0.08
    SMOOTH = 0.22
    BORDER_THRESHOLD = 0.40
    ILLUSORY_THRESHOLD = 0.35
    ENGAGED_THRESHOLD = 0.20
    QUIET_THRESHOLD = 0.15

    def __init__(self):
        super().__init__(
            name="SecondaryVisualCortex",
            human_analog="V2 / Prestriate cortex (Brodmann area 18)",
            layer="neocortical",
        )
        self.state.setdefault("v2_drive", self.BASELINE)
        self.state.setdefault("thick_stripe_signal", 0.0)
        self.state.setdefault("thin_stripe_signal", 0.0)
        self.state.setdefault("pale_stripe_signal", 0.0)
        self.state.setdefault("border_ownership_signal", 0.0)
        self.state.setdefault("illusory_contour_signal", 0.0)
        self.state.setdefault("v4_input_signal", 0.0)
        self.state.setdefault("mt_input_signal", 0.0)
        self.state.setdefault("v2_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v1: float, magno_v2: float, parvo_v2: float,
                       complex_v1: float) -> float:
        """Pooled V2 drive from V1 (Sincich 2002)."""
        target = (self.BASELINE
                  + v1 * 0.30
                  + magno_v2 * 0.25
                  + parvo_v2 * 0.25
                  + complex_v1 * 0.15)
        return min(1.0, target)

    def _thick_stripe(self, magno_v2: float, drive: float) -> float:
        """Thick stripe — dorsal/MT-bound (Sincich 2002)."""
        # Thick stripes carry magnocellular layer-4B input, primarily
        # motion/disparity, and project to MT (V5).
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, magno_v2 * 0.70 + drive * 0.25)

    def _thin_stripe(self, parvo_v2: float, drive: float) -> float:
        """Thin (CO-dense) stripe — ventral/V4-bound color."""
        # Thin stripes carry V1 blob input → color processing → V4.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, parvo_v2 * 0.65 + drive * 0.20)

    def _pale_stripe(self, parvo_v2: float, drive: float) -> float:
        """Pale interstripe — ventral/V4-bound form."""
        # Pale interstripes carry V1 interblob input → form / orientation.
        if drive < self.QUIET_THRESHOLD:
            return 0.0
        return min(1.0, parvo_v2 * 0.55 + drive * 0.30)

    def _border_ownership(self, drive: float, pale: float,
                            thin: float) -> float:
        """Border-ownership cells (Zhou 2000) — figure/ground."""
        # Border-ownership requires both contour (pale stripes) and
        # surface context. >50% of V2 cells show this modulation.
        if drive < 0.20:
            return 0.0
        return min(1.0, pale * 0.45 + thin * 0.25 + drive * 0.30)

    def _illusory_contour(self, drive: float, pale: float,
                            complex_v1: float) -> float:
        """Illusory contour response (von der Heydt 1984)."""
        # V2 cells respond to subjective contours (Kanizsa figures);
        # depends on V1 inducer activity but not local luminance edge.
        if drive < 0.18:
            return 0.0
        # Illusory contour activity when pale stripes are engaged but
        # local V1 complex-cell drive is moderate (inducer-driven).
        induce = pale * 0.50 + complex_v1 * 0.30 + drive * 0.20
        return min(1.0, induce * 0.85)

    def _v4_input(self, thin: float, pale: float, border: float) -> float:
        """V2 → V4 (ventral stream gate)."""
        return min(1.0, thin * 0.35 + pale * 0.40 + border * 0.25)

    def _mt_input(self, thick: float, drive: float) -> float:
        """V2 → MT (dorsal stream gate; Mishkin 1983)."""
        return min(1.0, thick * 0.70 + drive * 0.30)

    def _classify_state(self, drive: float, border: float,
                         illusory: float) -> str:
        if drive < self.QUIET_THRESHOLD:
            return "quiet"
        if border > self.BORDER_THRESHOLD:
            return "border_active"
        if illusory > self.ILLUSORY_THRESHOLD:
            return "illusory_active"
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
        v1 = float(v1_data.get("v1_drive", 0.0))
        magno_v2 = float(v1_data.get("magno_to_v2", 0.0))
        parvo_v2 = float(v1_data.get("parvo_to_v2", 0.0))
        complex_v1 = float(v1_data.get("complex_cell_signal", 0.0))

        target = self._drive_target(v1, magno_v2, parvo_v2, complex_v1)
        prev_drive = float(self.state.get("v2_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        thick = self._thick_stripe(magno_v2, new_drive)
        thin = self._thin_stripe(parvo_v2, new_drive)
        pale = self._pale_stripe(parvo_v2, new_drive)
        border = self._border_ownership(new_drive, pale, thin)
        illusory = self._illusory_contour(new_drive, pale, complex_v1)
        v4_in = self._v4_input(thin, pale, border)
        mt_in = self._mt_input(thick, new_drive)
        state = self._classify_state(new_drive, border, illusory)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["v2_drive"] = round(new_drive, 4)
        self.state["thick_stripe_signal"] = round(thick, 4)
        self.state["thin_stripe_signal"] = round(thin, 4)
        self.state["pale_stripe_signal"] = round(pale, 4)
        self.state["border_ownership_signal"] = round(border, 4)
        self.state["illusory_contour_signal"] = round(illusory, 4)
        self.state["v4_input_signal"] = round(v4_in, 4)
        self.state["mt_input_signal"] = round(mt_in, 4)
        self.state["v2_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "v2_drive": round(new_drive, 4),
            "thick_stripe_signal": round(thick, 4),
            "thin_stripe_signal": round(thin, 4),
            "pale_stripe_signal": round(pale, 4),
            "border_ownership_signal": round(border, 4),
            "illusory_contour_signal": round(illusory, 4),
            "v4_input_signal": round(v4_in, 4),
            "mt_input_signal": round(mt_in, 4),
            "v2_state": state,
        }

    def _stripe_balance(self) -> float:
        """Ventral (thin+pale) vs dorsal (thick) stream ratio."""
        ventral = (self.state.get("thin_stripe_signal", 0.0)
                    + self.state.get("pale_stripe_signal", 0.0))
        dorsal = self.state.get("thick_stripe_signal", 0.0)
        if (ventral + dorsal) < 0.01:
            return 0.5
        return ventral / (ventral + dorsal)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("v2_drive", 0.0),
            "border": self.state.get("border_ownership_signal", 0.0),
            "illusory": self.state.get("illusory_contour_signal", 0.0),
            "ventral_bias": self._stripe_balance(),
            "state": self.state.get("v2_state", "quiet"),
        }

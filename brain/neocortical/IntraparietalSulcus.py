"""
IntraparietalSulcus — IPS / Anterior, Lateral, Medial, Ventral, Caudal IPS

NEURAL SUBSTRATE
================
The intraparietal sulcus (IPS) is a deep furrow on the lateral surface
of the parietal lobe whose banks contain a constellation of functional
subdivisions: anterior IPS (AIP — grasp), lateral IPS (LIP — saccades /
attention), ventral IPS (VIP — peripersonal/multisensory), medial IPS
(MIP — reach / parietal reach region), and caudal IPS (CIP — 3D shape).
Each subdivision implements a different visuomotor transformation that
takes retinal/visual input and remaps it into the coordinate frame of
the relevant effector (eye, hand, head, body).

In humans, IPS contains topographically organized maps (IPS1, IPS2, …)
revealed by retinotopic mapping (Sereno et al. 2001), and is the
canonical neural substrate of non-symbolic numerosity coding: neurons
in the horizontal segment of IPS (HIPS) display tuning curves to
specific numbers of elements (Nieder & Miller 2004). Dehaene's
"three parietal circuits" model places HIPS as the core
quantity-representation system (Dehaene et al. 2003). AIP neurons
selectively encode object shape, size, and orientation for grasping
(Murata et al. 2000), and IPS is required for the dorsal stream's
visually guided actions (Goodale & Milner 1992).

KEY FINDINGS
============
1. Topographic IPS visual maps (IPS1, IPS2 …) revealed by retinotopic
   fMRI in human parietal cortex —
   [Sereno M 2001, Science 294:1350, doi:10.1126/science.1063695]
2. AIP neurons selective for object shape, size, and orientation during
   visually guided grasping —
   [Murata A 2000, J Neurophysiol 83:2580, PMID 10805659]
3. Three parietal circuits for number processing — HIPS as the
   quantity-specific substrate —
   [Dehaene S 2003, Cogn Neuropsychol 20:487, doi:10.1080/02643290244000239]
4. Dorsal-stream visuomotor transformations through parietal cortex
   support visually guided action vs ventral perception —
   [Goodale M 1992, Trends Neurosci 15:20, doi:10.1016/0166-2236(92)90344-8]
5. Tuning curves for approximate numerosity in human intraparietal
   sulcus, peaking at preferred numerosity —
   [Piazza M 2004, Neuron 44:547, doi:10.1016/j.neuron.2004.10.014]

INPUTS
======
- VisualCortexV1.v1_drive (occipital → parietal dorsal stream)
- PulvinarAttentionVisual.pulvinar_drive (attentional gain)
- PrimarySomatosensoryCortex.s1_drive (proprioceptive arm/eye state)
- LateralGeniculateNucleus.lgn_drive (early dorsal feed)
- PosteriorParietalCortex.ppc_drive (PPC partner)

OUTPUTS
=======
- ips_drive (0-1) — overall IPS activation
- aip_grasp_signal (0-1) — anterior IPS grasp (AIP)
- lip_saccade_signal (0-1) — lateral IPS saccade/attention (LIP)
- vip_peripersonal_signal (0-1) — ventral IPS peripersonal (VIP)
- numerosity_signal (0-1) — HIPS quantity coding
- reach_plan (0-1) — IPS reach/visuomotor transformation
- reach_direction (str) — selected target direction
- ips_state (str): "grasping" | "saccade_planning" |
                    "numerosity" | "attending" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class IntraparietalSulcus(BrainMechanism):
    """IPS — visuomotor transforms / numerosity / dorsal stream."""

    BASELINE = 0.07
    SMOOTH = 0.20
    ACTIVE_THRESHOLD = 0.20
    GRASP_THRESHOLD = 0.40
    NUM_THRESHOLD = 0.35
    DIRECTIONS = ("up", "down", "left", "right", "forward", "back")

    def __init__(self):
        super().__init__(
            name="IntraparietalSulcus",
            human_analog="Intraparietal sulcus (AIP, LIP, VIP, MIP, HIPS)",
            layer="neocortical",
        )
        self.state.setdefault("ips_drive", self.BASELINE)
        self.state.setdefault("aip_grasp_signal", 0.0)
        self.state.setdefault("lip_saccade_signal", 0.0)
        self.state.setdefault("vip_peripersonal_signal", 0.0)
        self.state.setdefault("numerosity_signal", 0.0)
        self.state.setdefault("reach_plan", 0.0)
        self.state.setdefault("reach_direction", "none")
        self.state.setdefault("ips_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, v1: float, pulv: float, s1: float,
                      lgn: float, ppc: float) -> float:
        """Composite IPS drive (Sereno 2001, Goodale 1992 — dorsal stream)."""
        # pulvinar provides attentional gain
        gain = 1.0 + pulv * 0.4
        target = (self.BASELINE
                  + v1 * 0.30 * gain
                  + s1 * 0.15
                  + lgn * 0.10
                  + ppc * 0.20)
        return min(1.0, target)

    def _aip_grasp(self, drive: float, v1: float) -> float:
        """AIP grasp / object selectivity (Murata 2000)."""
        if drive < 0.15 or v1 < 0.15:
            return 0.0
        return min(1.0, drive * 0.5 + v1 * 0.5)

    def _lip_saccade(self, drive: float, pulv: float) -> float:
        """LIP saccade / attention (pulvinar-gated)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.5 + pulv * 0.5)

    def _vip_peripersonal(self, drive: float, s1: float, v1: float) -> float:
        """VIP peripersonal/multisensory."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + s1 * 0.3 + v1 * 0.3)

    def _numerosity(self, drive: float, v1: float,
                    upstream: float) -> float:
        """HIPS numerosity tuning (Nieder 2003, Piazza 2004, Dehaene 2003).
        upstream represents an explicit numerosity cue from prior results."""
        if drive < 0.20:
            return 0.0
        # numerosity activity depends on visual element count + IPS engagement
        return min(1.0, drive * 0.4 + v1 * 0.3 + upstream * 0.5)

    def _reach_plan(self, drive: float, aip: float, ppc: float) -> float:
        """MIP reach plan (Goodale 1992 — visuomotor transformation)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + aip * 0.3 + ppc * 0.3)

    def _select_direction(self, plan: float, ppc_dir: str,
                          vis_dir: str) -> str:
        if plan < 0.15:
            return "none"
        if ppc_dir and ppc_dir in self.DIRECTIONS:
            return ppc_dir
        if vis_dir and vis_dir in self.DIRECTIONS:
            return vis_dir
        return "forward"

    def _classify_state(self, drive: float, aip: float, lip: float,
                         num: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if num > self.NUM_THRESHOLD and num >= max(aip, lip):
            return "numerosity"
        if aip > self.GRASP_THRESHOLD and aip >= lip:
            return "grasping"
        if lip > self.GRASP_THRESHOLD:
            return "saccade_planning"
        return "attending"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v1_data = prior.get("VisualCortexV1", {})
        if not v1_data:
            v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive",
                          v1_data.get("v1_signal", 0.0)))
        vis_dir = v1_data.get("salient_direction", "")
        # an upstream numerosity cue (e.g. number of element tokens detected)
        upstream_num = float(v1_data.get("numerosity_cue", 0.0))

        pulv_data = prior.get("PulvinarAttentionVisual", {})
        pulv = float(pulv_data.get("pulvinar_drive",
                            pulv_data.get("attention_signal", 0.0)))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive", 0.0))

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        lgn = float(lgn_data.get("lgn_drive", 0.0))

        ppc_data = prior.get("PosteriorParietalCortex", {})
        ppc = float(ppc_data.get("ppc_drive", 0.0))
        ppc_dir = ppc_data.get("spatial_direction", "")

        target = self._drive_target(v1, pulv, s1, lgn, ppc)
        prev_drive = float(self.state.get("ips_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        aip = self._aip_grasp(new_drive, v1)
        lip = self._lip_saccade(new_drive, pulv)
        vip = self._vip_peripersonal(new_drive, s1, v1)
        num = self._numerosity(new_drive, v1, upstream_num)
        plan = self._reach_plan(new_drive, aip, ppc)
        direction = self._select_direction(plan, str(ppc_dir), str(vis_dir))
        state = self._classify_state(new_drive, aip, lip, num)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ips_drive"] = round(new_drive, 4)
        self.state["aip_grasp_signal"] = round(aip, 4)
        self.state["lip_saccade_signal"] = round(lip, 4)
        self.state["vip_peripersonal_signal"] = round(vip, 4)
        self.state["numerosity_signal"] = round(num, 4)
        self.state["reach_plan"] = round(plan, 4)
        self.state["reach_direction"] = direction
        self.state["ips_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ips_drive": round(new_drive, 4),
            "aip_grasp_signal": round(aip, 4),
            "lip_saccade_signal": round(lip, 4),
            "vip_peripersonal_signal": round(vip, 4),
            "numerosity_signal": round(num, 4),
            "reach_plan": round(plan, 4),
            "reach_direction": direction,
            "ips_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _dominant_subfield(self) -> str:
        a = float(self.state.get("aip_grasp_signal", 0.0))
        l = float(self.state.get("lip_saccade_signal", 0.0))
        v = float(self.state.get("vip_peripersonal_signal", 0.0))
        n = float(self.state.get("numerosity_signal", 0.0))
        vals = {"AIP": a, "LIP": l, "VIP": v, "HIPS": n}
        best = max(vals.items(), key=lambda kv: kv[1])
        if best[1] < 0.05:
            return "none"
        return best[0]

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ips_drive", 0.0),
            "subfield": self._dominant_subfield(),
            "direction": self.state.get("reach_direction", "none"),
            "state": self.state.get("ips_state", "quiet"),
        }

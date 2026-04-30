"""
LateralDorsalThalamus — LD — limbic-cingulate spatial-context relay

NEURAL SUBSTRATE
================
The lateral dorsal thalamic nucleus (LD) is a limbic-aligned higher-order
thalamic relay sitting just dorsolateral to the anterior thalamic
nuclei. LD receives convergent input from the dorsal subiculum, the
postsubiculum, the visual pretectum and the superior colliculus, and
projects densely to the retrosplenial cortex, cingulate cortex and
dorsal subicular cortex (the "limbic" cortices). Mizumori & Williams 1993
recorded directionally-tuned head-direction cells in LD that are
preferentially driven by visual landmarks; LD is therefore considered
the "visual-landmark" limb of the head-direction circuit, complementing
the vestibular limb that converges through ATN.

Functionally, LD lesions produce modest but reliable spatial memory
deficits in the radial maze and water maze (Mizumori & Williams 1993;
Wilton et al. 2001). Wolff et al. (2015) and the Frontiers review of
"higher-order LD relays" position LD as a key node integrating visual
landmark, retrosplenial and subicular signals into spatial context.

KEY FINDINGS
============
1. LD contains directionally selective head-direction cells (visual-dependent)
   [Mizumori SJ 1993, J Neurosci 13:4015, doi:10.1523/JNEUROSCI.13-09-04015.1993]
2. LD lesions impair spatial reference memory in radial-arm maze
   [Mizumori SJ 1994, Behav Neurosci 108:1106, doi:10.1037/0735-7044.108.6.1106]
3. LD-retrosplenial loop supports navigation; lesions disrupt path integration
   [Wilton LA 2001, Behav Brain Res 121:89, doi:10.1016/S0166-4328(00)00389-3]
4. LD as higher-order relay; subicular driver input to retrosplenial cortex
   [Bubb EJ 2017, Front Mol Neurosci 12:167, doi:10.3389/fnmol.2019.00167]
5. LD–retrosplenial pathway encodes visual landmark stability for navigation
   [Yoder RM 2011, Hippocampus 21:1190, doi:10.1002/hipo.20842]
6. LD relays pretectal/SC visual input to limbic cortex
   [Thompson SM 1986, J Comp Neurol 247:417, doi:10.1002/cne.902470402]

INPUTS
======
- SubiculumDorsal.subiculum_output (limbic driver)
- Postsubiculum / PrePresubiculum.head_direction_signal
- SuperiorColliculus.visual_signal (superficial layers)
- RetrosplenialCortex.cortical_drive (Layer-VI feedback)
- ThalamicReticularNucleus.trn_inhibition

OUTPUTS
=======
- ld_drive (0-1)
- retrosplenial_signal (0-1)
- cingulate_signal (0-1)
- head_direction_signal (0-1)
- spatial_context_signal (0-1)
- ld_state (str): "landmark_active" | "hd_active" | "context_relay" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class LateralDorsalThalamus(BrainMechanism):
    """LD — limbic spatial-context / visual-landmark thalamic relay."""

    BASELINE = 0.09
    SMOOTH = 0.22
    HD_THRESHOLD = 0.35
    LANDMARK_THRESHOLD = 0.40
    CONTEXT_THRESHOLD = 0.25

    def __init__(self):
        super().__init__(
            name="LateralDorsalThalamus",
            human_analog="Lateral dorsal thalamic nucleus (LD)",
            layer="subcortical",
        )
        self.state.setdefault("ld_drive", self.BASELINE)
        self.state.setdefault("retrosplenial_signal", 0.0)
        self.state.setdefault("cingulate_signal", 0.0)
        self.state.setdefault("head_direction_signal", 0.0)
        self.state.setdefault("spatial_context_signal", 0.0)
        self.state.setdefault("ld_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("hd_active_count", 0)
        self.state.setdefault("tick_count", 0)

    # ---- helper sub-signals ----

    def _visual_landmark_drive(self, sc: float, vis: float) -> float:
        """Visual-landmark contribution from SC + cortical visual input.

        Mizumori 1993: LD HD cells require visual input to maintain
        directional firing. SC superficial layers + V1/V2 carry it.
        """
        return min(1.0, sc * 0.55 + vis * 0.45)

    def _hd_input(self, hd: float, landmark: float) -> float:
        """Head-direction signal arriving from postsubiculum + visual.

        Visual landmarks ANCHOR the HD signal in LD (Yoder 2011).
        """
        if hd <= 0.0 and landmark <= 0.0:
            return 0.0
        return min(1.0, hd * 0.6 + landmark * 0.4)

    def _drive_target(self, sub: float, hd: float, landmark: float,
                      ctx: float, trn: float) -> float:
        """Composite LD drive — subicular + HD + landmark drivers."""
        excitation = (self.BASELINE
                      + sub * 0.30
                      + hd * 0.25
                      + landmark * 0.30
                      + ctx * 0.10)
        inhibition = trn * 0.30
        target = excitation - inhibition * 0.5
        if target < 0.0:
            target = 0.0
        return min(1.0, target)

    def _retrosplenial(self, drive: float, hd: float,
                        landmark: float) -> float:
        """RSC-projecting axons (Wilton 2001; Yoder 2011)."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.5 + hd * 0.25 + landmark * 0.25)

    def _cingulate(self, drive: float, sub: float) -> float:
        """Cingulate component of limbic-cingulate output."""
        if drive < 0.10:
            return 0.0
        return min(1.0, drive * 0.45 + sub * 0.25)

    def _spatial_context(self, drive: float, sub: float, hd: float,
                          landmark: float) -> float:
        """Composite spatial-context signal (Bubb 2017)."""
        return min(1.0, drive * 0.3 + sub * 0.3 + hd * 0.2 + landmark * 0.2)

    def _classify_state(self, drive: float, hd: float,
                         landmark: float, sub: float) -> str:
        if drive < 0.13:
            return "quiet"
        if landmark > self.LANDMARK_THRESHOLD and hd > self.HD_THRESHOLD:
            return "landmark_active"
        if hd > self.HD_THRESHOLD:
            return "hd_active"
        if sub > self.CONTEXT_THRESHOLD:
            return "context_relay"
        return "context_relay" if drive > 0.20 else "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ---- main tick ----

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        sub_data = prior.get("SubiculumDorsal", {})
        if not sub_data:
            sub_data = prior.get("Subiculum", {})
        sub = float(sub_data.get("subiculum_output",
                          sub_data.get("subicular_output",
                              sub_data.get("dsub_drive", 0.0))))

        hd_data = prior.get("PrePresubiculum", {})
        if not hd_data:
            hd_data = prior.get("Postsubiculum", {})
        hd = float(hd_data.get("head_direction_signal",
                         hd_data.get("hd_drive", 0.0)))

        sc_data = prior.get("SuperiorColliculus", {})
        sc = float(sc_data.get("visual_signal",
                         sc_data.get("sc_drive",
                             sc_data.get("sc_output", 0.0))))

        vis_data = prior.get("V1", {})
        if not vis_data:
            vis_data = prior.get("VisualCortex", {})
        vis = float(vis_data.get("visual_signal",
                          vis_data.get("v1_drive", 0.0)))

        ctx_data = prior.get("RetrosplenialCortex", {})
        ctx = float(ctx_data.get("cortical_drive",
                          ctx_data.get("rsc_drive", 0.0)))

        trn_data = prior.get("ThalamicReticularNucleus", {})
        trn = float(trn_data.get("trn_inhibition", 0.0))

        landmark = self._visual_landmark_drive(sc, vis)
        hd_eff = self._hd_input(hd, landmark)
        target = self._drive_target(sub, hd_eff, landmark, ctx, trn)
        prev_drive = float(self.state.get("ld_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        rsc = self._retrosplenial(new_drive, hd_eff, landmark)
        cing = self._cingulate(new_drive, sub)
        ctx_sig = self._spatial_context(new_drive, sub, hd_eff, landmark)

        state = self._classify_state(new_drive, hd_eff, landmark, sub)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        hd_count = int(self.state.get("hd_active_count", 0))
        if state in ("hd_active", "landmark_active"):
            hd_count += 1

        self.state["ld_drive"] = round(new_drive, 4)
        self.state["retrosplenial_signal"] = round(rsc, 4)
        self.state["cingulate_signal"] = round(cing, 4)
        self.state["head_direction_signal"] = round(hd_eff, 4)
        self.state["spatial_context_signal"] = round(ctx_sig, 4)
        self.state["ld_state"] = state
        self.state["recent_states"] = recent
        self.state["hd_active_count"] = hd_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ld_drive": round(new_drive, 4),
            "retrosplenial_signal": round(rsc, 4),
            "cingulate_signal": round(cing, 4)
            ,
            "head_direction_signal": round(hd_eff, 4),
            "spatial_context_signal": round(ctx_sig, 4),
            "ld_state": state,
        }

    def _hd_engagement(self) -> float:
        ticks = max(1, int(self.state.get("tick_count", 1)))
        return min(1.0, self.state.get("hd_active_count", 0) / ticks)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ld_drive", 0.0),
            "rsc": self.state.get("retrosplenial_signal", 0.0),
            "hd": self.state.get("head_direction_signal", 0.0),
            "state": self.state.get("ld_state", "quiet"),
        }

"""
PremotorCortex — PMC / Brodmann 6 lateral

NEURAL SUBSTRATE
================
The premotor cortex (PMC) occupies the lateral part of Brodmann area 6,
anterior to M1, and is subdivided into a dorsal premotor area (PMd, F2)
and a ventral premotor area (PMv, F4/F5). PMd is preferentially involved
in receiving visuospatial signals and integrating which arm to use with
where the target is located, while PMv specifies the spatial location of
the target and contains neurons selective for grasp/object features
(Hoshi & Tanji 2007). PMv area F5 is the canonical site of "mirror
neurons" — cells that fire both when the monkey performs a goal-directed
action and when it observes the same action performed by another agent
(Rizzolatti et al. 1996).

Functionally, PMd performs the visuomotor transformation that converts a
target location in extrinsic coordinates into a reaching plan; preferred
directions of PMd cells shift systematically when reaches are performed
in different parts of the workspace (Caminiti et al. 1991). PMd is also
the cortical site at which competing potential actions are simultaneously
represented and one is selected — the "affordance competition"
hypothesis of action selection (Cisek & Kalaska 2005, 2007).

KEY FINDINGS
============
1. F5 mirror neurons in macaque ventral premotor cortex discharge during
   both action execution and action observation —
   [Rizzolatti G 1996, Cogn Brain Res 3:131, doi:10.1016/0926-6410(95)00038-0]
2. Premotor population vector codes reach direction, with preferred
   directions shifting across workspace coordinates —
   [Caminiti R 1991, J Neurosci 11:1182, PMID 2027042]
3. PMd represents multiple potential reach targets in parallel until one
   action is selected — affordance-competition substrate —
   [Cisek P 2005, Neuron 45:801, doi:10.1016/j.neuron.2005.01.027]
4. Dorsal vs ventral premotor functional dissociation: PMd integrates
   target/effector, PMv handles object-grasp matching —
   [Hoshi E 2007, Curr Opin Neurobiol 17:234, doi:10.1016/j.conb.2007.02.003]
5. Cortical mechanisms of action selection — affordance-competition
   review extending parietal-premotor circuits —
   [Cisek P 2007, Phil Trans R Soc B 362:1585, doi:10.1098/rstb.2007.2054]

INPUTS
======
- IntraparietalSulcus.ips_drive (visuomotor reach plan)
- PosteriorParietalCortex.ppc_drive (multimodal spatial)
- PrimaryMotorCortex.m1_drive (recurrent)
- PrelimbicCortex.prelimbic_drive (action goal/cognitive)
- VisualCortexV1.v1_drive (object/grasp visual cues)

OUTPUTS
=======
- pmc_drive (0-1) — overall PMC activation
- pmd_drive (0-1) — dorsal premotor (reach selection)
- pmv_drive (0-1) — ventral premotor (grasp/mirror)
- mirror_neuron_signal (0-1) — F5 mirror activity
- reach_direction (str) — selected direction token
- action_competition (0-1) — multiple-affordance competition strength
- pmc_state (str): "selecting" | "executing_plan" |
                   "observing_action" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PremotorCortex(BrainMechanism):
    """PMC — lateral premotor cortex (PMd + PMv) action selection / mirror."""

    BASELINE = 0.07
    SMOOTH = 0.22
    ACTIVE_THRESHOLD = 0.20
    SELECTION_THRESHOLD = 0.40
    DIRECTIONS = ("up", "down", "left", "right", "forward", "back")

    def __init__(self):
        super().__init__(
            name="PremotorCortex",
            human_analog="Lateral premotor cortex (PMd + PMv, Brodmann 6)",
            layer="neocortical",
        )
        self.state.setdefault("pmc_drive", self.BASELINE)
        self.state.setdefault("pmd_drive", 0.0)
        self.state.setdefault("pmv_drive", 0.0)
        self.state.setdefault("mirror_neuron_signal", 0.0)
        self.state.setdefault("reach_direction", "none")
        self.state.setdefault("action_competition", 0.0)
        self.state.setdefault("pmc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, ips: float, ppc: float, prelimbic: float,
                      v1: float) -> float:
        """Composite premotor drive (Cisek 2007 — parietal+frontal pooled)."""
        target = (self.BASELINE
                  + ips * 0.30
                  + ppc * 0.25
                  + prelimbic * 0.20
                  + v1 * 0.15)
        return min(1.0, target)

    def _pmd_drive(self, drive: float, ips: float, ppc: float) -> float:
        """PMd — visuomotor reach plan (Caminiti 1991, Hoshi 2007)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + ips * 0.4 + ppc * 0.3)

    def _pmv_drive(self, drive: float, v1: float, ips: float) -> float:
        """PMv — grasp / mirror system (Rizzolatti 1996, Hoshi 2007)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + v1 * 0.4 + ips * 0.2)

    def _mirror_neuron(self, pmv: float, v1: float, ips: float) -> float:
        """Mirror-neuron signal in F5: requires visual action + grasp goal
        (Rizzolatti 1996)."""
        if pmv < 0.20 or v1 < 0.20:
            return 0.0
        return min(1.0, pmv * 0.5 + v1 * 0.5)

    def _action_competition(self, drive: float, pmd: float,
                              ppc: float) -> float:
        """Affordance-competition signal (Cisek 2005, 2007).
        High when multiple targets/affordances co-active."""
        if drive < 0.20:
            return 0.0
        # competition is high when both PMd and parietal carry strong signals
        return min(1.0, pmd * 0.5 + ppc * 0.5)

    def _select_direction(self, pmd: float, ips_dir: str,
                          ppc_dir: str) -> str:
        if pmd < 0.20:
            return "none"
        if ips_dir and ips_dir in self.DIRECTIONS:
            return ips_dir
        if ppc_dir and ppc_dir in self.DIRECTIONS:
            return ppc_dir
        return "forward"

    def _classify_state(self, drive: float, mirror: float,
                         pmd: float, comp: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if mirror > 0.35:
            return "observing_action"
        if comp > self.SELECTION_THRESHOLD and pmd > 0.30:
            return "selecting"
        if pmd > self.SELECTION_THRESHOLD:
            return "executing_plan"
        return "selecting"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ips_data = prior.get("IntraparietalSulcus", {})
        ips = float(ips_data.get("ips_drive",
                            ips_data.get("reach_plan", 0.0)))
        ips_dir = ips_data.get("reach_direction", "")

        ppc_data = prior.get("PosteriorParietalCortex", {})
        ppc = float(ppc_data.get("ppc_drive",
                            ppc_data.get("spatial_signal", 0.0)))
        ppc_dir = ppc_data.get("spatial_direction", "")

        m1_data = prior.get("PrimaryMotorCortex", {})
        m1 = float(m1_data.get("m1_drive", 0.0))

        prelimbic_data = prior.get("PrelimbicCortex", {})
        prelimbic = float(prelimbic_data.get("prelimbic_drive",
                                          prelimbic_data.get("plc_drive", 0.0)))

        v1_data = prior.get("VisualCortexV1", {})
        if not v1_data:
            v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive",
                          v1_data.get("v1_signal", 0.0)))

        target = self._drive_target(ips, ppc, prelimbic, v1)
        # M1 recurrent feedback adds a small bump
        target = min(1.0, target + m1 * 0.05)
        prev_drive = float(self.state.get("pmc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        pmd = self._pmd_drive(new_drive, ips, ppc)
        pmv = self._pmv_drive(new_drive, v1, ips)
        mirror = self._mirror_neuron(pmv, v1, ips)
        comp = self._action_competition(new_drive, pmd, ppc)
        direction = self._select_direction(pmd, str(ips_dir), str(ppc_dir))
        state = self._classify_state(new_drive, mirror, pmd, comp)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pmc_drive"] = round(new_drive, 4)
        self.state["pmd_drive"] = round(pmd, 4)
        self.state["pmv_drive"] = round(pmv, 4)
        self.state["mirror_neuron_signal"] = round(mirror, 4)
        self.state["reach_direction"] = direction
        self.state["action_competition"] = round(comp, 4)
        self.state["pmc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pmc_drive": round(new_drive, 4),
            "pmd_drive": round(pmd, 4),
            "pmv_drive": round(pmv, 4),
            "mirror_neuron_signal": round(mirror, 4),
            "reach_direction": direction,
            "action_competition": round(comp, 4),
            "pmc_state": state,
            "preferred_direction": direction,
        }

    # ----- summary helpers --------------------------------------------------

    def _dominant_subdivision(self) -> str:
        d = float(self.state.get("pmd_drive", 0.0))
        v = float(self.state.get("pmv_drive", 0.0))
        if max(d, v) < 0.10:
            return "none"
        return "PMd" if d >= v else "PMv"

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pmc_drive", 0.0),
            "subdivision": self._dominant_subdivision(),
            "direction": self.state.get("reach_direction", "none"),
            "state": self.state.get("pmc_state", "quiet"),
        }

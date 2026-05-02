"""
PrimaryMotorCortex — M1 / Brodmann 4 / Precentral Gyrus

NEURAL SUBSTRATE
================
The primary motor cortex (M1) is Brodmann area 4 on the anterior wall of
the central sulcus / precentral gyrus. M1 layer V contains the giant
pyramidal Betz cells that give rise to the largest fibers of the
corticospinal tract; ~30% of the corticospinal tract originates in M1
(the rest from premotor, SMA and parietal areas). The motor homunculus
(Penfield & Boldrey 1937) lays out a distorted somatotopic map of body
parts on the precentral gyrus, with disproportionately large hand,
face, and tongue representations reflecting the precision of voluntary
control over those effectors.

Population-level coding: Georgopoulos and colleagues showed that
individual M1 neurons are broadly tuned to a "preferred direction" of
arm movement, and the population vector (the weighted sum of
preferred-direction vectors) accurately predicts the direction of
upcoming movement (Georgopoulos 1986). M1 simultaneously encodes muscle
parameters and abstract movement direction (Kakei, Hoffman & Strick
1999), and microstimulation on behavioral time scales evokes complex
ethologically relevant postures (Graziano, Taylor & Moore 2002).
Within a finger or limb, multiple movement-related neurons are
distributed widely rather than confined to discrete sub-regions
(Schieber 2001).

KEY FINDINGS
============
1. Penfield's electrical stimulation of human precentral gyrus revealed
   the distorted somatotopic motor homunculus —
   [Penfield W 1937, Brain 60:389, doi:10.1093/brain/60.4.389]
2. M1 population vector predicts arm-movement direction; individual cells
   are cosine-tuned to a preferred direction —
   [Georgopoulos A 1986, Science 233:1416, doi:10.1126/science.3749885]
3. M1 contains both muscle-like and direction-of-movement representations,
   with both populations active during reaching —
   [Kakei S 1999, Science 285:2136, doi:10.1126/science.285.5436.2136]
4. Long-train M1 microstimulation evokes coordinated, ethologically
   meaningful postures spanning multiple joints —
   [Graziano M 2002, Neuron 34:841, doi:10.1016/S0896-6273(02)00698-0]
5. Finger movements are represented by widely distributed M1 neurons,
   constraining strict somatotopic models —
   [Schieber M 2001, J Neurophysiol 86:2125, PMID 11698505]

INPUTS
======
- PremotorCortex.pmc_drive (PM → M1 action plan)
- SupplementaryMotorArea.sma_drive (SMA → M1 internally-generated)
- PrimarySomatosensoryCortex.s1_drive (S1 → M1 sensorimotor)
- CerebellarDeepNuclei.cb_output (cerebellar gating)
- IntraparietalSulcus.ips_drive (parietal reach plan)

OUTPUTS
=======
- m1_drive (0-1) — overall M1 activation
- corticospinal_drive (0-1) — Betz/CST output strength
- preferred_direction (str) — population-vector direction token
- motor_homunculus_focus (str) — engaged effector
- betz_cell_drive (0-1) — layer-V projection neurons
- m1_state (str): "executing" | "preparing" |
                  "fine_motor" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrimaryMotorCortex(BrainMechanism):
    """M1 — primary motor cortex / precentral gyrus / Betz cells."""

    BASELINE = 0.06
    SMOOTH = 0.22
    ACTIVE_THRESHOLD = 0.20
    EXECUTE_THRESHOLD = 0.50
    DIRECTIONS = ("up", "down", "left", "right", "forward", "back")
    EFFECTORS = ("hand", "arm", "leg", "face", "tongue")

    def __init__(self):
        super().__init__(
            name="PrimaryMotorCortex",
            human_analog="Primary motor cortex (M1, Brodmann 4)",
            layer="neocortical",
        )
        self.state.setdefault("m1_drive", self.BASELINE)
        self.state.setdefault("corticospinal_drive", 0.0)
        self.state.setdefault("preferred_direction", "none")
        self.state.setdefault("motor_homunculus_focus", "none")
        self.state.setdefault("betz_cell_drive", 0.0)
        self.state.setdefault("m1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("execute_count", 0)
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, pmc: float, sma: float, s1: float,
                      cb: float, ips: float) -> float:
        """Composite M1 drive from premotor/SMA/parietal/cerebellum
        (Georgopoulos 1986, Graziano 2002 — pooled motor commands)."""
        target = (self.BASELINE
                  + pmc * 0.30
                  + sma * 0.25
                  + s1 * 0.10
                  + cb * 0.15
                  + ips * 0.10)
        return min(1.0, target)

    def _corticospinal(self, drive: float, cb: float) -> float:
        """CST output from layer V Betz cells; cerebellum gates timing
        (Schieber 2001 — distributed CST projection)."""
        if drive < 0.18:
            return 0.0
        # cerebellar gating modulates timing/amplitude
        gate = 1.0 + cb * 0.3
        return min(1.0, drive * 0.7 * gate)

    def _betz_cell(self, drive: float, cst: float) -> float:
        """Betz layer-V drive — strongly correlated with CST output."""
        if drive < 0.18:
            return 0.0
        return min(1.0, drive * 0.6 + cst * 0.4)

    def _preferred_direction(self, pmc_dir: str, ips_dir: str) -> str:
        """Population vector direction (Georgopoulos 1986)."""
        # Trust premotor reach direction when given; otherwise IPS plan
        if pmc_dir and pmc_dir in self.DIRECTIONS:
            return pmc_dir
        if ips_dir and ips_dir in self.DIRECTIONS:
            return ips_dir
        return "none"

    def _homunculus_focus(self, pmc: float, ips: float, s1: float) -> str:
        """Penfield 1937 — pick the engaged effector."""
        signal = max(pmc, ips, s1)
        if signal < 0.15:
            return "none"
        # heuristic: strong premotor + IPS → reach (arm/hand)
        if pmc > 0.40 and ips > 0.30:
            return "hand"
        if s1 > 0.45:
            return "hand"
        if pmc > 0.30:
            return "arm"
        return "arm"

    def _classify_state(self, drive: float, cst: float,
                         pmc: float, sma: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if cst > self.EXECUTE_THRESHOLD:
            return "executing"
        if pmc > 0.30 or sma > 0.30:
            return "preparing"
        if drive > 0.40:
            return "fine_motor"
        return "preparing"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pmc_data = prior.get("PremotorCortex", {})
        pmc = float(pmc_data.get("pmc_drive",
                          pmc_data.get("premotor_drive", 0.0)))
        pmc_dir = pmc_data.get("reach_direction",
                              pmc_data.get("preferred_direction", ""))

        sma_data = prior.get("SupplementaryMotorArea", {})
        sma = float(sma_data.get("sma_drive",
                          sma_data.get("supp_motor_drive", 0.0)))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive",
                          s1_data.get("area_3b_signal", 0.0)))

        cb_data = prior.get("CerebellarDeepNuclei", {})
        cb = float(cb_data.get("cb_output",
                          cb_data.get("cerebellar_drive", 0.0)))

        ips_data = prior.get("IntraparietalSulcus", {})
        ips = float(ips_data.get("ips_drive",
                            ips_data.get("reach_plan", 0.0)))
        ips_dir = ips_data.get("reach_direction", "")

        target = self._drive_target(pmc, sma, s1, cb, ips)
        prev_drive = float(self.state.get("m1_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        cst = self._corticospinal(new_drive, cb)
        betz = self._betz_cell(new_drive, cst)
        direction = self._preferred_direction(str(pmc_dir), str(ips_dir))
        focus = self._homunculus_focus(pmc, ips, s1)
        state = self._classify_state(new_drive, cst, pmc, sma)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        execute_count = int(self.state.get("execute_count", 0))
        if state == "executing":
            execute_count += 1

        self.state["m1_drive"] = round(new_drive, 4)
        self.state["corticospinal_drive"] = round(cst, 4)
        self.state["preferred_direction"] = direction
        self.state["motor_homunculus_focus"] = focus
        self.state["betz_cell_drive"] = round(betz, 4)
        self.state["m1_state"] = state
        self.state["recent_states"] = recent
        self.state["execute_count"] = execute_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "m1_drive": round(new_drive, 4),
            "corticospinal_drive": round(cst, 4),
            "preferred_direction": direction,
            "motor_homunculus_focus": focus,
            "betz_cell_drive": round(betz, 4),
            "m1_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _executing_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        return sum(1 for s in recent if s == "executing") / max(1, len(recent))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("m1_drive", 0.0),
            "cst": self.state.get("corticospinal_drive", 0.0),
            "focus": self.state.get("motor_homunculus_focus", "none"),
            "state": self.state.get("m1_state", "quiet"),
        }

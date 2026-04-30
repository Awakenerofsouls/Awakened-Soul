"""
NucleusOfDiagonalBandHorizontal — hDBB / Cholinergic Olfactory Modulator

NEURAL SUBSTRATE
================
The horizontal limb of the diagonal band of Broca (hDBB) is the
principal source of cholinergic projections to the olfactory bulb (OB)
and piriform cortex. Distinct from vDBB (which targets hippocampus),
hDBB is a "centrifugal" cholinergic modulator of olfactory processing —
it gates olfactory cortex sensitivity to behaviorally relevant odors.

Cholinergic activation of OB granule cells via hDBB→OB projection
sharpens odor representations in mitral cells (Linster 2011). hDBB
selective lesion impairs odor discrimination learning without affecting
spatial memory — functionally separate from vDBB.

KEY FINDINGS
============
1. Horizontal diagonal band cholinergic neurons project to olfactory
   bulb; principal source of OB ACh —
   [Macrides 1981, Brain Res Bull 6:1, PMID 7470947]
2. hDBB cholinergic activation sharpens mitral cell odor tuning;
   improves discrimination —
   [Linster 2011, J Neurosci 31:2657, doi:10.1523/JNEUROSCI.5573-10.2011]
3. hDBB lesion impairs odor discrimination learning while sparing
   simple detection — selective deficit —
   [Roman 1993, Behav Brain Res 53:127, PMID 8466663]
4. hDBB→OB centrifugal axons activate granule cells, sharpening
   inhibition + improving signal-to-noise —
   [Devore 2013, Front Neural Circuits 7:147, doi:10.3389/fncir.2013.00147]
5. ACh release in piriform cortex from hDBB enhances odor learning
   plasticity at glutamatergic synapses —
   [Hasselmo 2004, Neural Comput 16:1763, doi:10.1162/0899766041336387]

INPUTS
======
- OlfactoryBulb.ob_drive (or ob_output)
- BrainstemReticular.arousal_drive (or ArousalRegulator.tonic_level)
- AmygdalaBasolateral.bla_drive (motivational gate)

OUTPUTS
=======
- hdbb_drive (0-1)
- ob_ach_signal (0-1)
- piriform_ach_signal (0-1)
- odor_discrimination_gain (0-1)
- hdbb_state (str): "ach_active" | "discrimination_high" | "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NucleusOfDiagonalBandHorizontal(BrainMechanism):
    """hDBB — cholinergic olfactory modulator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    DISCRIMINATION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="NucleusOfDiagonalBandHorizontal",
            human_analog="Horizontal diagonal band of Broca",
            layer="limbic",
        )
        self.state.setdefault("hdbb_drive", self.BASELINE)
        self.state.setdefault("ob_ach_signal", 0.0)
        self.state.setdefault("piriform_ach_signal", 0.0)
        self.state.setdefault("odor_discrimination_gain", 0.0)
        self.state.setdefault("hdbb_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, ob: float, arousal: float, bla: float) -> float:
        """hDBB drive (Macrides 1981)."""
        target = (self.BASELINE
                  + ob * 0.35
                  + arousal * 0.30
                  + bla * 0.20)
        return min(1.0, target)

    def _ob_ach(self, drive: float, ob: float) -> float:
        """hDBB→OB cholinergic projection (Devore 2013)."""
        return min(1.0, drive * 0.55 + ob * 0.30)

    def _piriform_ach(self, drive: float) -> float:
        """hDBB→piriform cholinergic (Hasselmo 2004)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.85)

    def _discrimination_gain(self, ob_ach: float, pir_ach: float) -> float:
        """Odor discrimination enhancement (Linster 2011; Roman 1993)."""
        return min(1.0, ob_ach * 0.6 + pir_ach * 0.4)

    def _classify_state(self, drive: float, ach: float,
                         discrimination: float) -> str:
        if drive < 0.20:
            return "quiet"
        if discrimination > self.DISCRIMINATION_THRESHOLD:
            return "discrimination_high"
        if ach > 0.30:
            return "ach_active"
        return "rest"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ob_data = prior.get("OlfactoryBulb", {})
        ob = float(ob_data.get("ob_drive",
                          ob_data.get("ob_output", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        if not ar_data:
            ar_data = prior.get("BrainstemReticular", {})
        arousal = float(ar_data.get("tonic_level",
                            ar_data.get("arousal_drive", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        target = self._drive_target(ob, arousal, bla)
        prev_drive = float(self.state.get("hdbb_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        ob_ach = self._ob_ach(new_drive, ob)
        pir_ach = self._piriform_ach(new_drive)
        discrim = self._discrimination_gain(ob_ach, pir_ach)

        state = self._classify_state(new_drive, ob_ach, discrim)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["hdbb_drive"] = round(new_drive, 4)
        self.state["ob_ach_signal"] = round(ob_ach, 4)
        self.state["piriform_ach_signal"] = round(pir_ach, 4)
        self.state["odor_discrimination_gain"] = round(discrim, 4)
        self.state["hdbb_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "hdbb_drive": round(new_drive, 4),
            "ob_ach_signal": round(ob_ach, 4),
            "piriform_ach_signal": round(pir_ach, 4),
            "odor_discrimination_gain": round(discrim, 4),
            "hdbb_state": state,
        }

    def _learning_facilitation(self) -> float:
        """ACh-driven olfactory learning facilitation (Hasselmo 2004)."""
        return float(self.state.get("odor_discrimination_gain", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("hdbb_drive", 0.0),
            "ob_ach": self.state.get("ob_ach_signal", 0.0),
            "discrim": self.state.get("odor_discrimination_gain", 0.0),
            "state": self.state.get("hdbb_state", "quiet"),
        }

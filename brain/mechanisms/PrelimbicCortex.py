"""
PrelimbicCortex -- PL / Fear Expression / Cognitive Control Hub

NEURAL SUBSTRATE
================
Prelimbic cortex (PL, dorsal mPFC, rodent area 32) sits dorsal to
infralimbic (IL). Functionally opposite: PL drives fear EXPRESSION while
IL drives fear EXTINCTION. Both are part of medial prefrontal cortex.

PL projection neurons:
- → BLA (drives fear expression neurons)
- → BA fear neurons (Herry 2008 contextual renewal)
- → CeA (direct fear output)
- → NAc (motivation/conflict)

PL is also critical for cognitive control, working memory, and conflict
monitoring. Vidal-Gonzalez 2006 demonstrated bidirectional optogenetic
control: PL stim enhances fear, IL stim enhances extinction.

KEY FINDINGS
============
1. Prelimbic vs infralimbic mPFC bidirectional optogenetic control of
   fear expression -- PL stim enhances fear, IL stim enhances
   extinction recall -- [Vidal-Gonzalez 2006, Learn Mem 13:728,
   doi:10.1101/lm.306106]
2. PL→BLA glutamatergic input drives fear neuron population +
   conditioned freezing -- [Sotres-Bayon 2010, Neuron 76:804,
   doi:10.1016/j.neuron.2012.09.028]
3. PL is necessary for sustained fear expression; selective inactivation
   reduces freezing during recall -- [Sierra-Mercado 2011,
   Neuropsychopharmacology 36:529, PMID 20962684]
4. PL working-memory dysfunction in chronic stress; sustained activity
   degrades -- [Arnsten 2009, Nat Rev Neurosci 10:410,
   doi:10.1038/nrn2648]
5. PL→NAc pathway gates cognitive-control vs habitual responding;
   conflict-monitoring substrate -- [Hyman 2017, Trends Cogn Sci
   21:108, doi:10.1016/j.tics.2016.12.005]

INPUTS
======
- BasolateralAmygdala.bla_drive
- HippocampalCA1Output.ca1_drive (context)
- ParaventricularThalamus.pvt_drive (aversive arousal feedback)
- ValenceTagger.aversive_signal, .valence_intensity
- LocusCoeruleusCore.lc_tonic_firing (Yerkes-Dodson WM gating)

OUTPUTS
=======
- pl_drive (0-1)
- fear_expression_command (0-1)
- bla_fear_drive (0-1)
- working_memory_signal (0-1)
- conflict_monitoring_signal (0-1)
- pl_state (str): "fear_expression" | "working_memory" |
  "conflict_monitoring" | "stress_dysfunction" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrelimbicCortex(BrainMechanism):
    """PL -- fear expression + cognitive control mPFC hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    FEAR_THRESHOLD = 0.40
    WM_THRESHOLD = 0.35
    HYPER_LC_THRESHOLD = 0.70  # high LC tonic = WM dysfunction (Arnsten 2009)

    def __init__(self):
        super().__init__(
            name="PrelimbicCortex",
            human_analog="Prelimbic cortex (fear expression + cognitive control)",
            layer="limbic",
        )
        self.state.setdefault("pl_drive", self.BASELINE)
        self.state.setdefault("fear_expression_command", 0.0)
        self.state.setdefault("bla_fear_drive", 0.0)
        self.state.setdefault("working_memory_signal", 0.0)
        self.state.setdefault("conflict_monitoring_signal", 0.0)
        self.state.setdefault("pl_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, bla: float, ca1: float, pvt: float,
                       aversive: float, lc: float) -> float:
        """PL firing -- driven by BLA + context + thalamic + aversive valence."""
        target = self.BASELINE + bla * 0.30 + ca1 * 0.20 + pvt * 0.20
        target += aversive * 0.20
        # LC tonic Yerkes-Dodson: moderate LC enhances PL, high LC degrades
        if lc > self.HYPER_LC_THRESHOLD:
            target *= 0.7  # WM dysfunction (Arnsten 2009)
        else:
            target += max(0.0, lc - 0.30) * 0.10
        return min(1.0, target)

    def _fear_expression(self, drive: float, aversive: float,
                          intensity: float) -> float:
        """Fear expression command (Vidal-Gonzalez 2006)."""
        if aversive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + aversive * intensity * 1.0)

    def _bla_fear_drive(self, drive: float, fear_expression: float) -> float:
        """PL→BLA glutamatergic drive to fear neurons (Sotres-Bayon 2010)."""
        return min(1.0, drive * 0.5 + fear_expression * 0.5)

    def _working_memory(self, drive: float, lc: float) -> float:
        """Working memory signal -- degraded by hyper-LC (Arnsten 2009)."""
        if lc > self.HYPER_LC_THRESHOLD:
            return drive * 0.3  # WM dysfunction at high LC tonic
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.85)

    def _conflict_monitoring(self, drive: float, aversive: float,
                                appetitive: float) -> float:
        """Conflict monitoring -- high when both aversive + appetitive present
        (approach-avoidance conflict, Hyman 2017)."""
        if aversive < 0.20 or appetitive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + min(aversive, appetitive) * 1.0)

    def _classify_state(self, drive: float, fear: float, wm: float,
                          conflict: float, lc: float) -> str:
        if lc > self.HYPER_LC_THRESHOLD and drive < 0.30:
            return "stress_dysfunction"
        if conflict > 0.30:
            return "conflict_monitoring"
        if fear > self.FEAR_THRESHOLD:
            return "fear_expression"
        if wm > self.WM_THRESHOLD:
            return "working_memory"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", bla_data.get("ba_fear_neurons", 0.0)))

        ca1_data = prior.get("HippocampalCA1Output", {})
        ca1 = float(ca1_data.get("ca1_drive", 0.0))

        pvt_data = prior.get("ParaventricularThalamus", {})
        pvt = float(pvt_data.get("pvt_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        appetitive = max(0.0, sign * intensity)

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc = float(lc_data.get("lc_tonic_firing", 0.20))

        target = self._drive_target(bla, ca1, pvt, aversive, lc)
        prev_drive = float(self.state.get("pl_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        fear_expr = self._fear_expression(new_drive, aversive, intensity)
        bla_fear = self._bla_fear_drive(new_drive, fear_expr)
        wm = self._working_memory(new_drive, lc)
        conflict = self._conflict_monitoring(new_drive, aversive, appetitive)

        state = self._classify_state(new_drive, fear_expr, wm, conflict, lc)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pl_drive"] = round(new_drive, 4)
        self.state["fear_expression_command"] = round(fear_expr, 4)
        self.state["bla_fear_drive"] = round(bla_fear, 4)
        self.state["working_memory_signal"] = round(wm, 4)
        self.state["conflict_monitoring_signal"] = round(conflict, 4)
        self.state["pl_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pl_drive": round(new_drive, 4),
            "fear_expression_command": round(fear_expr, 4),
            "bla_fear_drive": round(bla_fear, 4),
            "working_memory_signal": round(wm, 4),
            "conflict_monitoring_signal": round(conflict, 4),
            "pl_state": state,
        }

    def _yerkes_dodson_zone(self, lc: float, drive: float) -> str:
        """Identify operating zone on Yerkes-Dodson curve."""
        if lc > self.HYPER_LC_THRESHOLD:
            return "hypertonic_dysfunction"
        if 0.30 <= lc <= 0.65 and drive > 0.30:
            return "optimal_engagement"
        if lc < 0.20:
            return "underaroused"
        return "transitional"

    def _sustained_fear_signal(self, recent_states: list) -> float:
        """Proportion of recent ticks in fear_expression state --
        chronic fear expression indicator. High values suggest
        dysregulated fear that PL cannot suppress."""
        if not recent_states:
            return 0.0
        fear_ticks = sum(1 for s in recent_states[-30:]
                         if s == "fear_expression")
        return fear_ticks / max(1, len(recent_states[-30:]))

    def _cognitive_load_estimate(self, wm: float, conflict: float,
                                   fear: float) -> float:
        """Composite cognitive load signal -- weighted combination of
        working memory demand, conflict, and emotional interference.
        Used by upstream mechanisms to gate attention allocation."""
        return min(1.0, wm * 0.40 + conflict * 0.35 + fear * 0.25)

    def _stress_resilience_factor(self, lc: float, wm: float) -> float:
        """Stress resilience proxy -- PL's capacity to maintain function
        under NE load. Based on Arnsten 2009: high LC tonic degrades
        prefrontal spatial memory, but moderate LC preserves function."""
        if lc > self.HYPER_LC_THRESHOLD:
            return max(0.0, 1.0 - (lc - self.HYPER_LC_THRESHOLD) / 0.30)
        if wm > self.WM_THRESHOLD and lc < 0.50:
            return 0.80 + lc * 0.20
        return 0.60 + lc * 0.30

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("pl_drive", 0.0),
            "fear": self.state.get("fear_expression_command", 0.0),
            "wm": self.state.get("working_memory_signal", 0.0),
            "state": self.state.get("pl_state", "quiet"),
        }

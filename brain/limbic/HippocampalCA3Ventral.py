"""
HippocampalCA3Ventral — vCA3 / Affective Pattern Completion

NEURAL SUBSTRATE
================
Ventral CA3 (vCA3) parallels dorsal CA3 anatomically — same recurrent
auto-associative architecture — but participates in the affective
hippocampal stream (Fanselow & Dong 2010 dorsal/ventral gradient). vCA3
projects to vCA1 via Schaffer collaterals, supporting pattern completion
of contextual emotional memories. vCA3 lesions selectively impair
contextual fear conditioning while sparing spatial pattern completion.

Recent work (Jimenez 2018, 2020) shows vCA3 anxiety-related cells encode
threatening context with valence-specific coding. The vCA3 attractor
likely binds spatial context to emotional valence — distinct
computational role from dCA3's purely spatial pattern completion.

KEY FINDINGS
============
1. Ventral hippocampus (vCA3+vCA1) preferentially encodes contextual
   fear; dorsal-ventral functional dissociation —
   [Fanselow 2010, Neuron 65:7, doi:10.1016/j.neuron.2009.11.031]
2. vCA3 lesion impairs contextual fear conditioning while sparing water
   maze spatial memory; selective affective deficit —
   [Trivedi 2002, Behav Brain Res 137:67, PMID 12445998]
3. Ventral CA1/CA3 anxiety cells encode aversive contexts; selective
   activation drives anxiety-like behavior —
   [Jimenez 2018, Neuron 97:670, doi:10.1016/j.neuron.2018.01.016]
4. vCA3→vCA1 Schaffer projection is critical for retrieval of remote
   contextual fear memories; pathway-specific —
   [Stevenson 2021, Hippocampus 31:1041, doi:10.1002/hipo.23354]
5. Mossy-cell + DG mossy-fiber input to vCA3 follows same architecture
   as dCA3 — auto-associative —
   [Sun 2017, Neuron 95:656, doi:10.1016/j.neuron.2017.07.012]

INPUTS
======
- DentateGyrusPatternSep.dg_drive (mossy fiber)
- EntorhinalLateral.lec_drive (object/affective)
- ValenceTagger.valence_intensity, .valence_sign
- MedialSeptum.theta_signal

OUTPUTS
=======
- vca3_drive (0-1)
- ca3_output (alias)
- ventral_schaffer_output (0-1)
- affective_completion_signal (0-1)
- valence_bound_signal (0-1)
- vca3_state (str): "fear_completing" | "reward_completing" | "encoding" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA3Ventral(BrainMechanism):
    """vCA3 — affective pattern completion."""

    BASELINE = 0.10
    SMOOTH = 0.20
    COMPLETION_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="HippocampalCA3Ventral",
            human_analog="Ventral CA3 (affective auto-associative)",
            layer="limbic",
        )
        self.state.setdefault("vca3_drive", self.BASELINE)
        self.state.setdefault("ventral_schaffer_output", 0.0)
        self.state.setdefault("affective_completion_signal", 0.0)
        self.state.setdefault("valence_bound_signal", 0.0)
        self.state.setdefault("vca3_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recurrent_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, dg: float, lec: float, intensity: float,
                      theta: float, recurrent: float) -> float:
        """Composite vCA3 drive (Sun 2017 — same arch as dCA3)."""
        target = (self.BASELINE
                  + dg * 0.40
                  + lec * 0.20
                  + intensity * 0.15
                  + theta * 0.05
                  + recurrent * 0.20)
        return min(1.0, target)

    def _recurrent(self, drive: float, prev_trace: float) -> float:
        """Auto-associative recurrent dynamics (Marr-style)."""
        if drive < 0.20:
            return prev_trace * 0.80
        return min(1.0, prev_trace * 0.65 + drive * 0.35)

    def _affective_completion(self, drive: float, intensity: float,
                                recurrent: float) -> float:
        """Pattern completion of affective context (Trivedi 2002)."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.4 + intensity * 0.3 + recurrent * 0.3)

    def _valence_bound(self, completion: float, sign: int,
                        intensity: float) -> float:
        """Valence-bound attractor strength (Jimenez 2018)."""
        if completion < 0.20:
            return 0.0
        return min(1.0, completion * (0.5 + abs(sign) * 0.5) * (0.5 + intensity * 0.5))

    def _ventral_schaffer(self, drive: float, completion: float) -> float:
        """vCA3→vCA1 Schaffer (Stevenson 2021)."""
        return min(1.0, drive * 0.55 + completion * 0.45)

    def _classify_state(self, drive: float, completion: float, sign: int) -> str:
        if drive < 0.20:
            return "quiet"
        if completion > self.COMPLETION_THRESHOLD:
            if sign < 0:
                return "fear_completing"
            if sign > 0:
                return "reward_completing"
        return "encoding"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        dg_data = prior.get("DentateGyrusPatternSep", {})
        if not dg_data:
            dg_data = prior.get("DentateGyrus", {})
        dg = float(dg_data.get("dg_drive",
                          dg_data.get("dg_output", 0.0)))

        lec_data = prior.get("LateralEntorhinalCortex", {})
        if not lec_data:
            lec_data = prior.get("EntorhinalCortexGridCells", {})
        lec = float(lec_data.get("lec_drive",
                          lec_data.get("ec_output", 0.0)))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta = float(sept_data.get("theta_signal",
                            sept_data.get("theta_drive", 0.0)))

        prev_recurrent = float(self.state.get("recurrent_trace", 0.0))
        prev_drive = float(self.state.get("vca3_drive", self.BASELINE))

        target = self._drive_target(dg, lec, intensity, theta, prev_recurrent)
        new_drive = self._smooth(prev_drive, target)

        recurrent = self._recurrent(new_drive, prev_recurrent)
        completion = self._affective_completion(new_drive, intensity, recurrent)
        valence_bound = self._valence_bound(completion, sign, intensity)
        schaffer = self._ventral_schaffer(new_drive, completion)

        state = self._classify_state(new_drive, completion, sign)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vca3_drive"] = round(new_drive, 4)
        self.state["ventral_schaffer_output"] = round(schaffer, 4)
        self.state["affective_completion_signal"] = round(completion, 4)
        self.state["valence_bound_signal"] = round(valence_bound, 4)
        self.state["recurrent_trace"] = round(recurrent, 4)
        self.state["vca3_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vca3_drive": round(new_drive, 4),
            "ca3_output": round(new_drive, 4),  # alias
            "ventral_schaffer_output": round(schaffer, 4),
            "affective_completion_signal": round(completion, 4),
            "valence_bound_signal": round(valence_bound, 4),
            "vca3_state": state,
        }

    def _emotional_memory_strength(self) -> float:
        """Sustained valence-bound completion (Jimenez 2018)."""
        return float(self.state.get("valence_bound_signal", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vca3_drive", 0.0),
            "completion": self.state.get("affective_completion_signal", 0.0),
            "valence": self.state.get("valence_bound_signal", 0.0),
            "state": self.state.get("vca3_state", "quiet"),
        }

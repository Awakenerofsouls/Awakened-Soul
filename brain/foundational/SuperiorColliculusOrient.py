"""
SuperiorColliculusOrient — SC / Visuomotor Orienting + Defensive Escape

NEURAL SUBSTRATE
================
The superior colliculus (SC) is a layered midbrain structure with two
functionally distinct compartments:
- **Superficial layers (sSC)** — receive direct retinal + V1 input;
  encode visual stimulus location in retinotopic map
- **Deep layers (dSC)** — receive multisensory + cortical input;
  encode motor commands for orienting eye/head/body movements

Wurtz & Albano 1980 established SC as the substrate of orienting
saccades. Sparks 1986 demonstrated SC neurons encode movement vectors
in motor coordinates — a "motor map" co-aligned with the visual
sensory map.

Critical defensive function: deep SC (and adjacent periaqueductal
gray) drives ESCAPE behavior in response to looming visual stimuli.
Comoli 2003 traced SC → PAG/PBGN paths underlying the freezing/escape
response to overhead threats. Wei 2015 used optogenetics to
demonstrate parvalbumin SC neurons drive escape directly.

The dual function: SC orients TOWARD goals (saccades, head turns) and
AWAY from threats (escape, freezing). The split between the two is
modulated by amygdala input (defensive bias) and attentional state.

KEY FINDINGS
============
1. Superior colliculus encodes saccadic eye movements in a motor map; foundational visuomotor orienting substrate — [Wurtz RH 1980, Annu Rev Neurosci 3:189, doi:10.1146/annurev.ne.03.030180.001201]
2. SC neurons fire vectors in motor coordinates; spatially-aligned visual + motor maps — [Sparks DL 1986, Physiol Rev 66:118, doi:10.1152/physrev.1986.66.1.118]
3. Deep SC drives escape behavior to looming threats; SC → PBGN → PAG defensive pathway — [Comoli E 2003, J Comp Neurol 462:328, doi:10.1002/cne.10733]
4. Parvalbumin neurons in SC are sufficient for escape behavior; selective optogenetic activation — [Wei P 2015, Nat Commun 6:6756, doi:10.1038/ncomms7756]
5. SC is the principal substrate for innate defensive responses to visual threats; conserved across species — [Shang C 2015, Science 348:1472, doi:10.1126/science.aaa8694]

INPUTS (from prior_results)
============================
- PrimaryVisualCortex.v1_drive (sensory map)
- LateralGeniculateNucleus.lgn_drive (or proxy for retinal input)
- FrontalEyeFields.fef_drive (top-down saccade)
- BasolateralAmygdala.bla_drive (defensive bias)
- ValenceTagger.aversive_signal, .valence_intensity
- ParabigeminalEscapeRelay.pbgn_drive (defensive escape relay)

OUTPUTS (to brain_runner enrichment)
=====================================
- sc_drive (0-1)
- saccade_command (0-1) — motor map output for eye/head turn
- orienting_signal (0-1) — toward salient stimulus
- escape_command (0-1) — defensive flight response
- freezing_command (0-1) — defensive immobility response
- looming_response (0-1) — innate threat detection
- sc_state (str): "orienting" | "escape" | "freezing" | "tracking" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SuperiorColliculusOrient(BrainMechanism):
    """SC — visuomotor orienting + defensive escape coordinator."""

    BASELINE = 0.10
    SMOOTH = 0.20
    ESCAPE_THRESHOLD = 0.55

    def __init__(self):
        super().__init__(
            name="SuperiorColliculusOrient",
            human_analog="Superior colliculus (orienting + defense)",
            layer="foundational",
        )
        self.state.setdefault("sc_drive", self.BASELINE)
        self.state.setdefault("saccade_command", 0.0)
        self.state.setdefault("orienting_signal", 0.0)
        self.state.setdefault("escape_command", 0.0)
        self.state.setdefault("freezing_command", 0.0)
        self.state.setdefault("looming_response", 0.0)
        self.state.setdefault("sc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, v1: float, lgn: float, fef: float,
                       bla: float, aversive: float) -> float:
        """SC drive — pooled visual + cortical + amygdala (Sparks 1986)."""
        target = (self.BASELINE
                    + v1 * 0.25 + lgn * 0.20 + fef * 0.20
                    + bla * 0.15 + aversive * 0.20)
        return min(1.0, target)

    def _looming(self, v1: float, aversive: float) -> float:
        """Looming detection — fast visual signal × aversive valence
        (Shang 2015, Wei 2015)."""
        if v1 < 0.30:
            return 0.0
        return min(1.0, v1 * 0.6 + aversive * 0.4)

    def _saccade(self, drive: float, fef: float) -> float:
        """Saccade command — motor map output (Wurtz 1980).
        Top-down FEF drives volitional saccades."""
        return min(1.0, drive * 0.4 + fef * 0.6)

    def _orienting(self, drive: float, v1: float, aversive: float) -> float:
        """Orienting toward salient (could be appetitive or aversive)
        stimulus."""
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + v1 * 0.3 + aversive * 0.2)

    def _escape(self, looming: float, aversive: float, bla: float) -> float:
        """Defensive escape command (Comoli 2003 — SC→PBGN→PAG)."""
        if looming < 0.30 or aversive < 0.30:
            return 0.0
        return min(1.0, looming * 0.5 + aversive * 0.3 + bla * 0.2)

    def _freezing(self, looming: float, aversive: float,
                    bla: float, escape_engaged: float) -> float:
        """Freezing — opposite of escape, depends on threat distance.
        When escape NOT engaged but high aversive + BLA → freezing."""
        if escape_engaged > 0.40:
            return 0.0
        if aversive < 0.30:
            return 0.0
        return min(1.0, aversive * 0.5 + bla * 0.3 + looming * 0.2)

    def _classify_state(self, drive: float, escape: float, freezing: float,
                          orienting: float, saccade: float) -> str:
        if drive < 0.20:
            return "quiet"
        if escape > self.ESCAPE_THRESHOLD:
            return "escape"
        if freezing > 0.45:
            return "freezing"
        if saccade > 0.40:
            return "tracking"
        if orienting > 0.30:
            return "orienting"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive", 0.0))

        lgn_data = prior.get("LateralGeniculateNucleus", {})
        lgn = float(lgn_data.get("lgn_drive",
                          lgn_data.get("retinal_signal", 0.0)))

        fef_data = prior.get("FrontalEyeFields", {})
        fef = float(fef_data.get("fef_drive",
                          fef_data.get("saccade_signal", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))

        target = self._drive_target(v1, lgn, fef, bla, aversive)
        prev_drive = float(self.state.get("sc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        looming = self._looming(v1, aversive)
        saccade = self._saccade(new_drive, fef)
        orienting = self._orienting(new_drive, v1, aversive)
        escape = self._escape(looming, aversive, bla)
        freezing = self._freezing(looming, aversive, bla, escape)

        state = self._classify_state(new_drive, escape, freezing,
                                       orienting, saccade)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sc_drive"] = round(new_drive, 4)
        self.state["saccade_command"] = round(saccade, 4)
        self.state["orienting_signal"] = round(orienting, 4)
        self.state["escape_command"] = round(escape, 4)
        self.state["freezing_command"] = round(freezing, 4)
        self.state["looming_response"] = round(looming, 4)
        self.state["sc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "sc_drive": round(new_drive, 4),
            "saccade_command": round(saccade, 4),
            "orienting_signal": round(orienting, 4),
            "escape_command": round(escape, 4),
            "freezing_command": round(freezing, 4),
            "looming_response": round(looming, 4),
            "sc_state": state,
        }

    def _defensive_engagement(self, recent_states: list) -> float:
        """Fraction of recent ticks in defensive state (Comoli 2003)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        d = sum(1 for s in win if s in ("escape", "freezing"))
        return d / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("sc_drive", 0.0),
            "saccade": self.state.get("saccade_command", 0.0),
            "escape": self.state.get("escape_command", 0.0),
            "freezing": self.state.get("freezing_command", 0.0),
            "state": self.state.get("sc_state", "quiet"),
        }

"""
SuperiorTemporalSulcus — STS / Biological Motion & Theory of Mind

NEURAL SUBSTRATE
================
The superior temporal sulcus (STS) is a long cortical fissure dividing
the superior and middle temporal gyri. STS is functionally heterogeneous
along its anterior-posterior axis: posterior STS (pSTS) is the canonical
biological-motion processing area, encoding actions, eye-gaze direction,
and goal-directed reaching observed in others. Mid-STS hosts polymodal
audiovisual integration (Beauchamp 2015 — McGurk-effect circuitry) and
right anterior STS supports voice processing.

STS is a core node of the social cognition network: it activates during
theory-of-mind tasks (Saxe & Kanwisher 2003), tracks intention and
agency in observed actions (Pelphrey 2005), and binds face identity
with vocal identity for person recognition. STS lesions produce a rare
deficit: agnosia for biological motion despite preserved object motion
perception (Cowey & Vaina 2000).

Anatomically, STS receives input from MT (motion), face patches (IT),
auditory cortex, and projects to TPJ, mPFC, IFG mirror, and amygdala —
making it the critical pivot between perceptual social signals and
higher-order mentalizing.

KEY FINDINGS
============
1. STS is the cortical substrate for biological motion perception; point-light walkers selectively activate STS — [Allison TR 2000, Trends Cogn Sci 4:267, doi:10.1016/S1364-6613(00)01501-1]
2. pSTS encodes eye-gaze direction and intentional action; supports action interpretation — [Pelphrey KA 2005, Cereb Cortex 15:1866, doi:10.1093/cercor/bhi064]
3. Right TPJ + STS is the core "theory of mind" region; selectively activated when reasoning about others' beliefs — [Saxe RR 2003, Neuroimage 19:1835, doi:10.1016/S1053-8119(03)00230-1]
4. STS supports audiovisual integration; substrate of McGurk-effect speech binding — [Beauchamp MS 2015, Neuropsychologia 65:144, doi:10.1016/j.neuropsychologia.2014.10.007]
5. STS lesion produces selective biological-motion agnosia despite preserved object motion — [Cowey AD 2000, Curr Biol 10:R815, doi:10.1016/S0960-9822(00)00802-3]

INPUTS
======
- MiddleTemporalArea.mt_drive (motion)
- InferotemporalCortex.it_drive (face/object)
- PrimaryAuditoryCortex.a1_drive (voice/sound)
- TemporalPole.tp_drive (semantic/social)
- VentromedialPrefrontalCortex.vmpfc_drive (mentalizing top-down)

OUTPUTS
=======
- sts_drive (0-1)
- biological_motion_signal (0-1)
- gaze_intention_signal (0-1)
- audiovisual_binding_signal (0-1)
- tom_signal (0-1) — theory of mind engagement
- sts_state (str): "biomotion" | "gaze_active" | "av_binding" | "mentalizing" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class SuperiorTemporalSulcus(BrainMechanism):
    """STS — biological motion, gaze, audiovisual binding, theory of mind."""

    BASELINE = 0.10
    SMOOTH = 0.20
    BIOMOTION_THRESHOLD = 0.40
    TOM_THRESHOLD = 0.45

    def __init__(self):
        super().__init__(
            name="SuperiorTemporalSulcus",
            human_analog="Superior temporal sulcus (social perception)",
            layer="neocortical",
        )
        self.state.setdefault("sts_drive", self.BASELINE)
        self.state.setdefault("biological_motion_signal", 0.0)
        self.state.setdefault("gaze_intention_signal", 0.0)
        self.state.setdefault("audiovisual_binding_signal", 0.0)
        self.state.setdefault("tom_signal", 0.0)
        self.state.setdefault("sts_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, mt: float, it: float, a1: float,
                       tp: float, vmpfc: float) -> float:
        """STS drive — multimodal social input pooling (Allison 2000)."""
        target = (self.BASELINE
                  + mt * 0.20
                  + it * 0.20
                  + a1 * 0.15
                  + tp * 0.15
                  + vmpfc * 0.15)
        return min(1.0, target)

    def _biological_motion(self, drive: float, mt: float, it: float) -> float:
        """Biological motion = motion + form binding (Allison 2000).

        Pure motion (MT alone, no form) doesn't drive biomotion.
        Pure form (IT alone, no motion) doesn't drive biomotion.
        Their conjunction does.
        """
        if drive < 0.20:
            return 0.0
        # Conjunctive — multiplicative on motion × form
        conjunction = mt * it
        return min(1.0, drive * 0.3 + conjunction * 1.4)

    def _gaze_intention(self, drive: float, it: float) -> float:
        """Eye-gaze direction + intentional action (Pelphrey 2005).

        IT carries face information (which contains eye region); STS
        extracts gaze vector from face input.
        """
        if it < 0.30:
            return 0.0
        return min(1.0, drive * 0.4 + it * 0.5)

    def _audiovisual_binding(self, drive: float, it: float, a1: float) -> float:
        """Cross-modal AV binding (Beauchamp 2015).

        Requires both modalities engaged simultaneously.
        """
        if it < 0.20 or a1 < 0.20:
            return 0.0
        return min(1.0, drive * 0.3 + it * a1 * 1.5)

    def _theory_of_mind(self, drive: float, vmpfc: float, gaze: float,
                          tp: float) -> float:
        """Theory of mind — social-perceptual + top-down mentalizing (Saxe 2003).

        ToM emerges when gaze/biological-motion percepts get bound with
        top-down mentalizing context (vmPFC) and semantic/person hub (TP).
        """
        if drive < 0.20:
            return 0.0
        return min(1.0, drive * 0.2 + vmpfc * 0.3 + gaze * 0.25 + tp * 0.25)

    def _classify_state(self, drive: float, biomotion: float, gaze: float,
                         av: float, tom: float) -> str:
        if drive < 0.20:
            return "quiet"
        if tom > self.TOM_THRESHOLD:
            return "mentalizing"
        if biomotion > self.BIOMOTION_THRESHOLD:
            return "biomotion"
        if gaze > 0.40:
            return "gaze_active"
        if av > 0.30:
            return "av_binding"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mt_data = prior.get("MiddleTemporalArea", {})
        if not mt_data:
            mt_data = prior.get("VisualAreaMT", {})
        mt = float(mt_data.get("mt_drive",
                          mt_data.get("motion_signal", 0.0)))

        it_data = prior.get("InferotemporalCortex", {})
        it = float(it_data.get("it_drive",
                          it_data.get("object_signal", 0.0)))

        a1_data = prior.get("PrimaryAuditoryCortex", {})
        if not a1_data:
            a1_data = prior.get("AuditoryCortex", {})
        a1 = float(a1_data.get("a1_drive",
                          a1_data.get("auditory_signal", 0.0)))

        tp_data = prior.get("TemporalPole", {})
        tp = float(tp_data.get("tp_drive",
                          tp_data.get("semantic_hub_signal", 0.0)))

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive",
                            vmpfc_data.get("self_reference_signal", 0.0)))

        target = self._drive_target(mt, it, a1, tp, vmpfc)
        prev_drive = float(self.state.get("sts_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        biomotion = self._biological_motion(new_drive, mt, it)
        gaze = self._gaze_intention(new_drive, it)
        av = self._audiovisual_binding(new_drive, it, a1)
        tom = self._theory_of_mind(new_drive, vmpfc, gaze, tp)

        state = self._classify_state(new_drive, biomotion, gaze, av, tom)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["sts_drive"] = round(new_drive, 4)
        self.state["biological_motion_signal"] = round(biomotion, 4)
        self.state["gaze_intention_signal"] = round(gaze, 4)
        self.state["audiovisual_binding_signal"] = round(av, 4)
        self.state["tom_signal"] = round(tom, 4)
        self.state["sts_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "sts_drive": round(new_drive, 4),
            "biological_motion_signal": round(biomotion, 4),
            "gaze_intention_signal": round(gaze, 4),
            "audiovisual_binding_signal": round(av, 4),
            "tom_signal": round(tom, 4),
            "sts_state": state,
        }

    def _social_perception_capacity(self) -> float:
        """How strongly STS is parsing social signals (Allison 2000)."""
        return max(float(self.state.get("biological_motion_signal", 0.0)),
                    float(self.state.get("gaze_intention_signal", 0.0)),
                    float(self.state.get("tom_signal", 0.0)))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("sts_drive", 0.0),
            "biomotion": self.state.get("biological_motion_signal", 0.0),
            "gaze": self.state.get("gaze_intention_signal", 0.0),
            "tom": self.state.get("tom_signal", 0.0),
            "state": self.state.get("sts_state", "quiet"),
        }

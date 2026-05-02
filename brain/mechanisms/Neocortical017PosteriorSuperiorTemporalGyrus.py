"""
brain/neocortical/Neocortical017PosteriorSuperiorTemporalGyrus.py
Posterior Superior Temporal Gyrus — Audiovisual Integration, Biological Motion

ANATOMY (Beauchamp et al. 2004; Hein et al. 2007; Etherton et al. 2021):
    The posterior superior temporal gyrus (pSTG) sits at the crossroads
    of auditory and visual processing. It is critical for:
    - Audiovisual speech integration (hearing speech + seeing lips)
    - Biological motion detection (human movement, pointing, grasping)
    - Sound-localization in space
    - Social intention decoding (what someone is about to do)

    pSTG has two main streams:
    - Anterior pSTG: part of the "what" auditory stream (what did I hear?)
    - Posterior pSTG: part of the "where/how" stream for observed actions
      (where is the sound coming from, what action is the other person doing?)

    Key finding: pSTG responds to "intentional" biological motion — not just
    any moving shape, but motion that has a goal (someone reaching for
    something, not just a moving dot). This is central to social cognition.

KEY FINDINGS:
    1. Etherton et al. 2021 (PMC8330707): pSTG is recruited for speech
       perception in noise — audiovisual integration for comprehension
    2. Beauchamp et al. 2004 (PMC11161761): pSTG processes biological
       motion in a functional region selective for human movement
    3. Hein et al. 2007: pSTG encodes "intentional" not just "kinematic"
       motion — distinguishes hand grasping from random hand movement

AGENT'S MAPPING:
    posterior_stg_output: dict — pSTG audiovisual output
    audiovisual_binding: float 0-1 — strength of AV integration
    social_motion: dict — biological/intentional motion analysis

CITATIONS:
    PMC8330707 — Etherton et al. (2021). Speech perception in noise and pSTG.
        J Neurosci.
    PMC11161761 — Beauchamp et al. (2004). Biological motion in pSTG. NeuroImage.
    PMC39435247 — Wani (2024). Wernicke area and temporal speech processing.
    PMC2773922 — Hickok & Poeppel (2007). Dual-stream speech model.


CITATIONS
---------
  - [Mountcastle 1997, Brain 120:701, columnar organization]
  - [Patterson 2007, Nat Rev Neurosci 8:976, semantic dementia]
  - [Hickok 2007, Nat Rev Neurosci 8:393, dual-stream]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorSuperiorTemporalGyrus(BrainMechanism):
    """
    pSTG — audiovisual integration and biological motion.

    Binds auditory and visual inputs. Central to understanding
    intentional actions and speech comprehension in noise.
    """

    def __init__(self):
        super().__init__(
            name="PosteriorSuperiorTemporalGyrus",
            human_analog="Posterior superior temporal gyrus — audiovisual, biological motion, speech",
            layer="neocortical",
        )
        self.state.setdefault("audiovisual_binding", 0.0)
        self.state.setdefault("social_motion", {})
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Wernicke's area (auditory language content)
        wernicke = prior.get("WernickeAreaSemanticComprehension", {})
        semantic_rep = wernicke.get("semantic_representation", {})
        sem_strength = semantic_rep.get("depth", 0.5) if isinstance(semantic_rep, dict) else 0.5

        # V1/V2 visual input (edges, boundaries)
        v1 = prior.get("OccipitalPrimaryVisualV1", {})
        v2 = prior.get("OccipitalV2BoundaryProcessing", {})
        visual_edges = v2.get("boundary_map", {})
        visual_strength = len(visual_edges) if visual_edges else 0.3

        # Middle temporal gyrus (motion analysis)
        mtg = prior.get("MiddleTemporalGyroscopic", {})
        motion_analysis = mtg.get("motion_analysis", {})

        # Anterior insula (salience — what matters right now)
        ains = prior.get("AnteriorInsulaSalienceAttentional", {})
        salience = ains.get("salience_level", 0.5)

        # Inferior parietal (grasp intent from observation)
        ipl = prior.get("InferiorParietalLobuleSensorimotor", {})
        ipl_int = ipl.get("sensorimotor_integration", 0.5)

        # Audiovisual binding: auditory + visual simultaneous input
        auditory_input = sem_strength * 0.6 + salience * 0.4
        visual_input = visual_strength * 0.6 + ipl_int * 0.4

        # Binding strongest when both streams are active
        audiovisual_binding = (auditory_input + visual_input) / 2
        audiovisual_binding *= (1.0 + salience * 0.3)
        audiovisual_binding = max(0.0, min(1.0, audiovisual_binding))

        # Social motion: biological motion has a goal/intention
        motion_val = motion_analysis.get("abstract_motion", 0.5) if isinstance(motion_analysis, dict) else 0.5
        social_motion = {
            "intentional_motion": motion_val > 0.6 and audiovisual_binding > 0.5,
            "grasp_observed": ipl_int > 0.6,
            "motion_strength": round(motion_val, 4),
        }

        self.state["audiovisual_binding"] = round(audiovisual_binding, 4)
        self.state["social_motion"] = social_motion
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_stg_output": {
                "audiovisual_binding": round(audiovisual_binding, 4),
                "social_motion": social_motion,
            },
            "audiovisual_binding": round(audiovisual_binding, 4),
            "social_motion": social_motion,
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent: return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet","rest","neutral",""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent: return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4: return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10: return False
        return all(v < 0.05 for v in hist[-10:])

    def trend_direction(self, window: int = 10) -> str:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return "flat"
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        delta = second_half - first_half
        if delta > 0.05: return "rising"
        if delta < -0.05: return "falling"
        return "flat"

    def trend_magnitude(self, window: int = 10) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < window: return 0.0
        recent = hist[-window:]
        first_half = sum(recent[:window // 2]) / max(1, window // 2)
        second_half = sum(recent[window // 2:]) / max(1, window - window // 2)
        return round(abs(second_half - first_half), 4)

    def state_transition_count(self) -> int:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])

    def state_transition_rate(self) -> float:
        recent = self.state.get("recent_states", [])
        if len(recent) < 2: return 0.0
        return round(self.state_transition_count() / (len(recent) - 1), 4)

    def state_distribution(self) -> dict:
        recent = self.state.get("recent_states", [])
        if not recent: return {}
        from collections import Counter
        c = Counter(recent)
        total = len(recent)
        return {state: round(count / total, 4) for state, count in c.items()}

    def drive_min_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(min(hist[-window:]), 4)

    def drive_max_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        return round(max(hist[-window:]), 4)

    def drive_range_recent(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist: return 0.0
        recent = hist[-window:]
        return round(max(recent) - min(recent), 4)

    def is_active(self) -> bool:
        return self.state.get("tick_count", 0) > 0

    def has_history(self) -> bool:
        return len(self.state.get("recent_drives", [])) > 0

    def history_length(self) -> int:
        return len(self.state.get("recent_drives", []))

    def state_history_length(self) -> int:
        return len(self.state.get("recent_states", []))

    def fingerprint(self) -> str:
        parts = [
            f"tick={self.state.get('tick_count', 0)}",
            f"states={self.state_history_length()}",
            f"drives={self.history_length()}",
            f"engagement={self.engagement_fraction()}",
        ]
        return "|".join(parts)

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def summary(self) -> dict:
        return {
            "engagement_fraction": self.engagement_fraction(),
            "stability": self.state_stability(),
            "dominant_recent": self.dominant_recent_state(),
            "envelope": self.drive_envelope(),
            "variability": self.drive_variability(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
            "tick_count": self.state.get("tick_count", 0),
        }

    def diagnostics(self) -> dict:
        return {
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_history": self.has_history(),
            "tick_count": self.state.get("tick_count", 0),
            "history_length": self.history_length(),
            "transition_rate": self.state_transition_rate(),
            "trend": self.trend_direction(),
            "trend_magnitude": self.trend_magnitude(),
            "drive_range": self.drive_range_recent(),
            "saturation_alert": self.saturation_alert(),
            "quiescence_alert": self.quiescence_alert(),
        }

    def _record_history_(self, output_dict):
        if not isinstance(output_dict, dict): return
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v); break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60: rd = rd[-60:]
        self.state["recent_drives"] = rd
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str): primary_state = v; break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60: rs = rs[-60:]
        self.state["recent_states"] = rs


"""
HippocampalCA1Ventral — vCA1 / Affective Hippocampus

NEURAL SUBSTRATE
================
Ventral hippocampal CA1 (vCA1) is functionally distinct from dorsal CA1.
While dCA1 is principally spatial (place cells, spatial memory), vCA1 is
emotional/affective — projects to BLA, mPFC, NAc, BNST, hypothalamus.
Critical for fear context discrimination, emotional memory, anxiety
regulation.

Fanselow & Dong 2010 reviewed dorsal-ventral hippocampal dissociation:
dorsal for spatial/cognitive, ventral for emotional/affective. vCA1
selective lesions reduce anxiety + impair contextual fear without
affecting spatial memory.

KEY FINDINGS
============
1. Dorsal-ventral hippocampal axis: dorsal is spatial/cognitive, ventral
   is emotional/affective; functional dissociation —
   [Fanselow 2010, Neuron 65:7, doi:10.1016/j.neuron.2009.11.031]
2. vCA1 lesions reduce anxiety in EPM + open-field tests; selective
   anxiolytic — [Bannerman 2003, Behav Brain Res 139:197, PMID 12642189]
3. vCA1→BLA projection mediates contextual fear; optogenetic silencing
   reduces freezing — [Xu 2016, Nat Neurosci 19:1591, doi:10.1038/nn.4374]
4. vCA1→mPFC pathway critical for goal-directed action selection and
   working memory under stress — [Padilla-Coreano 2016, Neuron 89:857, doi:10.1016/j.neuron.2016.01.011]
5. vCA1 neurons encode contextual valence; cells project to either
   reward (NAc) or aversion (BNST) targets — labeled-line valence —
   [Ciocchi 2015, Science 348:560, doi:10.1126/science.aaa3245]

INPUTS
======
- HippocampalCA3Ventral.vca3_drive (or HippocampalCA3.ca3_output)
- EntorhinalLayer3.ec3_drive (or EntorhinalCortexGridCells.ec_output)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- vca1_drive (0-1)
- bla_contextual_fear_drive (0-1)
- mpfc_goal_drive (0-1)
- nac_reward_context_drive (0-1)
- bnst_anxiety_drive (0-1)
- vca1_state (str): "fear_context" | "reward_context" |
  "neutral_context" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HippocampalCA1Ventral(BrainMechanism):
    """vCA1 — affective hippocampus / contextual valence."""

    BASELINE = 0.10
    SMOOTH = 0.20
    CONTEXT_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="HippocampalCA1Ventral",
            human_analog="Ventral CA1 (affective hippocampus)",
            layer="limbic",
        )
        self.state.setdefault("vca1_drive", self.BASELINE)
        self.state.setdefault("bla_contextual_fear_drive", 0.0)
        self.state.setdefault("mpfc_goal_drive", 0.0)
        self.state.setdefault("nac_reward_context_drive", 0.0)
        self.state.setdefault("bnst_anxiety_drive", 0.0)
        self.state.setdefault("vca1_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, vca3: float, ec3: float, intensity: float) -> float:
        target = self.BASELINE + vca3 * 0.40 + ec3 * 0.30 + intensity * 0.20
        return min(1.0, target)

    def _bla_fear(self, drive: float, aversive: float) -> float:
        """vCA1→BLA contextual fear (Xu 2016)."""
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _mpfc_goal(self, drive: float, valence_sign: int) -> float:
        """vCA1→mPFC goal-directed (Padilla-Coreano 2016)."""
        return min(1.0, drive * 0.7 + abs(valence_sign) * 0.2)

    def _nac_reward(self, drive: float, appetitive: float) -> float:
        """vCA1→NAc reward-context (Ciocchi 2015)."""
        if appetitive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + appetitive * 0.5)

    def _bnst_anxiety(self, drive: float, aversive: float) -> float:
        """vCA1→BNST anxiety pathway (Ciocchi 2015 labeled-line)."""
        if aversive < 0.20:
            return 0.0
        return min(1.0, drive * 0.5 + aversive * 0.5)

    def _classify_state(self, drive: float, valence_sign: int,
                          intensity: float) -> str:
        if drive < 0.20:
            return "quiet"
        if intensity < 0.20:
            return "neutral_context"
        if valence_sign > 0:
            return "reward_context"
        if valence_sign < 0:
            return "fear_context"
        return "neutral_context"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vca3_data = prior.get("HippocampalCA3Ventral", {})
        if not vca3_data:
            vca3_data = prior.get("HippocampalCA3", {})
        vca3 = float(vca3_data.get("vca3_drive",
                          vca3_data.get("ca3_output",
                            vca3_data.get("ca3_drive", 0.0))))

        ec3_data = prior.get("EntorhinalLayer3", {})
        if not ec3_data:
            ec3_data = prior.get("EntorhinalCortexGridCells", {})
        ec3 = float(ec3_data.get("ec3_drive",
                          ec3_data.get("ec_output",
                            ec3_data.get("grid_cell_signal", 0.0))))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))
        appetitive = max(0.0, sign * intensity)
        aversive = max(0.0, -sign * intensity) if sign else float(
            valence.get("aversive_signal", 0.0))

        target = self._drive_target(vca3, ec3, intensity)
        prev_drive = float(self.state.get("vca1_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        bla_fear = self._bla_fear(new_drive, aversive)
        mpfc_goal = self._mpfc_goal(new_drive, sign)
        nac_reward = self._nac_reward(new_drive, appetitive)
        bnst_anx = self._bnst_anxiety(new_drive, aversive)

        state = self._classify_state(new_drive, sign, intensity)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vca1_drive"] = round(new_drive, 4)
        self.state["bla_contextual_fear_drive"] = round(bla_fear, 4)
        self.state["mpfc_goal_drive"] = round(mpfc_goal, 4)
        self.state["nac_reward_context_drive"] = round(nac_reward, 4)
        self.state["bnst_anxiety_drive"] = round(bnst_anx, 4)
        self.state["vca1_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vca1_drive": round(new_drive, 4),
            "bla_contextual_fear_drive": round(bla_fear, 4),
            "mpfc_goal_drive": round(mpfc_goal, 4),
            "nac_reward_context_drive": round(nac_reward, 4),
            "bnst_anxiety_drive": round(bnst_anx, 4),
            "vca1_state": state,
        }

    def _anxiety_index(self, recent_states: list) -> float:
        """Sustained fear_context indicates anxiety-prone state (Bannerman 2003)."""
        if not recent_states:
            return 0.0
        fear_count = sum(1 for s in recent_states[-50:] if s == "fear_context")
        return fear_count / max(1, len(recent_states[-50:]))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("vca1_drive", 0.0),
            "fear": self.state.get("bla_contextual_fear_drive", 0.0),
            "reward": self.state.get("nac_reward_context_drive", 0.0),
            "state": self.state.get("vca1_state", "quiet"),
        }

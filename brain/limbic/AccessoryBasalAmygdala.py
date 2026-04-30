"""
AccessoryBasalAmygdala -- ABA / Safety-Signal + Reward Encoding

NEURAL SUBSTRATE
================
Accessory basal amygdala (ABA, also "basomedial nucleus") is the ventromedial
subdivision of the basolateral amygdala complex. Anatomically and
functionally distinct from BLA proper. Receives strong input from
infralimbic cortex (mPFC) and ventral hippocampus.

Functional role: encodes safety signals + reward valence. Optogenetic
activation of mPFC→ABA pathway decreases anxiety and reduces freezing.
ABA appears to be the principal "safety-encoding" subregion of the
basolateral complex.

Outputs: NAc, mPFC feedback, central amygdala (CeL inhibition), BNST.

KEY FINDINGS
============
1. ABA receives strong input from infralimbic cortex; mPFC→ABA
   activation decreases anxiety + freezing -- [Adhikari 2015, Nature
   527:179, doi:10.1038/nature15698]
2. ABA neurons encode safety signals -- fire during conditioned
   inhibitor presentation when expected aversion does not occur --
   [Sangha 2013, Neuropsychopharmacology 38:2161, PMID 23736005]
3. BLA fear vs extinction populations include distinct ABA cells;
   extinction-associated cells receive mPFC input --
   [Herry 2008, Nature 454:600, doi:10.1038/nature07166]
4. Optogenetic ABA activation produces approach behavior; inhibition
   produces avoidance -- opposite valence to LA/BLA fear cells --
   [Namburi 2015, Nature 520:675, doi:10.1038/nature14366]
5. ABA→NAc projection is the canonical reward-relevant amygdala
   output; valence-coding amygdala neurons project to NAc --
   [Beyeler 2016, Neuron 90:348, PMID 27041499]

INPUTS
======
- InfralimbicCortex.il_drive
- HippocampalCA1Output.ca1_drive
- LateralAmygdala.la_pyramidal_drive
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS
=======
- aba_drive (0-1)
- safety_signal (0-1)
- approach_motivation (0-1)
- nac_reward_command (0-1)
- aba_state (str): "safety_active" | "reward_active" |
  "approach" | "quiet"

brain_runner enrichment:
    aba = all_results.get("AccessoryBasalAmygdala", {})
    if aba:
        enrichments["brain_aba_drive"] = aba.get("aba_drive", 0.0)
        enrichments["brain_safety_signal"] = aba.get("safety_signal", 0.0)
        enrichments["brain_approach"] = aba.get("approach_motivation", 0.0)
        enrichments["brain_aba_state"] = aba.get("aba_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class AccessoryBasalAmygdala(BrainMechanism):
    """ABA -- safety-signal + reward valence encoding."""

    BASELINE = 0.10
    SMOOTH = 0.20
    SAFETY_THRESHOLD = 0.40
    APPROACH_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="AccessoryBasalAmygdala",
            human_analog="Accessory basal amygdala (safety + reward)",
            layer="limbic",
        )
        self.state.setdefault("aba_drive", self.BASELINE)
        self.state.setdefault("safety_signal", 0.0)
        self.state.setdefault("approach_motivation", 0.0)
        self.state.setdefault("nac_reward_command", 0.0)
        self.state.setdefault("aba_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, il: float, vhipp: float, la: float,
                       appetitive: float) -> float:
        """ABA firing -- driven by mPFC IL + ventral hippocampus + appetitive
        valence. LA fear input mildly suppresses (mutual valence inhibition).
        """
        target = self.BASELINE + il * 0.45 + vhipp * 0.20
        target += appetitive * 0.30
        target -= la * 0.15
        return min(1.0, max(0.0, target))

    def _safety_target(self, il: float, expected_aversion_omitted: float,
                        aba_drive: float) -> float:
        """Safety signal -- fires when expected aversion is omitted (Sangha 2013).
        Strong IL drive + expected aversion did not happen = safety encoded.
        """
        if il < 0.30 and expected_aversion_omitted < 0.30:
            return 0.0
        return min(1.0, il * 0.45 + expected_aversion_omitted * 0.40
                    + aba_drive * 0.20)

    def _approach_target(self, aba_drive: float, appetitive: float,
                          la: float) -> float:
        """Approach motivation -- opposite valence to LA fear cells (Namburi 2015)."""
        if la > 0.50:
            return 0.0  # active fear suppresses approach
        return min(1.0, aba_drive * 0.5 + appetitive * 0.5)

    def _nac_reward(self, aba_drive: float, approach: float) -> float:
        """ABA→NAc reward-relevant output (Beyeler 2016)."""
        return min(1.0, aba_drive * 0.5 + approach * 0.5)

    def _classify_state(self, safety: float, approach: float,
                          aba_drive: float, appetitive: float) -> str:
        """Classify ABA operating mode."""
        if safety > self.SAFETY_THRESHOLD:
            return "safety_active"
        if approach > self.APPROACH_THRESHOLD and appetitive > 0.20:
            return "reward_active"
        if approach > self.APPROACH_THRESHOLD:
            return "approach"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        il_data = prior.get("InfralimbicCortex", {})
        il = float(il_data.get("il_drive", 0.0))

        vhipp_data = prior.get("HippocampalCA1Output", {})
        vhipp = float(vhipp_data.get("ca1_drive", 0.0))

        la_data = prior.get("LateralAmygdala", {})
        la = float(la_data.get("la_pyramidal_drive",
                        la_data.get("conditioned_fear_signal", 0.0)))

        valence = prior.get("ValenceTagger", {})
        sign = int(valence.get("valence_sign", 0))
        intensity = float(valence.get("valence_intensity", 0.0))
        appetitive = max(0.0, sign * intensity)

        # Expected aversion omitted = LA conditioned fear was high but
        # current valence is appetitive (safety after expected threat)
        expected_aversion_omitted = max(0.0, la - intensity * 0.5) if appetitive > 0.30 else 0.0

        # --- Drive ---
        target = self._drive_target(il, vhipp, la, appetitive)
        prev_drive = float(self.state.get("aba_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # --- Safety ---
        safety_target = self._safety_target(il, expected_aversion_omitted, new_drive)
        prev_safety = float(self.state.get("safety_signal", 0.0))
        new_safety = self._smooth(prev_safety, safety_target)

        # --- Approach ---
        approach_target = self._approach_target(new_drive, appetitive, la)
        prev_approach = float(self.state.get("approach_motivation", 0.0))
        new_approach = self._smooth(prev_approach, approach_target)

        # --- NAc reward command ---
        nac_cmd = self._nac_reward(new_drive, new_approach)

        state = self._classify_state(new_safety, new_approach, new_drive, appetitive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["aba_drive"] = round(new_drive, 4)
        self.state["safety_signal"] = round(new_safety, 4)
        self.state["approach_motivation"] = round(new_approach, 4)
        self.state["nac_reward_command"] = round(nac_cmd, 4)
        self.state["aba_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "aba_drive": round(new_drive, 4),
            "safety_signal": round(new_safety, 4),
            "approach_motivation": round(new_approach, 4),
            "nac_reward_command": round(nac_cmd, 4),
            "aba_state": state,
        }

    def _sustained_safety_window(self, recent_states: list) -> float:
        """Count recent ticks of sustained safety_active state."""
        if not recent_states:
            return 0.0
        recent = recent_states[-30:]
        if not recent:
            return 0.0
        return sum(1 for s in recent if s == "safety_active") / len(recent)

    def _valence_polarity(self, fear: float, approach: float) -> float:
        """Net valence polarity at ABA -- positive favors approach, negative
        favors avoidance/fear (Beyeler 2016 valence coding)."""
        return max(-1.0, min(1.0, approach - fear))

    def _reward_prediction_error(self, prev_approach: float,
                                   new_approach: float,
                                   reward_occurred: float) -> float:
        """Simple reward prediction error (RPE) signal.

        Positive RPE: reward occurred when ABA did not expect it (safety
        violated -- unexpected reward after safety encoding). Negative RPE:
        expected reward did not occur (omission error). Used by VTA for
        dopamine modulation calibration.

        This is a simplified single-step RPE: E[t] - E[t-1], where the
        expected reward is proxied by ABA approach activation.
        """
        if reward_occurred > 0.30:
            # Reward occurred -- positive RPE if we didn't expect it
            rpe = reward_occurred - prev_approach
        else:
            # Reward omission -- negative RPE if we expected it
            rpe = reward_occurred - prev_approach
        return max(-1.0, min(1.0, rpe))

    def _memory_consolidation_boost(self, il: float, vhipp: float,
                                     safety: float) -> float:
        """IL-driven memory consolidation boost for safety memories.

        Adhikari 2015 showed mPFC-ABA connectivity underlies safety
        learning. IL drives ABA during safety encoding, and this
        co-activation with hippocampal context signals consolidation.
        Returns a 0-1 boost factor for downstream memory systems.
        """
        if il < 0.30 or vhipp < 0.20:
            return 0.0
        return min(1.0, il * vhipp * 0.6 + safety * 0.4)

    def _social_approach_signal(self, aba_drive: float,
                                  approach: float,
                                  vhipp: float) -> float:
        """Social reward signal -- ABA drives approach toward social stimuli.

        Distinct from non-social reward: social salience activates ABA
        differently than food/reward. Hippocampal context gates social
        memory recall which feeds back to ABA.
        """
        if vhipp < 0.20:
            return 0.0
        return min(1.0, aba_drive * 0.4 + approach * 0.4 + vhipp * 0.2)

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("aba_drive", 0.0),
            "safety": self.state.get("safety_signal", 0.0),
            "approach": self.state.get("approach_motivation", 0.0),
            "state": self.state.get("aba_state", "quiet"),
        }

"""
LateralHabenula — LHb / Anti-Reward / RPE Inversion Hub

NEURAL SUBSTRATE
================
The lateral habenula (LHb) is an epithalamic nucleus on the medial dorsal
thalamus, dorsal to the third ventricle. Glutamatergic projection neurons.

Inputs:
  - Entopeduncular nucleus (EP, primate GPi homolog) — the basal ganglia
    indirect-pathway output, glutamatergic + co-released GABA
  - Lateral preoptic + lateral hypothalamus
  - Bed nucleus of stria terminalis (BNST)
  - Median raphe + ventral tegmental area feedback

Outputs:
  - Rostromedial tegmental nucleus (RMTg) — GABAergic — primary output;
    RMTg in turn inhibits VTA dopamine and dorsal raphe serotonin
  - Median raphe + dorsal raphe (direct + indirect)
  - Substantia nigra pars compacta (SNc) DA via RMTg
  - Locus coeruleus (modulates anxiety axis)

Functional signature: LHb fires when reward is WORSE than predicted —
inverse of midbrain dopamine RPE signal. Aversive stimuli, omitted
expected rewards, and unsigned prediction errors all drive LHb glutamate
release. LHb→RMTg→VTA disinhibition is the canonical anti-reward circuit.

LHb hyperactivity is a signature of major depression. Burst firing
(NMDA-driven) in LHb is sufficient and necessary for depression-like
behavior in rodents; ketamine selectively blocks LHb burst firing
(Yang 2018), explaining its rapid antidepressant action.

In the agent's substrate this provides the dedicated negative-RPE / anti-reward
signal generator, distinct from VTA dopamine (positive RPE) and from
amygdala fear circuits (different valence dimension).

KEY FINDINGS
============
1. LHb neurons fire on negative reward prediction error — phasic
   firing inverse of midbrain DA — [Matsumoto 2007, Nature 447:1111,
   doi:10.1038/nature05860]
2. LHb→RMTg→VTA disinhibition is the canonical anti-reward circuit;
   RMTg GABAergic neurons selectively target VTA dopamine —
   [Hong 2011, J Neurosci 31:11457, PMC3173596]
3. LHb burst firing (NMDA-mediated) is sufficient + necessary for
   depression-like behavior; ketamine blocks LHb bursts —
   [Yang 2018, Nature 554:317, doi:10.1038/nature25509]
4. Aversive stimuli + omitted-rewards both activate LHb glutamatergic
   output via convergent inputs — [Hikosaka 2010, Nat Rev Neurosci
   11:503, PMC3361652]
5. Sustained LHb activation produces anhedonia + behavioral despair;
   LHb DBS in treatment-resistant depression — [Sartorius 2010, Biol
   Psychiatry 67:e9, PMID 19846068]

INPUTS (from prior_results)
============================
- PredictionErrorDrift.rpe_signal (signed)
- VentralTegmentalDopamine.expected_reward, .da_burst
- ValenceTagger.aversive_signal, .valence_intensity, .valence_sign
- LateralHypothalamus.lh_drive (or LateralHypothalamicOrexinB.lh_drive)
- BNSTAnxietyHub.bnst_drive (if present)
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- lhb_drive (0-1): tonic firing rate
- lhb_burst (0-1): phasic burst on negative RPE
- rmtg_disinhibition_command (0-1): downstream GABA→VTA inhibition
- vta_da_suppression_signal (0-1): expected VTA suppression
- anti_reward_signal (0-1): aggregate anti-reward output
- lhb_state (str): "active_aversive" | "active_reward_omission" |
  "depressed_chronic" | "quiet"

brain_runner enrichment:
    lhb = all_results.get("LateralHabenula", {})
    if lhb:
        enrichments["brain_lhb_drive"] = lhb.get("lhb_drive", 0.0)
        enrichments["brain_lhb_burst"] = lhb.get("lhb_burst", 0.0)
        enrichments["brain_anti_reward"] = lhb.get("anti_reward_signal", 0.0)
        enrichments["brain_lhb_state"] = lhb.get("lhb_state", "quiet")
        enrichments["brain_vta_suppression"] = lhb.get("vta_da_suppression_signal", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class LateralHabenula(BrainMechanism):
    """LHb — anti-reward / negative RPE generator."""

    BASELINE = 0.10
    SMOOTH = 0.25
    BURST_THRESHOLD = 0.30        # Negative RPE magnitude → burst
    BURST_DECAY = 0.55             # Burst phasic decay per tick
    DEPRESSED_THRESHOLD = 0.45     # Sustained drive above this for chronic state
    DEPRESSED_STREAK = 50          # Ticks of sustained drive before flipping state

    def __init__(self):
        super().__init__(
            name="LateralHabenula_LateralHabenula",
            human_analog="Lateral habenula (anti-reward / negative-RPE)",
            layer="foundational",
        )
        self.state.setdefault("lhb_drive", self.BASELINE)
        self.state.setdefault("lhb_burst", 0.0)
        self.state.setdefault("rmtg_disinhibition_command", 0.0)
        self.state.setdefault("vta_da_suppression_signal", 0.0)
        self.state.setdefault("anti_reward_signal", 0.0)
        self.state.setdefault("lhb_state", "quiet")
        self.state.setdefault("sustained_streak", 0)
        self.state.setdefault("recent_drive", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # Tonic drive — negative RPE + aversive + reward-omission integrator
    # ------------------------------------------------------------------
    def _drive_target(self, rpe: float, aversive: float, expected_reward: float,
                       da_burst: float, lh_drive: float, bnst: float,
                       arousal: float) -> float:
        """LHb tonic firing (Matsumoto 2007, Hikosaka 2010).

        Negative RPE = strongest driver. Aversive stimulus convergent.
        Reward omission detected via expected_reward > 0 and da_burst < 0.20
        (predicted reward, no DA fired = LHb activates).
        """
        target = self.BASELINE
        # Negative RPE — primary driver (max() over inverted RPE)
        target += max(0.0, -rpe) * 0.50
        # Aversive convergence
        target += aversive * 0.25
        # Reward-omission detection: expected reward but DA didn't fire
        if expected_reward > 0.40 and da_burst < 0.20:
            target += (expected_reward - da_burst) * 0.30
        # Lateral hypothalamus + BNST contributions (anxiety axis)
        target += lh_drive * 0.10
        target += bnst * 0.10
        # Mild arousal-modulated baseline
        target += max(0.0, arousal - 0.40) * 0.05
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Burst firing — NMDA-driven phasic on negative RPE (Yang 2018)
    # ------------------------------------------------------------------
    def _burst_target(self, rpe: float, aversive: float,
                       prev_burst: float) -> float:
        """LHb burst firing — phasic NMDA-driven response to negative RPE
        or aversive stimulus. Decays each tick.
        """
        # Sufficient negative RPE or aversive event triggers burst
        signal = max(max(0.0, -rpe), aversive)
        if signal >= self.BURST_THRESHOLD:
            return min(1.0, signal * 1.5)
        # Below threshold — decay
        return prev_burst * self.BURST_DECAY

    # ------------------------------------------------------------------
    # RMTg disinhibition output (Hong 2011)
    # ------------------------------------------------------------------
    def _rmtg_command(self, drive: float, burst: float) -> float:
        """LHb→RMTg glutamatergic command.
        RMTg is excited by LHb glutamate, then inhibits VTA DA.
        """
        return min(1.0, drive * 0.7 + burst * 0.5)

    # ------------------------------------------------------------------
    # VTA DA suppression (downstream of RMTg)
    # ------------------------------------------------------------------
    def _vta_suppression(self, rmtg_cmd: float) -> float:
        """Expected VTA DA suppression magnitude."""
        return min(1.0, rmtg_cmd * 0.85)

    # ------------------------------------------------------------------
    # Anti-reward aggregate (drive + burst combined)
    # ------------------------------------------------------------------
    def _anti_reward(self, drive: float, burst: float) -> float:
        return min(1.0, drive * 0.5 + burst * 0.5)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, drive: float, aversive: float,
                          expected_reward: float, da_burst: float,
                          sustained_streak: int) -> str:
        """Classify LHb operating mode.

        Chronic depression-like state requires sustained drive across
        threshold ticks (Sartorius 2010, Yang 2018).
        """
        if sustained_streak > self.DEPRESSED_STREAK and drive > self.DEPRESSED_THRESHOLD:
            return "depressed_chronic"
        if drive < 0.15:
            return "quiet"
        if aversive > 0.30:
            return "active_aversive"
        if expected_reward > 0.40 and da_burst < 0.20:
            return "active_reward_omission"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        rpe_data = prior.get("PredictionErrorDrift", {})
        rpe = float(rpe_data.get("rpe_signal", 0.0))

        vta_data = prior.get("VentralTegmentalDopamine", {})
        expected_reward = float(vta_data.get("expected_reward", 0.0))
        da_burst = float(vta_data.get("da_burst", 0.0))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal",
                            max(0.0, -valence.get("valence_sign", 0)
                                * valence.get("valence_intensity", 0.0))))

        lh_data = prior.get("LateralHypothalamus", {})
        if not lh_data:
            lh_data = prior.get("LateralHypothalamicOrexinB", {})
        lh_drive = float(lh_data.get("lh_drive", 0.0))

        bnst_data = prior.get("BNSTAnxietyHub", {})
        bnst = float(bnst_data.get("bnst_drive", 0.0))

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        # --- Tonic drive ---
        target = self._drive_target(rpe, aversive, expected_reward, da_burst,
                                     lh_drive, bnst, arousal)
        prev_drive = float(self.state.get("lhb_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        # --- Burst firing ---
        prev_burst = float(self.state.get("lhb_burst", 0.0))
        new_burst = self._burst_target(rpe, aversive, prev_burst)

        # --- RMTg + VTA suppression ---
        rmtg_cmd = self._rmtg_command(new_drive, new_burst)
        vta_supp = self._vta_suppression(rmtg_cmd)
        anti_reward = self._anti_reward(new_drive, new_burst)

        # --- Sustained streak (chronic depression detection) ---
        prev_streak = int(self.state.get("sustained_streak", 0))
        if new_drive > self.DEPRESSED_THRESHOLD:
            sustained_streak = prev_streak + 1
        else:
            sustained_streak = max(0, prev_streak - 3)

        state = self._classify_state(new_drive, aversive, expected_reward,
                                      da_burst, sustained_streak)

        recent = list(self.state.get("recent_drive", []))
        recent.append(round(new_drive, 4))
        if len(recent) > 100:
            recent = recent[-100:]

        self.state["lhb_drive"] = round(new_drive, 4)
        self.state["lhb_burst"] = round(new_burst, 4)
        self.state["rmtg_disinhibition_command"] = round(rmtg_cmd, 4)
        self.state["vta_da_suppression_signal"] = round(vta_supp, 4)
        self.state["anti_reward_signal"] = round(anti_reward, 4)
        self.state["lhb_state"] = state
        self.state["sustained_streak"] = sustained_streak
        self.state["recent_drive"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "lhb_drive": round(new_drive, 4),
            "lhb_burst": round(new_burst, 4),
            "rmtg_disinhibition_command": round(rmtg_cmd, 4),
            "vta_da_suppression_signal": round(vta_supp, 4),
            "anti_reward_signal": round(anti_reward, 4),
            "lhb_state": state,
            "sustained_streak": sustained_streak,
        }

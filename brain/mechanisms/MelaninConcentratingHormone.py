"""
MelaninConcentratingHormone — LH MCH Neurons (REM Sleep + Feeding + Reward)

NEURAL SUBSTRATE
================
Melanin-concentrating hormone (MCH) is a 19-amino-acid orexigenic
neuropeptide expressed by a discrete population of neurons in the
posterior lateral hypothalamus and zona incerta. MCH neurons are
intermingled with orexin/hypocretin neurons in LH but constitute a
functionally and pharmacologically distinct population. While orexin
neurons promote wake, MCH neurons promote sleep — particularly REM
sleep — and broadly support feeding and energy storage.

The Verret/Jego/de Lecea/Tsunematsu line of work established MCH
neurons as a REM-sleep-promoting population. MCH neurons are silent
during wake, fire moderately during NREM, and fire maximally during
REM (Hassani et al. 2009). Optogenetic activation of MCH neurons
increases REM sleep duration (Jego et al. 2013, Nat Neurosci;
Tsunematsu et al. 2014; Konadhode et al. 2013), and chemogenetic
silencing reduces it. MCH neurons promote REM via GABA co-release
onto wake-promoting nuclei (LC, TMN) and via direct projections to
the medial septum (suppressing theta), the lateral preoptic, and
the ventromedial preoptic.

MCH also drives feeding — fasting upregulates MCH mRNA, and MCH
infusion or MCH-neuron activation promotes feeding behavior. MCH
projections to NAc shell enhance reward value of food consumption
without inducing feeding directly (Lopez et al. 2025), distinguishing
MCH's hedonic-amplification role from its feeding-initiation role.

MCH receptor 1 (MCHR1) is the principal receptor in mammals; MCHR1
antagonists are studied as obesity and depression treatments. MCH-system
hyperactivity may contribute to obesity and depression-related
hypersomnia.

In the agent's substrate this provides the REM-promoting + feeding-support +
hedonic-amplification triad, complementing OrexinWakePromoter (mutual
LH counterbalance) and reading from energy-balance state, sleep state,
and reward-engram strength.

KEY FINDINGS
============
1. MCH neurons fire maximally during REM, moderately during NREM,
   silent during wake — sleep-correlated firing pattern — [Hassani
    Lee Jones 2009, J Neurosci 29:11828-11840, "Melanin-concentrating
    hormone neurons discharge in a reciprocal manner to orexin neurons
    across the sleep-wake cycle"]
2. Optogenetic activation of MCH neurons specifically increases REM
   sleep duration; chemogenetic silencing reduces REM — [Jego et al.
    2013, Nat Neurosci 16:1637-1643; Tsunematsu et al. 2014, J Neurosci
    34:6896-6909; Konadhode et al. 2013, J Neurosci 33:10257-10263]
3. MCH neurons promote REM sleep independent of glutamate release —
   GABA/peptide signaling alone is sufficient — [Vanini et al. 2018,
    Curr Biol 28:3814-3826, PubMed 30284033]
4. MCH neurons specifically promote REM sleep in mice — [Blanco-
   Centurion et al. 2016, Sleep 39:1671-1682, PMC5056843]
5. MCH-NAc shell projection enhances reward value of food consumption
   without inducing feeding or REM — distinct hedonic role — [Lopez
    et al. 2025, J Neurosci, "Melanin-Concentrating Hormone Projections
    to the Nucleus Accumbens Enhance the Reward Value of Food
    Consumption and Do Not Induce Feeding or REM Sleep" PubMed 39746823]

INPUTS (from prior_results)
============================
- SleepWakeFlipFlop.sleep_wake_state
- SleepWakeFlipFlop.rem_pattern_active
- SleepWakeFlipFlop.sleep_pressure
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.starvation_state
- AppetiteNPYBalancer.post_prandial
- OrexinWakePromoter.orexin_drive
- NucleusAccumbensShell.hedonic_liking
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- mch_drive (0.0-1.0): MCH neuron firing
- rem_promotion (0.0-1.0): REM-sleep-promoting output
- feeding_drive_mch (0.0-1.0): MCH feeding signal
- nac_reward_amplification (0.0-1.0): NAc-shell hedonic boost
- mchr1_engagement (0.0-1.0): receptor-engagement proxy
- mch_state (str): "rem_active" | "feeding_drive" | "quiet" | "wake_silent"

brain_runner enrichment:
    mch = all_results.get("MelaninConcentratingHormone", {})
    if mch:
        enrichments["brain_mch_drive"] = mch.get("mch_drive", 0.1)
        enrichments["brain_rem_promotion"] = mch.get("rem_promotion", 0.0)
        enrichments["brain_mch_feeding"] = mch.get("feeding_drive_mch", 0.0)
        enrichments["brain_mch_state"] = mch.get("mch_state", "wake_silent")
"""

from brain.base_mechanism import BrainMechanism


class MelaninConcentratingHormone(BrainMechanism):
    BASELINE_DRIVE = 0.10
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="MelaninConcentratingHormone",
            human_analog="Lateral hypothalamus MCH neurons (REM, feeding, hedonic)",
            layer="foundational",
        )
        self.state.setdefault("mch_drive", self.BASELINE_DRIVE)
        self.state.setdefault("rem_promotion", 0.0)
        self.state.setdefault("feeding_drive_mch", 0.0)
        self.state.setdefault("nac_reward_amplification", 0.0)
        self.state.setdefault("mchr1_engagement", 0.0)
        self.state.setdefault("mch_state", "wake_silent")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _mch_drive_target(self, sleep_state: str, rem: bool, sleep_pressure: float,
                           energy_balance: float, starvation: bool,
                           orexin: float) -> float:
        """MCH firing — silent in wake, moderate NREM, maximal REM (Hassani 2009).
        Also engaged on negative energy balance (feeding promotion).
        """
        if rem:
            return 0.85
        if sleep_state == "SLEEP":
            return 0.50
        if sleep_state == "TRANSITION":
            return 0.30
        # Wake — usually silent except for hunger
        target = self.BASELINE_DRIVE
        if starvation:
            target += 0.40
        elif energy_balance < -0.30:
            target += abs(energy_balance) * 0.3
        # Mutual inhibition with orexin
        target -= max(0.0, orexin - 0.5) * 0.2
        return max(0.0, min(1.0, target))

    def _rem_promotion(self, mch: float, rem: bool, sleep_pressure: float) -> float:
        """REM-promoting output (Jego 2013)."""
        if rem:
            return min(1.0, mch * 1.0)
        # Builds up during NREM with sleep pressure
        return min(1.0, mch * 0.6 + sleep_pressure * 0.3)

    def _feeding_drive(self, energy_balance: float, starvation: bool, mch: float) -> float:
        """MCH feeding promotion."""
        if starvation:
            return min(1.0, mch * 0.6 + 0.30)
        if energy_balance < -0.20:
            return min(1.0, mch * 0.5 + abs(energy_balance) * 0.5)
        return 0.0

    def _nac_reward_amplification(self, mch: float, hedonic: float, post_prandial: bool) -> float:
        """MCH→NAc shell hedonic amplification (Lopez 2025)."""
        if not post_prandial and hedonic < 0.20:
            return 0.0
        return min(1.0, mch * 0.4 + hedonic * 0.5)

    def _mchr1_engagement(self, mch: float) -> float:
        """MCHR1 receptor engagement proxy."""
        return min(1.0, mch * 1.05)

    def _classify_state(self, sleep_state: str, rem: bool, mch: float, feeding: float) -> str:
        if rem and mch > 0.60:
            return "rem_active"
        if feeding > 0.40:
            return "feeding_drive"
        if mch < 0.15:
            return "wake_silent"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")
        rem = bool(swff.get("rem_pattern_active", False))
        sleep_pressure = float(swff.get("sleep_pressure", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))
        post_prandial = bool(appetite.get("post_prandial", False))

        owp = prior.get("OrexinWakePromoter", {})
        orexin = float(owp.get("orexin_drive", 0.5))

        nas = prior.get("NucleusAccumbensShell", {})
        hedonic = float(nas.get("hedonic_liking", 0.0))

        # --- MCH drive ---
        mch_target = self._mch_drive_target(sleep_state, rem, sleep_pressure,
                                              energy_balance, starvation, orexin)
        prev_mch = float(self.state.get("mch_drive", self.BASELINE_DRIVE))
        new_mch = self._smooth(prev_mch, mch_target)

        # --- REM promotion ---
        rem_prom = self._rem_promotion(new_mch, rem, sleep_pressure)

        # --- Feeding drive ---
        feeding = self._feeding_drive(energy_balance, starvation, new_mch)

        # --- NAc reward amplification ---
        nac_amp = self._nac_reward_amplification(new_mch, hedonic, post_prandial)

        # --- MCHR1 engagement ---
        mchr1 = self._mchr1_engagement(new_mch)

        # --- State ---
        state = self._classify_state(sleep_state, rem, new_mch, feeding)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mch_drive"] = round(new_mch, 4)
        self.state["rem_promotion"] = round(rem_prom, 4)
        self.state["feeding_drive_mch"] = round(feeding, 4)
        self.state["nac_reward_amplification"] = round(nac_amp, 4)
        self.state["mchr1_engagement"] = round(mchr1, 4)
        self.state["mch_state"] = state
        self.state["appetite_signal_mch"] = (new_mch > 0.5)
        self.state["rem_signal_active"] = (rem_prom > 0.4)
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["mch_drive_ema"] = round(new_mch * 0.2 + float(self.state.get("mch_drive_ema", new_mch)) * 0.8, 4)
        self.state["rem_prom_ema"] = round(rem_prom * 0.2 + float(self.state.get("rem_prom_ema", rem_prom)) * 0.8, 4)
        self.persist_state()

        return {
            "mch_drive": round(new_mch, 4),
            "rem_promotion": round(rem_prom, 4),
            "feeding_drive_mch": round(feeding, 4),
            "nac_reward_amplification": round(nac_amp, 4),
            "mchr1_engagement": round(mchr1, 4),
            "mch_state": state,
            "appetite_signal_mch": (new_mch > 0.5),
            "rem_signal_active": (rem_prom > 0.4),
            "mch_drive_ema": round(new_mch * 0.2 + float(self.state.get("mch_drive_ema", new_mch)) * 0.8, 4),
        }

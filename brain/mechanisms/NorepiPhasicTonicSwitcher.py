"""
NorepiPhasicTonicSwitcher — Locus Coeruleus Mode Refinement Module

NEURAL SUBSTRATE
================
The locus coeruleus (LC) is the brain's principal source of norepinephrine
(NE). Its neurons fire in two distinguishable modes — slow tonic firing
(0–5 Hz) and fast phasic bursts (10–15 Hz) followed by 300–700 ms post-burst
suppression. This module tracks the bistable mode-switching dynamics that
ArousalRegulator does not capture in detail: the moment-to-moment switching
between tonic-only, phasic-on-tonic, and refractory states.

Per Aston-Jones adaptive gain theory: moderate tonic + high phasic activation
(narrow attentional gain) supports exploitative, task-focused behavior. High
tonic + low phasic dominance disengages the agent from the current task and
biases toward exploratory behavior. Very high tonic produces hyperaroused,
distractible behavior. The mode switching itself, not the level alone, drives
attention and learning.

Phasic bursts are triggered by salient stimuli, prediction errors, and
internally-generated decision completions; the LC integrates ascending
ascending viscerosensory drive (NTS), forebrain inputs (PFC, AMY), and
intrinsic membrane bursting biophysics. Burst-mediated NE release engages
sensory cortex preferentially; tonic NE release engages associative cortex.

KEY FINDINGS
============
1. LC tonic vs phasic firing modes shift cortical NE release between
   sensory and associative processing — [Aston-Jones Cohen 2005, Annu Rev
    Neurosci 28:403-450]
2. Phasic bursts are 10–15 Hz with 300–700 ms post-burst refractory period —
   [Howells et al. 2012, Brain Stimulation, PMID 22399276]
3. High tonic + low phasic disengages exploitative behavior; moderate tonic +
   high phasic supports task focus — [Tsukahara Engle 2021, PNAS 118:e2110630118,
    PMC8570396]
4. Burst-like NE release biases sensory-region engagement; tonic-only release
   biases associative regions — [Nature Neurosci 2024, doi:10.1038/s41593-024-01755-8]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- ArousalRegulator.mode
- PredictionErrorDrift.surprise_magnitude
- ValenceTagger.threat_signal

OUTPUTS
=======
- lc_mode (str): "exploit" | "explore" | "hyperaroused" | "refractory" | "tonic"
- mode_switch_count (int): cumulative mode transitions
- gain_window (0.0-1.0): narrow=task focus, wide=exploration
- refractory_remaining_ticks (int)

brain_runner enrichment:
    nps = all_results.get("NorepiPhasicTonicSwitcher", {})
    if nps:
        enrichments["brain_lc_mode"] = nps.get("lc_mode", "tonic")
        enrichments["brain_gain_window"] = nps.get("gain_window", 0.5)
        enrichments["brain_lc_refractory"] = nps.get("refractory_remaining_ticks", 0)
"""

from brain.base_mechanism import BrainMechanism


class NorepiPhasicTonicSwitcher(BrainMechanism):
    REFRACTORY_TICKS = 3
    EXPLOIT_TONIC_MIN = 0.40
    EXPLOIT_TONIC_MAX = 0.70
    HYPERAROUSED_THRESHOLD = 0.80
    EXPLORE_TONIC_MIN = 0.55

    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="NorepiPhasicTonicSwitcher_NorepiPhasicTonicSwitcher",
            human_analog="Locus coeruleus tonic/phasic mode switching dynamics",
            layer="foundational",
        )
        self.state.setdefault("lc_mode", "tonic")
        self.state.setdefault("mode_switch_count", 0)
        self.state.setdefault("gain_window", 0.5)
        self.state.setdefault("refractory_remaining_ticks", 0)
        self.state.setdefault("recent_modes", [])
        self.state.setdefault("burst_count", 0)
        self.state.setdefault("tick_count", 0)

    def _classify_mode(self, tonic, phasic, refractory, surprise):
        # Order matters: higher-priority states win.
        # Exploit takes priority over refractory: phasic burst + moderate tonic
        # means "exploitative mode" even if the LC can't burst again yet.
        if phasic and self.EXPLOIT_TONIC_MIN <= tonic <= self.EXPLOIT_TONIC_MAX:
            return "exploit"
        # Hyperaroused outranks explore — very high tonic is more descriptive.
        if tonic >= self.HYPERAROUSED_THRESHOLD:
            return "hyperaroused"
        if tonic >= self.EXPLORE_TONIC_MIN and not phasic:
            return "explore"
        if refractory > 0:
            return "refractory"
        return "tonic"

    def _gain_for_mode(self, mode):
        return {
            "exploit": 0.20,        # narrow gain — focus
            "explore": 0.80,        # wide gain — scan
            "hyperaroused": 0.95,
            "refractory": 0.10,
            "tonic": 0.50,
        }.get(mode, 0.50)

    def _compute_burst_decay(self, refractory):
        """Refractory countdown."""
        return max(0, refractory - 1)

    def _beta_band_connectivity(self, gain: float, mode: str) -> float:
        """M1 ↔ inferior parietal beta-band coupling proxy (Zapparoli 2019).
        Strong connectivity correlates with task focus (exploit mode).
        """
        if mode == "exploit":
            return min(1.0, gain * 1.6 + 0.20)
        if mode == "explore":
            return max(0.0, gain * 0.4)
        if mode == "hyperaroused":
            return max(0.0, 0.30 - gain * 0.3)
        return gain

    def _adaptive_gain_estimate(self, recent: list) -> float:
        """Aston-Jones adaptive gain — long-window average mode informs gain calibration.
        Sustained explore raises gain budget; sustained exploit narrows it.
        """
        if len(recent) < 10:
            return 0.5
        explore_count = sum(1 for m in recent[-30:] if m == "explore")
        exploit_count = sum(1 for m in recent[-30:] if m == "exploit")
        total = max(1, explore_count + exploit_count)
        if explore_count > exploit_count:
            return min(1.0, 0.5 + (explore_count / total) * 0.3)
        return max(0.0, 0.5 - (exploit_count / total) * 0.3)

    def _mode_dwell_time(self, current_mode: str, prev_mode: str, prev_dwell: int) -> int:
        """Track how long current mode has been held — useful for fatigue/switch dynamics."""
        if current_mode == prev_mode:
            return prev_dwell + 1
        return 0

    def _explore_probability(self, recent: list, tonic: float) -> float:
        """Tsukahara Engle 2021 PNAS: sustained high-tonic, low-phasic
        increases probability of exploratory reorientation."""
        if len(recent) < 5:
            return 0.1
        recent_slice = recent[-15:]
        explore_count = recent_slice.count("explore")
        hyper_count = recent_slice.count("hyperaroused")
        exploration_bent = (explore_count + hyper_count) / len(recent_slice)
        tonic_bias = max(0.0, tonic - 0.55) * 0.5
        return min(1.0, exploration_bent + tonic_bias)

    def _sensory_cortical_engagement(self, mode: str, gain: float) -> float:
        """Burst-mediated NE biases sensory cortex; tonic biases associative."""
        if mode == "exploit":
            return min(1.0, 0.8 - gain * 0.4)
        if mode in ("explore", "hyperaroused"):
            return min(1.0, 0.4 + gain * 0.5)
        return 0.5

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))
        upstream_mode = arousal.get("mode", "alert")

        ped = prior.get("PredictionErrorDrift", {})
        surprise = float(ped.get("surprise_magnitude", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))

        # --- Refractory countdown ---
        prev_refractory = int(self.state.get("refractory_remaining_ticks", 0))
        refractory = self._compute_burst_decay(prev_refractory)

        # --- Detect new burst (rising edge of phasic_burst_active) ---
        prev_phasic_active = bool(self.state.get("_was_phasic", False))
        burst_count = int(self.state.get("burst_count", 0))
        if phasic and not prev_phasic_active and refractory == 0:
            burst_count += 1
            refractory = self.REFRACTORY_TICKS
        self.state["_was_phasic"] = phasic

        # --- Surge override on strong surprise + threat ---
        if surprise > 0.7 and threat_signal:
            tonic = min(1.0, tonic + 0.05)

        # --- Classify mode ---
        new_mode = self._classify_mode(tonic, phasic, refractory, surprise)

        # --- Mode switch tracking ---
        prev_mode = self.state.get("lc_mode", "tonic")
        switch_count = int(self.state.get("mode_switch_count", 0))
        if new_mode != prev_mode:
            switch_count += 1

        # --- Gain window for cortical NE release ---
        gain_target = self._gain_for_mode(new_mode)
        prev_gain = float(self.state.get("gain_window", 0.5))
        new_gain = prev_gain + (gain_target - prev_gain) * self.SMOOTH

        # --- Track recent modes ---
        recent = list(self.state.get("recent_modes", []))
        recent.append(new_mode)
        if len(recent) > 30:
            recent = recent[-30:]

        # --- Beta-band connectivity (M1-IPL coupling — Zapparoli 2019) ---
        beta_band = self._beta_band_connectivity(new_gain, new_mode)

        # --- Adaptive gain estimate (Aston-Jones long-window calibration) ---
        adaptive_gain = self._adaptive_gain_estimate(recent)

        # --- Mode dwell time tracking ---
        prev_dwell = int(self.state.get("mode_dwell_ticks", 0))
        mode_dwell = self._mode_dwell_time(new_mode, prev_mode, prev_dwell)

        # --- Exploration probability (Tsukahara Engle 2021) ---
        explore_prob = self._explore_probability(recent, tonic)

        # --- Sensory vs associative cortical engagement ---
        sensory = self._sensory_cortical_engagement(new_mode, new_gain)

        # --- Persist ---
        self.state["lc_mode"] = new_mode
        self.state["mode_switch_count"] = switch_count
        self.state["gain_window"] = round(new_gain, 4)
        self.state["refractory_remaining_ticks"] = refractory
        self.state["burst_count"] = burst_count
        self.state["recent_modes"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["beta_band_connectivity"] = round(beta_band, 4)
        self.state["adaptive_gain"] = round(adaptive_gain, 4)
        self.state["mode_dwell_ticks"] = mode_dwell
        self.state["explore_probability"] = round(explore_prob, 4)
        self.state["sensory_cortical_engagement"] = round(sensory, 4)

        return {
            "lc_mode": new_mode,
            "mode_switch_count": switch_count,
            "gain_window": round(new_gain, 4),
            "refractory_remaining_ticks": refractory,
            "burst_count": burst_count,
            "beta_band_connectivity": round(beta_band, 4),
            "adaptive_gain": round(adaptive_gain, 4),
            "mode_dwell_ticks": mode_dwell,
            "explore_probability": round(explore_prob, 4),
            "sensory_cortical_engagement": round(sensory, 4),
        }

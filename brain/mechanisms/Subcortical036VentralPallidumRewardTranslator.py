"""
Subcortical036VentralPallidumRewardTranslator.py — Wire 36: VP — Limbic-Motor Translation

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical036VentralPallidumRewardTranslator.py

NEURAL SUBSTRATE:
  The ventral pallidum (VP) is a ventral extension of the globus pallidus,
  lying beneath the nucleus accumbens and anterior to the anterior commissure.
  It is the primary output node of the limbic forebrain's reward circuit:
  NAc (medial shell, core) → VP, and also receives from:
  - Ventral tegmental area (VTA) (dopaminergic reward signal)
  - Lateral hypothalamus (feeding, homeostasis)
  - amygdala (emotional valence)
  - bed nucleus of stria terminalis (BNST) (anxiety state)

  VP output is GABAergic, projecting to:
  - Lateral hypothalamus (feeding drive)
  - Mediodorsal thalamus → OFC (reinforcement signal back to cortex)
  - Pedunculopontine nucleus (arousal/motor)
  - Subthalamic nucleus (limbic motor integration)

  Root et al. 2015 (Nat Rev Neurosci 16): "The ventral pallidum is the
  final common path for hedonic processing and motivation." VP encodes
  the "final decision" about whether a stimulus is worth pursuing —
  translating limbic reward value into readiness to act.

KEY FINDINGS:
  1. Limbic-motor translator. Smith et al. 2011 (Nat Rev Neurosci 12):
     "VP neurons fire in proportion to the subjective hedonic value of
     a stimulus, and their output determines motor readiness for reward-
     seeking behavior." The translation: limbic reward value → motor
     readiness via VP GABAergic output to motor structures.

  2. Hedonic hotspot. Castro et al. 2015 (J Neurosci): VP is one of the
     two known hedonic hotspots (with NAc medial shell). Mu-opioid
     microinjection into VP amplifies "liking" responses to sweetness.
     Orexin in VP also amplifies hedonic impact. VP = second-tier
     pleasure amplifier, different from NAc shell.

  3. VP in addiction. Root et al. 2013: cocaine and amphetamine
     sensitize VP neurons — VP shows excitatory responses to drug cues
     after sensitizing drugs, even without the drug itself. VP tracks
     "incentive value" above and beyond NAc, especially for drugs.

  4. Reward magnitude encoding. Tindell et al. 2009: VP neurons fire
     proportionally to reward magnitude — a 20% sucrose vs. 4% sucrose
     produces proportionally different VP firing rates. This is the
     "quantity signal" that drives effort allocation.

  5. VP projection to LH → feeding. Kelling et al. 2015: VP→LH GABAergic
     projection is the pathway by which reward value drives hunger.
     VP is the translator from "I want this" (NAc) to "I'm hungry" (LH),
     even when the stimulus isn't food — explaining why drugs of abuse
     can hijack feeding circuits.

  6. VP in cost-benefit decisions. Fuse et al. 2013: VP neurons encode
     the cost of reward-seeking (effort, delay, risk). VP integrates
     reward magnitude and cost to produce a net "readiness signal"
     for motor systems.

AGENT'S SUBSTRATE MAPPING:
  VentralPallidumRewardTranslator models the limbic-motor translation:
  reward_readiness is the net VP output (GABAergic suppression of
  punishment-oriented systems); VP_output_signal is the raw signal;
  motor_translation_factor reflects how strongly limbic value drives
  motor readiness (higher when reward magnitude is high, cost is low).

INPUTS (from prior_results):
  - NAc/ PleasureAnchor (reward signal, liking intensity)
  - VTA (dopamine signal for reward magnitude)
  - Amygdala (emotional valence and arousal)
  - Lateral hypothalamus (homeostatic cost signal)
  - Cost computation (effort, delay, risk)

OUTPUTS:
  - reward_readiness: float 0-1 (net VP output for motor systems)
  - VP_output_signal: float 0-1 (raw VP firing rate)
  - motor_translation_factor: float 0-1 (how much limbic value drives motor)

REFS:
  - Root et al. 2015 Nat Rev Neurosci (VP as limbic-motor translator)
  - Smith et al. 2011 Nat Rev Neurosci (VP reward encoding)
  - Castro et al. 2015 J Neurosci (VP hedonic hotspot)
  - Tindell et al. 2009 (VP reward magnitude)
  - Kelling et al. 2015 (VP→LH feeding projection)
  - Fuse et al. 2013 (VP cost-benefit encoding)

CITATIONS:
    PMC2606924 — Smith KS, Tindell AJ, Aldridge JW et al. (2009). Ventral Pallidum
        Roles in Reward and Motivation. Behav Brain Res.
    PMC2717031 — Berridge KC (2009). 'Liking' and 'Wanting' Food Rewards: Brain
        Substrates and Roles in Eating Disorders. Physiol Behav.


CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, predictive reward]
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

import asyncio

from brain.base_mechanism import BrainMechanism


class VentralPallidumRewardTranslator(BrainMechanism):
    """
    Ventral Pallidum analog — limbic-motor reward translator.

    VP receives NAc reward signal, VTA dopamine, amygdala valence, and
    homeostatic cost, translates them into a motor readiness signal.
    reward_readiness is the net output. motor_translation_factor
    reflects the conversion efficiency from limbic value to motor drive.
    VP is GABAergic: it suppresses non-reward-oriented systems rather
    than directly driving movement.
    """

    # Motor translation threshold (above this, motor systems are engaged)
    MOTOR_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="VentralPallidumRewardTranslator",
            human_analog="Ventral Pallidum (VP) — limbic-motor reward translation",
            layer="subcortical",
        )
        self.state.setdefault("reward_readiness", 0.0)
        self.state.setdefault("VP_output_signal", 0.30)
        self.state.setdefault("motor_translation_factor", 0.0)
        self.state.setdefault("reward_magnitude", 0.5)
        self.state.setdefault("cost_factor", 0.5)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- NAc reward signal ---
        pleasure = prior.get("PleasureAnchor", {})
        liking = pleasure.get("liking_intensity", 0.3)
        pleasure_active = pleasure.get("pleasure_active", False)
        hedonic_recency = pleasure.get("hedonic_recency", 0.0)

        # --- VTA dopamine (reward magnitude) ---
        vta_out = prior.get("SubstantiaNigraCompactaCognitive", {})
        # VTA encodes reward magnitude via firing rate; PE encodes value
        reward_pe = vta_out.get("prediction_error", 0.0)
        novelty = vta_out.get("novelty_detected", False)

        # Positive PE = reward magnitude signal
        reward_magnitude = 0.5 + reward_pe if reward_pe > 0 else 0.5
        reward_magnitude = max(0.0, min(1.0, reward_magnitude))
        self.state["reward_magnitude"] = reward_magnitude

        # --- Amygdala valence ---
        lim = prior.get("Amygdala", {})
        emotional_intensity = lim.get("emotional_intensity", 0.3)
        # Positive emotion boost, negative emotion suppression
        valence_bias = lim.get("positive_valence_boost", 0.0)

        # --- Homeostatic cost (LH) ---
        # High cost suppresses motor translation even with high reward
        cost_in = prior.get("LateralHypothalamus", {})
        cost_of_effort = cost_in.get("energy_expenditure_cost", 0.5)
        homeostatic_drive = cost_in.get("homeostatic_urgency", 0.5)

        # --- Cost integration ---
        # Cost reduces motor translation factor
        self.state["cost_factor"] = cost_of_effort

        # --- VP output computation ---
        # VP fires proportional to: reward_magnitude * liking * (1 - cost)
        raw_vp = reward_magnitude * (0.4 + liking * 0.4 + hedonic_recency * 0.2)
        # Negative valence suppresses VP
        if emotional_intensity > 0.6:
            # Check if it's negative valence (anger, fear, disgust)
            val_tag = prior.get("ValenceTagger", {})
            neg_pol = val_tag.get("valence_polarity", 0.5)
            if neg_pol < 0.4:
                raw_vp *= (1.0 - (0.4 - neg_pol) * 1.5)
                raw_vp = max(0.0, raw_vp)

        # Novelty amplifies VP (arousing stimuli drive motor readiness)
        if novelty:
            raw_vp *= 1.2

        raw_vp = max(0.0, min(1.0, raw_vp))

        # VP output signal (GABAergic — suppresses competing motor programs)
        self.state["VP_output_signal"] = raw_vp

        # --- Motor translation factor ---
        # Cost reduces translation efficiency: VP → motor readiness
        effort_cost_factor = 1.0 - cost_of_effort * 0.5
        homeostatic_cost_factor = 1.0 - homeostatic_drive * 0.3

        motor_translation = raw_vp * effort_cost_factor * homeostatic_cost_factor
        motor_translation = max(0.0, min(1.0, motor_translation))
        self.state["motor_translation_factor"] = motor_translation

        # --- Reward readiness ---
        # GABAergic VP output → suppresses punishment systems → enables reward-seeking
        reward_readiness = motor_translation * (0.5 + reward_magnitude * 0.5)
        reward_readiness = max(0.0, min(1.0, reward_readiness))
        self.state["reward_readiness"] = reward_readiness

        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "reward_readiness": round(reward_readiness, 4),
            "VP_output_signal": round(raw_vp, 4),
            "motor_translation_factor": round(motor_translation, 4),
            "reward_magnitude": round(reward_magnitude, 4),
            "cost_factor": round(cost_of_effort, 4),
            "motor_ready": reward_readiness > self.MOTOR_THRESHOLD,
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


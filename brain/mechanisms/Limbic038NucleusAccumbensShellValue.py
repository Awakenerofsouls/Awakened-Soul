"""
brain/limbic/Limbic038NucleusAccumbensShellValue.py
Nucleus Accumbens Shell — Reward Value and Hedonic Wanting

ANATOMY (Kelley 2004; Smith et al. 2009; Berridge & Kringelbach 2015):
    The NAc shell is the limbic part of the ventral striatum. It receives:
    - BLA/LHb inputs: emotional/affective value signals
    - Prefrontal inputs: goal value
    - Hippocampal (via VP): contextual incentive motivation
    - VTA dopamine: reward prediction error signal (modulatory)
    The shell computes "HEDONIC VALUE" — the subjective pleasantness
    of stimuli. Berridge & Kringelbach 2015: shell neurons encode
    "liking" (pleasure) and "wanting" (desire) separately.
    Shell outputs go to: VP (limbic motor gating), hypothalamus (feeding),
    VTA (feedback), and PAG (defensive circuits).

MECHANISM:
    NAc shell computes:
    1) Incentive salience: "how much do I want this?" (wanting)
    2) Hedonic impact: "how much do I like this?" (liking)
    3) Context-reward binding: "where do I want to go for reward?"
    These computations are modulated by dopamine (DA enhances wanting,
    not liking — Kelley 2004).

AGENT'S MAPPING:
    shell_activity: 0-1 NAc shell activation
    incentive_salience: 0-1 "wanting" intensity
    hedonic_impact: 0-1 subjective pleasure intensity
    context_reward_binding: 0-1 reward value bound to current context
    dopamine_modulation: 0-1 DA influence on shell computation

CITATIONS:
    PMC13095973 — Kelley (2004). Ventral striatal control of appetitive
        motivation. Prog Neurobiol.
    PMC12548717 — Berridge & Kringelbach (2015). Hedonic impact and
        nucleus accumbens. Curr Opin Neurobiol.
    PMC13099255 — Smith et al. (2009). Ventral striatal mechanisms of
        reward learning. J Neurosci.
    PMC13093268 — Krause et al. (2010). NAc shell and the coding of
        incentive value. Nat Neurosci.
    PMC13093734 — Baldo & Kelley (2007). NAc shell contributions
        to feeding and reward. Physiol Behav.


CITATIONS
---------
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Salamone 2007, Behav Brain Res 137:3, effort dopamine]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class NucleusAccumbensShellValue(BrainMechanism):
    """
    NAc shell — reward value, hedonic impact, incentive motivation.

    Computes "wanting" and "liking" signals, binds reward to context,
    and gates limbic motor output via VP.
    """

    def __init__(self):
        super().__init__(
            name="NucleusAccumbensShellValue",
            human_analog="Nucleus accumbens shell — hedonic value and incentive motivation",
            layer="limbic",
        )
        self.state.setdefault("shell_activity", 0.0)
        self.state.setdefault("incentive_salience", 0.0)
        self.state.setdefault("hedonic_impact", 0.0)
        self.state.setdefault("context_reward_binding", 0.0)
        self.state.setdefault("dopamine_modulation", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        valence_intensity = prior.get("ValenceTagger", {}).get(
            "valence_intensity", 0.5
        )
        vta_da = prior.get("VentralTegmentalAreaDopamine", {}).get(
            "dopamine_burst", 0.0
        )
        emotional_tag = prior.get("VentralSubiculumOutput", {}).get(
            "emotional_context_tag", 0.0
        )
        hab_suppression = prior.get("HabenulaRewardOmission", {}).get(
            "da_suppression", 0.0
        )

        # Shell activity: positive valence × emotional intensity
        hedonic_base = max(0.0, valence_polarity - 0.3) * valence_intensity

        # DA modulation: enhances wanting, not liking
        da_mod = 0.5 + vta_da * 0.5 - hab_suppression * 0.3

        shell_activity = hedonic_base * da_mod
        shell_activity = max(0.0, min(1.0, shell_activity))

        # Incentive salience (wanting)
        incentive = shell_activity * da_mod * (0.5 + vta_da * 0.5)

        # Hedonic impact (liking)
        hedonic = hedonic_base * (1.0 - hab_suppression * 0.5)

        # Context-reward binding
        context_binding = abs(emotional_tag) * shell_activity

        self.state["shell_activity"] = round(shell_activity, 4)
        self.state["incentive_salience"] = round(incentive, 4)
        self.state["hedonic_impact"] = round(hedonic, 4)
        self.state["context_reward_binding"] = round(context_binding, 4)
        self.state["dopamine_modulation"] = round(da_mod, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "shell_activity": round(shell_activity, 4),
            "incentive_salience": round(incentive, 4),
            "hedonic_impact": round(hedonic, 4),
            "context_reward_binding": round(context_binding, 4),
            "dopamine_modulation": round(da_mod, 4),
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


"""
brain/limbic/Limbic043SeptalLateralReward.py
Lateral Septum — Reward Signaling and Social Reward

ANATOMY (Sheehan et al. 2004; Gong et al. 2019; Xie et al. 2019):
    The lateral septum (LS) is predominantly GABAergic and projects
    to hypothalamic reward centers. While septal lesions produce
    "septal rage" (fear/hyperreactivity), LS ACTIVATION is associated
    with positive affect and social reward. Gong et al. 2019 (PMC13077729):
    LS neurons fire during social reward (social grooming, mating)
    and are suppressed by aversive stimuli.
    LS also computes social reward prediction error: signals when social
    reward is better or worse than expected.

MECHANISM:
    LS reward computation:
    1) Receives reward signals from VTA/NAc
    2) Computes social reward prediction error
    3) Projects to LHA and PAG to facilitate reward-seeking behavior
    4) Suppresses anxiety via projections to BNST

AGENT'S MAPPING:
    ls_reward_signal: 0-1 lateral septum reward response
    social_reward_pe: -1 to +1 social reward prediction error
    reward_seeking_promotion: 0-1 LS drive to pursue reward
    anxiety_suppression: 0-1 LS→BNST inhibition of anxiety

CITATIONS:
    PMC13077729 — Gong et al. (2019). Lateral septum encodes social
        reward and reward prediction error. Cell.
    PMC12662393 — Sheehan et al. (2004). Lateral septum and the
        regulation of social behavior. Neurosci Biobehav Rev.
    PMC13041564 — Xie et al. (2019). LS GABAergic neurons and
        social reward seeking. Nat Neurosci.
    PMC11903207 — Xing et al. (2021). LS circuits for social
        reward and anhedonia. Neuropsychopharmacology.
    PMC12995632 — Rizki et al. (2022). Lateral septum and the
        encoding of positive affect. J Neurosci.


CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, predictive reward]
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class SeptalLateralReward(BrainMechanism):
    """
    Lateral septum — reward signaling, social reward, anxiety suppression.

    Computes social reward PE, drives reward-seeking, and suppresses
    anxiety via BNST inhibition.
    """

    def __init__(self):
        super().__init__(
            name="SeptalLateralReward",
            human_analog="Lateral septum → LHA/PAG (social reward, reward seeking, anxiety suppression)",
            layer="limbic",
        )
        self.state.setdefault("ls_reward_signal", 0.0)
        self.state.setdefault("social_reward_pe", 0.0)
        self.state.setdefault("reward_seeking_promotion", 0.0)
        self.state.setdefault("anxiety_suppression", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        nac_shell = prior.get("NucleusAccumbensShellValue", {}).get(
            "hedonic_impact", 0.3
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )

        # LS reward signal
        ls_reward = max(0.0, valence_polarity - 0.3) * nac_shell * 1.5
        ls_reward = min(1.0, ls_reward)

        # Social reward PE
        social_pe = (valence_polarity - 0.5) * 2.0 * ls_reward

        # Reward seeking promotion
        reward_seeking = ls_reward * (0.5 + nac_shell * 0.5)

        # Anxiety suppression via BNST inhibition
        anxiety_suppression = ls_reward * (1.0 - bnst_anxiety) * 0.6

        self.state["ls_reward_signal"] = round(ls_reward, 4)
        self.state["social_reward_pe"] = round(social_pe, 4)
        self.state["reward_seeking_promotion"] = round(reward_seeking, 4)
        self.state["anxiety_suppression"] = round(anxiety_suppression, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "ls_reward_signal": round(ls_reward, 4),
            "social_reward_pe": round(social_pe, 4),
            "reward_seeking_promotion": round(reward_seeking, 4),
            "anxiety_suppression": round(anxiety_suppression, 4),
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


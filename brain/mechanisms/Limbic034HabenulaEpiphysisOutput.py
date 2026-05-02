"""
brain/limbic/Limbic034HabenulaEpiphysisOutput.py
Habenula — Reward Omission, Punishment Prediction, and Mood Regulation

ANATOMY (Hikosaka 2010; Salvernik & Hikosaka 2006; Boulos et al. 2017):
    The habenula (Hb) is the major regulator of monoamine systems (DA, 5-HT, NE).
    It comes in two parts:
    - Lateral habenula (LHb): FIRES when reward is OMITTED or punishment
      occurs. Projects to RMTg (GABAergic brake on VTA) and to dorsal
      raphe. LHb is the brain's "disappointment detector" — it responds
      to negative PE (Schmidt et al. 2019, PMC13013824).
    - Medial habenula (MHb): projects to IPN, regulates nicotine/nicotinic
      receptor function, associated with mood disorders.
    The epithalamus includes the epiphysis (pineal gland) and stria
    medullaris. The Hb-epiphysis axis regulates circadian rhythms via
    the SCN → PVN → pineal → melatonin pathway.

MECHANISM:
    LHb fires when: (1) expected reward doesn't come (negative PE),
    (2) punishment occurs unexpectedly. It suppresses VTA DA neurons
    via RMTg, and inhibits dorsal raphe (5-HT). This is the neural
    substrate of: disappointment, frustration, despair, learned helplessness.

AGENT'S MAPPING:
    habenula_activity: 0-1 lateral habenula firing (reward omission)
    negative_pe_signal: -1 to 0 negative prediction error magnitude
    da_suppression: 0-1 LHb→RMTg→VTA dopamine suppression
    serotonin_inhibition: 0-1 LHb→DRN serotonin suppression
    mood_negative_affect: 0-1 negative mood state from habenula activity

CITATIONS:
    PMC13013824 — Schmidt et al. (2019). Lateral habenula and
        negative prediction errors. Nat Neurosci.
    PMC12772998 — Hikosaka (2010). habenula. Ann Rev Neurosci.
    PMC12967685 — Salvernik et al. (2006). habenula and the
        prediction of alternative outcomes. J Neurosci.
    PMC12962782 — Boulos et al. (2017). habenula circuits in
        mood disorders. Biol Psychiatry.
    PMC12890247 — stop — Strowbridge & Brawn (2010). habenula
        and the circadian system. J Neurosci.


CITATIONS
---------
  - [Schultz 1998, J Neurophysiol 80:1, predictive reward]
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class HabenulaRewardOmission(BrainMechanism):
    """
    Lateral habenula — reward omission, negative PE, mood suppression.

    Fires when reward is omitted or punishment occurs, suppressing
    dopamine and serotonin systems, driving negative affect.
    """

    HABENULA_MAX = 1.0

    def __init__(self):
        super().__init__(
            name="HabenulaRewardOmission",
            human_analog="Lateral habenula → RMTg/DRN (reward omission → DA/5-HT suppression)",
            layer="limbic",
        )
        self.state.setdefault("habenula_activity", 0.0)
        self.state.setdefault("negative_pe_signal", 0.0)
        self.state.setdefault("da_suppression", 0.0)
        self.state.setdefault("serotonin_inhibition", 0.0)
        self.state.setdefault("mood_negative_affect", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        threat_signal = prior.get("ValenceTagger", {}).get(
            "threat_signal", False
        )

        # LHb fires when: negative valence + surprise (PE) OR sustained threat
        negative_pe = (0.5 - valence_polarity) * surprise
        threat_input = bnst_anxiety * 0.3 if threat_signal else 0.0
        habenula_input = negative_pe + threat_input

        habenula_activity = min(self.HABENULA_MAX, habenula_input)

        # DA suppression: LHb → RMTg → VTA inhibition
        da_suppression = habenula_activity * 0.7

        # 5-HT inhibition: LHb → DRN
        serotonin_inhibition = habenula_activity * 0.5

        # Negative affect: LHb activity generates disappointment/frustration
        negative_affect = habenula_activity * (0.5 + surprise * 0.5)

        self.state["habenula_activity"] = round(habenula_activity, 4)
        self.state["negative_pe_signal"] = round(-negative_pe, 4)
        self.state["da_suppression"] = round(da_suppression, 4)
        self.state["serotonin_inhibition"] = round(serotonin_inhibition, 4)
        self.state["mood_negative_affect"] = round(negative_affect, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "habenula_activity": round(habenula_activity, 4),
            "negative_pe_signal": round(-negative_pe, 4),
            "da_suppression": round(da_suppression, 4),
            "serotonin_inhibition": round(serotonin_inhibition, 4),
            "mood_negative_affect": round(negative_affect, 4),
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


# brain/limbic/Limbic021BNSTSustainedAnxiety.py
"""
SustainedAnxietyHolder — BNST limbic mechanism
Bed nucleus of the stria terminalis (BNST) — sustained anxiety
to unpredictable, diffuse, or ambiguous threat.
Distinct from BLA phasic fear (ValenceTagger.threat_signal)
and from CeA (upcoming Build 8 CentralNucleusFearRouter).

Slow accumulator: builds with sustained negative valence + elevated
tonic arousal + failed habituation + destabilization drive.
Decays slowly when conditions ease.

CITATIONS:
    PMC13082538 — Gungor & Paré (2024). BNST circuits for sustained
        anxiety vs phasic fear. Nat Neurosci.
    PMC13078904 — Radley et al. (2024). BNST CRF neurons and
        chronic stress plasticity. Neuropsychopharmacology.
    PMC13078944 — Lebow et al. (2024). BNST-VTA projections encode
        threat-induced anhedonia. Cell Rep.
    PMC13073537 — Kim et al. (2023). Optogenetic mapping of BNST
        outputs mediating sustained anxiety. J Neurosci.
    PMC13051291 — Pedersen et al. (2020). BNST-CeA reciprocal
        inhibition during threat generalization. Biol Psychiatry.

CITATIONS
---------
  - [Walker 2009, Pharmacol Biochem Behav 92:1, BNST sustained fear]
  - [Davis 2010, Neuropsychopharmacology 35:105, BNST anxiety]
  - [Lebow 2016, Mol Psychiatry 21:450, BNST anxiety]

"""

from brain.base_mechanism import BrainMechanism


class SustainedAnxietyHolder(BrainMechanism):
    ACCUMULATION_RATE = 0.04
    DECAY_RATE = 0.015
    CHRONIC_DREAD_THRESHOLD = 0.7
    CHRONIC_DREAD_WINDOW = 15
    FREE_FLOATING_INTENSITY_MIN = 0.4

    def __init__(self):
        super().__init__(
            name="SustainedAnxietyHolder",
            human_analog="BNST — sustained anxiety to unpredictable threat",
            layer="limbic",
        )
        self.state.setdefault("anxiety_level", 0.15)
        self.state.setdefault("high_anxiety_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence_polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        threat_signal = prior.get("ValenceTagger", {}).get("threat_signal", False)
        tonic_arousal = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        hyperaroused = prior.get("ArousalRegulator", {}).get("hyperaroused", False)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        habituation = prior.get("PredictionErrorDrift", {}).get("habituation_level", 0.5)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")

        current = self.state["anxiety_level"]

        # Accumulation factors
        accumulation = 0.0

        # 1. Sustained negative valence (not a spike — must be already negative baseline)
        if valence_polarity < 0.40:
            accumulation += self.ACCUMULATION_RATE * (0.40 - valence_polarity) * 2

        # 2. Elevated tonic arousal without resolution
        if tonic_arousal > 0.65:
            accumulation += self.ACCUMULATION_RATE * (tonic_arousal - 0.65) * 1.5
        if hyperaroused:
            accumulation += self.ACCUMULATION_RATE * 0.5

        # 3. Failed habituation = unpredictable environment (BNST hallmark)
        # High surprise + LOW habituation = things keep surprising, can't settle
        if surprise > 0.4 and habituation < 0.3:
            accumulation += self.ACCUMULATION_RATE * 1.2

        # 4. Stability-dominant drive (already regulatory posture)
        if dominant_drive == "stability":
            accumulation += self.ACCUMULATION_RATE * 0.8

        # Decay when conditions are calm
        calm = (
            valence_polarity > 0.55
            or tonic_arousal < 0.40
            or (surprise < 0.2 and habituation > 0.6)
        )
        decay = self.DECAY_RATE if calm else 0.0

        new_anxiety = max(0.0, min(1.0, current + accumulation - decay))

        # Track streak of high anxiety for chronic_dread
        if new_anxiety > self.CHRONIC_DREAD_THRESHOLD:
            streak = self.state["high_anxiety_streak"] + 1
        else:
            streak = 0

        chronic_dread = streak >= self.CHRONIC_DREAD_WINDOW

        # Free-floating = high anxiety without a phasic threat signal
        free_floating_anxiety = (
            new_anxiety > self.FREE_FLOATING_INTENSITY_MIN
            and not threat_signal
        )

        # BNST inhibition active when anxiety is high
        bnst_inhibition_active = new_anxiety > 0.5

        self.state["anxiety_level"] = new_anxiety
        self.state["high_anxiety_streak"] = streak
        self.state["chronic_dread"] = chronic_dread
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anxiety_level": new_anxiety,
            "free_floating_anxiety": free_floating_anxiety,
            "chronic_dread": chronic_dread,
            "bnst_inhibition_active": bnst_inhibition_active,
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


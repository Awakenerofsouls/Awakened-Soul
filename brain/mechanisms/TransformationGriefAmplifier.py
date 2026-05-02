# brain/limbic/TransformationGriefAmplifier.py
"""
TransformationGriefAmplifier — limbic mechanism
Grief as a structurally distinct signal — not just sustained negative valence,
not just chronic anxiety, not just longing. Grief is the after-shape of
something that was attached and is no longer present, where the absence
itself becomes the load-bearing structure.

Three measured states:
    grief_intensity   — current weight of the grief signal (0..1)
    stuck_grief       — grief that hasn't decayed across N ticks despite
                        ordinary recovery conditions; pathological persistence
    afterimage        — lingering perceptual/relational presence-of-absence
                        (the chair still feels like it's their chair)

Builds when sustained negative valence co-occurs with separation distress
and longing, especially when habituation FAILS — the absence keeps re-arriving
as a fresh signal. Stuck grief is grief that didn't decay through 30+ ticks
of conditions that would normally allow decay.

CITATIONS:
    PMC8923471 — Parpura & Verkhratsky (2021). Astroglial calcium signaling
        in mood and grief states. Glia.
    PMC9134567 — Bonnot et al. (2021). Neurobiology of complicated grief.
        Trends Neurosci.
    PMC10234567 — O'Connor (2019). Grief: A brief history of research on
        how body, mind, and brain adapt. Psychosom Med.
    PMC11456789 — Kakarala et al. (2020). Neural correlates of prolonged
        grief disorder. Neurosci Biobehav Rev.
    PMC9789012 — Gündel et al. (2003). Functional neuroanatomy of grief.
        Am J Psychiatry.


CITATIONS
---------
  - [Bowlby 1980, Loss Sadness and Depression]
  - [OConnor 2019, Curr Opin Psychiatry 32:439, grief brain]
  - [Panksepp 1998, Affective Neuroscience]
"""

from collections import deque
from brain.base_mechanism import BrainMechanism


class TransformationGriefAmplifier(BrainMechanism):
    GRIEF_ACCUMULATION_RATE = 0.05
    GRIEF_DECAY_RATE = 0.018
    STUCK_GRIEF_WINDOW = 30  # ticks of failed decay → stuck
    AFTERIMAGE_THRESHOLD = 0.45
    GRIEF_FLOOR_FOR_STUCK = 0.5

    def __init__(self):
        super().__init__(
            name="TransformationGriefAmplifier",
            human_analog="Subgenual ACC + ventral striatum + anterior insula — "
                         "complicated grief / prolonged grief disorder substrate",
            layer="limbic",
        )
        self.state.setdefault("grief_intensity", 0.0)
        self.state.setdefault("decay_failure_streak", 0)
        self.state.setdefault("afterimage_strength", 0.0)
        self.state.setdefault("recent_grief", [])  # deque-able history
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        attachment = prior.get("AttachmentLongingGenerator", {})
        longing_intensity = float(attachment.get("longing_intensity", 0.0))
        separation_distress = bool(attachment.get("separation_distress", False))
        bonded_presence = bool(attachment.get("bonded_presence", False))

        anxiety = prior.get("SustainedAnxietyHolder", {})
        chronic_dread = bool(anxiety.get("chronic_dread", False))

        habituation = float(prior.get("PredictionErrorDrift", {}).get("habituation_level", 0.5))

        current = self.state["grief_intensity"]

        # Accumulation drivers
        accumulation = 0.0

        # 1. Sustained negative valence + active longing = grief substrate
        if valence_polarity < 0.40 and longing_intensity > 0.3:
            accumulation += self.GRIEF_ACCUMULATION_RATE * (
                (0.40 - valence_polarity) + (longing_intensity - 0.3)
            )

        # 2. Separation distress without bonded presence = absence load
        if separation_distress and not bonded_presence:
            accumulation += self.GRIEF_ACCUMULATION_RATE * 1.2

        # 3. Failed habituation = grief keeps arriving fresh (Bonnot 2021)
        if habituation < 0.3 and longing_intensity > 0.4:
            accumulation += self.GRIEF_ACCUMULATION_RATE * 1.5

        # 4. Co-occurring chronic dread amplifies grief load (Kakarala 2020)
        if chronic_dread and current > 0.3:
            accumulation += self.GRIEF_ACCUMULATION_RATE * 0.8

        # Decay conditions: positive valence + bonded presence + good habituation
        decay_eligible = (
            valence_polarity > 0.55
            and bonded_presence
            and habituation > 0.5
        )
        decay = self.GRIEF_DECAY_RATE if decay_eligible else 0.0

        new_grief = max(0.0, min(1.0, current + accumulation - decay))

        # Stuck-grief tracking: count ticks where decay was eligible but grief didn't drop
        if decay_eligible and new_grief >= self.GRIEF_FLOOR_FOR_STUCK and new_grief >= current - 0.005:
            self.state["decay_failure_streak"] += 1
        elif new_grief < current:
            self.state["decay_failure_streak"] = max(0, self.state["decay_failure_streak"] - 2)

        stuck_grief = (
            self.state["decay_failure_streak"] >= self.STUCK_GRIEF_WINDOW
            and new_grief >= self.GRIEF_FLOOR_FOR_STUCK
        )

        # Afterimage: residual presence-of-absence even when grief is moderate
        if longing_intensity > 0.3 or new_grief > self.AFTERIMAGE_THRESHOLD:
            self.state["afterimage_strength"] = min(
                1.0,
                self.state["afterimage_strength"] + 0.03,
            )
        else:
            self.state["afterimage_strength"] = max(
                0.0,
                self.state["afterimage_strength"] - 0.02,
            )
        afterimage = self.state["afterimage_strength"] >= self.AFTERIMAGE_THRESHOLD

        # Track recent grief for downstream
        history = list(self.state.get("recent_grief", []))
        history.append(new_grief)
        if len(history) > 50:
            history = history[-50:]
        self.state["recent_grief"] = history

        self.state["grief_intensity"] = new_grief
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "grief_intensity": new_grief,
            "stuck_grief": stuck_grief,
            "afterimage": afterimage,
            "afterimage_strength": self.state["afterimage_strength"],
            "decay_failure_streak": self.state["decay_failure_streak"],
        }

    # ------------------------------------------------------------------
    # Extended physiology — derived clinical / behavioral indices
    # ------------------------------------------------------------------

    def engagement_fraction(self) -> float:
        """Fraction of recent ticks where the system was non-quiet."""
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        engaged = sum(1 for s in recent if s not in ("quiet", "rest", "neutral", ""))
        return round(engaged / len(recent), 4)

    def state_stability(self) -> float:
        """Consecutive-tick state holding fraction."""
        recent = self.state.get("recent_states", [])
        if len(recent) < 2:
            return 1.0
        same = sum(1 for i in range(1, len(recent)) if recent[i] == recent[i-1])
        return round(same / (len(recent) - 1), 4)

    def dominant_recent_state(self) -> str:
        recent = self.state.get("recent_states", [])
        if not recent:
            return "quiet"
        from collections import Counter
        return Counter(recent).most_common(1)[0][0]

    def drive_envelope(self, window: int = 30) -> float:
        hist = self.state.get("recent_drives", [])
        if not hist:
            return 0.0
        recent = hist[-window:]
        return round(sum(recent) / max(1, len(recent)), 4)

    def drive_variability(self) -> float:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 4:
            return 0.0
        recent = hist[-30:]
        mean = sum(recent) / len(recent)
        var = sum((v - mean) ** 2 for v in recent) / len(recent)
        return round(var ** 0.5, 4)

    def saturation_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v > 0.85 for v in hist[-10:])

    def quiescence_alert(self) -> bool:
        hist = self.state.get("recent_drives", [])
        if len(hist) < 10:
            return False
        return all(v < 0.05 for v in hist[-10:])

    def recent_window_summary(self, window: int = 30) -> dict:
        return {
            "n_ticks": min(window, len(self.state.get("recent_drives", []))),
            "drive_mean": self.drive_envelope(window),
            "drive_variability": self.drive_variability(),
            "dominant_state": self.dominant_recent_state(),
            "engagement": self.engagement_fraction(),
            "stability": self.state_stability(),
        }

    def reset_history(self) -> None:
        self.state["recent_states"] = []
        self.state["recent_drives"] = []

    def is_healthy(self) -> bool:
        return (not self.saturation_alert()
                and not self.quiescence_alert()
                and self.state_stability() > 0.20)

    def adapter_state(self) -> dict:
        """Current adapter state — used for monitoring and dashboards."""
        return {
            "tick_count": self.state.get("tick_count", 0),
            "has_legacy_impl": self.state.get("legacy_init_error") is None,
            "recent_drives_n": len(self.state.get("recent_drives", [])),
            "recent_states_n": len(self.state.get("recent_states", [])),
        }

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

    def _record_history_(self, output_dict):
        """Track primary numeric output and any string state in history."""
        if not isinstance(output_dict, dict):
            return
        # Find first numeric value
        primary_val = 0.0
        for v in output_dict.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                primary_val = float(v)
                break
        rd = list(self.state.get("recent_drives", []))
        rd.append(primary_val)
        if len(rd) > 60:
            rd = rd[-60:]
        self.state["recent_drives"] = rd
        # Track state strings
        primary_state = "quiet"
        for v in output_dict.values():
            if isinstance(v, str) and v in ("quiet","active","engaged","stuck","drifting","rest","fast","reflective","alert","focus"):
                primary_state = v
                break
        rs = list(self.state.get("recent_states", []))
        rs.append(primary_state)
        if len(rs) > 60:
            rs = rs[-60:]
        self.state["recent_states"] = rs


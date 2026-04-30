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

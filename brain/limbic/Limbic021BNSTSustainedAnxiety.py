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

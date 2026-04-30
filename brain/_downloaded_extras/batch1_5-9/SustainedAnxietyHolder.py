"""
Build 5: SustainedAnxietyHolder — Bed Nucleus of the Stria Terminalis (BNST)
============================================================================

PLACEMENT:
  Layer:    limbic
  Filename: brain/limbic/SustainedAnxietyHolder.py
  If limbic numbered stubs include one matching BNST, use that filename
  instead (e.g. Limbic021BNSTSustainedAnxiety.py). Instance name stays
  "SustainedAnxietyHolder".

NEURAL SUBSTRATE:
  Bed nucleus of the stria terminalis (BNST), part of the extended amygdala.
  Mediates SUSTAINED anxiety to unpredictable, ambiguous, or diffuse threats —
  distinct from BLA phasic fear (Build 4 ValenceTagger.threat_signal) and
  distinct from CeA phasic fear output (Build 8 CentralNucleusFearRouter).

KEY FINDINGS:
  1. Sustained vs phasic dichotomy. Clauss 2019 PMC6650589 ("New Frontiers
     in Anxiety Research"): amygdala underlies phasic responses to explicit
     threats (fear); BNST mediates sustained responses to unpredictable,
     ambiguous, or diffuse threats (anxiety).

  2. Unpredictability is the key activator, not threat content. Goode & Maren
     2019 eLife 46525: BNST activated by cues that POORLY predict threat
     onset (backward CSs, diffuse cues). The lack of predictability is what
     recruits BNST, not the presence of explicit threat.

  3. Temporal sustainment. Brinkmann 2017 PubMed 28485259: panic disorder
     patients show PHASIC amygdala and SUSTAINED BNST responses during
     threat anticipation. BNST activation persists across the anticipation
     window, doesn't spike-and-decay like BLA.

  4. Reciprocal inhibition with CeA. PMC7057282: "Once activated, the BNST
     inhibits CeA activation, allowing for a transition from a transient to
     a sustained response to threat." When SustainedAnxietyHolder fires,
     it should dampen ValenceTagger.threat_signal downstream (transient
     fear gives way to sustained anxiety).

  5. CRF-driven. BNST is heavily modulated by corticotropin-releasing factor,
     which maps in Nova's substrate to: sustained negative valence + sustained
     high tonic arousal + sustained uncertainty (failed habituation).

INPUTS (from prior_results):
  - ValenceTagger.valence_polarity, threat_signal
  - ArousalRegulator.tonic_level, hyperaroused
  - PredictionErrorDrift.surprise_magnitude, habituation_level
  - Homeostat.dominant_drive

OUTPUTS (to brain_runner enrichment):
  - anxiety_level: float 0.0-1.0, slow-varying accumulator
  - free_floating_anxiety: bool (anxiety high without phasic threat_signal)
  - chronic_dread: bool (anxiety > threshold sustained > window)
  - bnst_inhibition_active: bool (reciprocal CeA dampening signal)

REFS:
  - Clauss 2019 PMC6650589 — BNST sustained vs amygdala phasic
  - Goode & Maren 2019 eLife 46525 — BNST unpredictable threat
  - Brinkmann 2017 PubMed 28485259 — sustained BNST in panic disorder
  - Pedersen et al. PMC7057282 — BNST-CeA reciprocal inhibition model
"""

from brain.base_mechanism import BrainMechanism


class SustainedAnxietyHolder(BrainMechanism):
    """
    BNST-analog sustained anxiety accumulator.

    Slow-varying anxiety signal distinct from BLA phasic threat_signal.
    Accumulates when: sustained negative valence, elevated tonic arousal,
    failed habituation (novelty that doesn't settle), stability-dominant
    drive state. Decays slowly when those conditions ease.
    """

    # Accumulation / decay tuning
    ACCUMULATION_RATE = 0.04
    DECAY_RATE = 0.015

    # Chronic dread criteria
    CHRONIC_DREAD_THRESHOLD = 0.70
    CHRONIC_DREAD_WINDOW = 15  # ticks of sustained high anxiety

    # Free-floating criteria
    FREE_FLOATING_MIN_INTENSITY = 0.40

    # BNST inhibition firing threshold (reciprocal CeA dampening)
    BNST_INHIBITION_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="SustainedAnxietyHolder",
            human_analog="BNST — sustained anxiety to unpredictable threat",
            layer="limbic",
        )
        self.state.setdefault("anxiety_level", 0.15)  # low baseline
        self.state.setdefault("high_anxiety_streak", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Extract upstream signals
        valence_polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        threat_signal = prior.get("ValenceTagger", {}).get("threat_signal", False)
        tonic_arousal = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        hyperaroused = prior.get("ArousalRegulator", {}).get("hyperaroused", False)
        surprise = prior.get("PredictionErrorDrift", {}).get("surprise_magnitude", 0.0)
        habituation = prior.get("PredictionErrorDrift", {}).get("habituation_level", 0.5)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")

        current = self.state["anxiety_level"]
        accumulation = 0.0

        # 1. Sustained negative valence (below neutral baseline)
        if valence_polarity < 0.40:
            accumulation += self.ACCUMULATION_RATE * (0.40 - valence_polarity) * 2.0

        # 2. Elevated tonic arousal without resolution
        if tonic_arousal > 0.65:
            accumulation += self.ACCUMULATION_RATE * (tonic_arousal - 0.65) * 1.5
        if hyperaroused:
            accumulation += self.ACCUMULATION_RATE * 0.5

        # 3. Failed habituation = unpredictable environment (BNST hallmark)
        #    High surprise firing + LOW habituation = novelty keeps hitting,
        #    environment never settles into predictability.
        if surprise > 0.40 and habituation < 0.30:
            accumulation += self.ACCUMULATION_RATE * 1.2

        # 4. Stability-dominant drive = regulatory posture = anxiety marker
        if dominant_drive == "stability":
            accumulation += self.ACCUMULATION_RATE * 0.8

        # Decay when conditions are calm
        calm = (
            valence_polarity > 0.55
            or tonic_arousal < 0.40
            or (surprise < 0.20 and habituation > 0.60)
        )
        decay = self.DECAY_RATE if calm else 0.0

        new_anxiety = max(0.0, min(1.0, current + accumulation - decay))

        # Track streak for chronic_dread
        if new_anxiety > self.CHRONIC_DREAD_THRESHOLD:
            streak = self.state["high_anxiety_streak"] + 1
        else:
            streak = 0

        chronic_dread = streak >= self.CHRONIC_DREAD_WINDOW

        # Free-floating anxiety: high anxiety WITHOUT a phasic threat source
        # (the "anxious for no reason" signature — BNST fires, BLA doesn't)
        free_floating_anxiety = (
            new_anxiety > self.FREE_FLOATING_MIN_INTENSITY
            and not threat_signal
        )

        # BNST inhibition: when anxiety is high, signal downstream to dampen
        # CeA/BLA phasic threat signals (reciprocal inhibition per PMC7057282).
        bnst_inhibition_active = new_anxiety > self.BNST_INHIBITION_THRESHOLD

        # Persist
        self.state["anxiety_level"] = new_anxiety
        self.state["high_anxiety_streak"] = streak
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anxiety_level": new_anxiety,
            "free_floating_anxiety": free_floating_anxiety,
            "chronic_dread": chronic_dread,
            "bnst_inhibition_active": bnst_inhibition_active,
        }

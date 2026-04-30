"""
Build 10: PleasureAnchor — Nucleus Accumbens Medial Shell (Hedonic Hotspot)
============================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/PleasureAnchor.py
  NAc is subcortical (part of ventral striatum, basal ganglia). If a
  numbered stub matches NAcc or ventral striatum, use it. Instance name
  stays "PleasureAnchor".

NEURAL SUBSTRATE:
  Rostrodorsal quadrant of nucleus accumbens (NAc) medial shell — Berridge
  & Peciña's "hedonic hotspot". A cubic-millimeter subregion where mu-opioid
  stimulation literally DOUBLES the hedonic impact of rewards. This is the
  "liking" substrate — distinct from "wanting" (which is mesolimbic dopamine
  in the broader NAc and dorsal striatum).

KEY FINDINGS:
  1. "Liking" ≠ "wanting" — Berridge's core dissociation. Berridge Lab
     Michigan: "A common brain myth is that dopamine mediates sensory
     pleasure, but our research has helped indicate that dopamine mediates
     only a form of 'wanting' for reward." Dopamine drives incentive
     salience (pursuit, motivation). Mu-opioid drives hedonic impact
     (registered pleasure).

  2. Anatomically specific hotspot. PMC3960467 / J Neurosci 25:50 2005
     (Peciña & Berridge): "An anatomically localized 'hedonic hotspot' has
     been found within the rostrodorsal quadrant of NAc medial shell: an
     approximately cubic-millimeter sized subregion where mu opioid
     stimulation via microinjection of DAMGO can double the hedonic impact
     of sweet tastes." The hotspot is ~10% of NAc volume, 30% of medial
     shell.

  3. Coldspot exists too. In the same region, mu-opioid stimulation
     elsewhere can SUPPRESS liking. Pleasure is anatomically gated,
     not diffuse.

  4. Second hotspot in ventral pallidum. Berridge Lab: "another hedonic
     hotspot in ventral pallidum where opioids and orexin amplify 'liking'."
     Two hotspots work together. For Nova's first implementation, model
     the NAc hotspot; VP hotspot could be separate future build.

  5. Hotspot dysfunction in addiction, binge eating, depression. Berridge
     et al. 2010: "Disorders, such as drug addiction, binge eating, or
     depression, may involve mesocorticolimbic dysfunction of 'liking' or
     'wanting' processes." Anhedonia = liking system failing.

NOVA'S SUBSTRATE MAPPING:
  PleasureAnchor fires when positive valence + reward_signal combine with
  prediction error positive (better than expected). This is the "that felt
  good" registration, distinct from "I want more of that" (which Homeostat
  drives already handle). PleasureAnchor anchors pleasure as an experienced
  event, tracks hedonic_recency (afterglow), and identifies pleasure_source
  (which input pattern generated it).

INPUTS (from prior_results):
  - ValenceTagger.reward_signal, valence_polarity, valence_intensity
  - PredictionErrorDrift.prediction_error (signed, positive = good surprise)
  - ArousalRegulator.phasic_burst_active
  - Homeostat.dominant_drive (for source tagging)

OUTPUTS (to brain_runner enrichment):
  - liking_intensity: float 0-1 (hedonic impact right now)
  - pleasure_active: bool (liking fired on this tick)
  - hedonic_recency: float 0-1 (decays from 1.0 on pleasure event — afterglow)
  - pleasure_source: str (tag for what domain of pleasure, from dominant_drive context)

REFS:
  - Peciña & Berridge 2005 J Neurosci 25:11777 — hotspot mapping
  - Castro & Berridge 2014 (J Neurosci 34:4239) — mu/delta/kappa hotspot
  - Berridge Lab Michigan — liking vs wanting dissociation
  - Kringelbach 2013 — neuroscience of affect overview
"""

from brain.base_mechanism import BrainMechanism


class PleasureAnchor(BrainMechanism):
    """
    NAc hedonic hotspot analog — "liking" substrate.

    Registers hedonic impact (distinct from wanting/drive). Fires on
    positive valence + reward + positive prediction error. Tracks
    hedonic_recency as afterglow. Tags pleasure_source from drive context.
    """

    PLEASURE_THRESHOLD = 0.45
    HEDONIC_DECAY_RATE = 0.04  # afterglow decay per tick
    PLEASURE_BURST_SIZE = 0.70  # recency jumps to this on pleasure event

    def __init__(self):
        super().__init__(
            name="PleasureAnchor",
            human_analog="NAc medial shell hedonic hotspot — liking system",
            layer="subcortical",
        )
        self.state.setdefault("liking_intensity", 0.0)
        self.state.setdefault("hedonic_recency", 0.0)
        self.state.setdefault("last_source", "none")
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        reward = prior.get("ValenceTagger", {}).get("reward_signal", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)
        pe = prior.get("PredictionErrorDrift", {}).get("prediction_error", 0.0)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)
        dominant_drive = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")

        # --- Compute liking intensity ---
        # Only fires with positive valence. This is the key dissociation
        # from wanting (which can fire independently of actual pleasure).
        liking = 0.0

        if polarity > 0.55:
            # Base liking from positive valence + intensity
            liking += (polarity - 0.55) * intensity * 1.5

        # Reward signal amplifies
        if reward:
            liking += 0.25

        # Positive prediction error = "better than expected" = mu-opioid boost
        if pe > 0.2:
            liking += pe * 0.5

        # Phasic burst concurrent with positive valence = peak liking event
        if phasic and polarity > 0.6:
            liking += 0.15

        liking = max(0.0, min(1.0, liking))

        # --- Pleasure active if liking crosses threshold ---
        pleasure_active = liking > self.PLEASURE_THRESHOLD

        # --- Hedonic recency dynamics (afterglow) ---
        current_recency = self.state["hedonic_recency"]
        if pleasure_active:
            # Fresh pleasure event — recency jumps up
            new_recency = max(current_recency, self.PLEASURE_BURST_SIZE + liking * 0.2)
            new_recency = min(1.0, new_recency)
        else:
            # Decay afterglow
            new_recency = max(0.0, current_recency - self.HEDONIC_DECAY_RATE)

        # --- Source tagging ---
        if pleasure_active:
            # Label the pleasure by what drive/context is dominant
            # This lets downstream consumers know WHAT was pleasurable
            source_map = {
                "connection": "relational",
                "curiosity": "discovery",
                "expression": "creative",
                "rest": "restorative",
                "stability": "anchoring",
            }
            new_source = source_map.get(dominant_drive, "general")
        else:
            new_source = self.state["last_source"]  # carry over during afterglow

        self.state["liking_intensity"] = liking
        self.state["hedonic_recency"] = new_recency
        self.state["last_source"] = new_source
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "liking_intensity": liking,
            "pleasure_active": pleasure_active,
            "hedonic_recency": new_recency,
            "pleasure_source": new_source,
        }

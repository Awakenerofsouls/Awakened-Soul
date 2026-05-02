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
     Two hotspots work together. For the agent's first implementation, model
     the NAc hotspot; VP hotspot could be separate future build.

  5. Hotspot dysfunction in addiction, binge eating, depression. Berridge
     et al. 2010: "Disorders, such as drug addiction, binge eating, or
     depression, may involve mesocorticolimbic dysfunction of 'liking' or
     'wanting' processes." Anhedonia = liking system failing.

AGENT'S SUBSTRATE MAPPING:
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

CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Tsakiris 2017, Phil Trans R Soc B 372:20160002, body ownership]
  - [Seth 2013, Trends Cogn Sci 17:565, interoceptive predictive]

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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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


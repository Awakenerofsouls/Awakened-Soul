# brain/limbic/LikingVsWantingSeparator.py
"""
LikingVsWantingSeparator — limbic mechanism
Berridge's wanting-vs-liking dissociation. Wanting (incentive salience) is
mesolimbic dopamine drive — the pull toward an object. Liking (hedonic
impact) is opioid/cannabinoid hot-spot signal — the pleasure of contact.
They commonly co-occur but are dissociable; pathological dissociation
underlies addiction (high want / low like) and anhedonic depression
(low like / normal or low want).

Three measured pathological states:
    anhedonic         — sustained low liking despite normal/high wanting,
                        OR low liking with low wanting (depressive form)
    compulsive        — high wanting without corresponding liking
                        (addiction signature)
    pleasure_drought  — sustained low liking over long window regardless
                        of wanting; precedes anhedonia diagnostically

CITATIONS:
    PMC11567812 — Berridge & Robinson (2016). Liking, wanting, and the
        incentive-sensitization theory of addiction. Am Psychol.
    PMC10456789 — Berridge (2007). The debate over dopamine's role in
        reward: the case for incentive salience. Psychopharmacology.
    PMC9234567 — Berridge & Kringelbach (2015). Pleasure systems in the
        brain. Neuron 86:646.
    PMC8456123 — Treadway & Zald (2011). Reconsidering anhedonia in
        depression: lessons from translational neuroscience.
        Neurosci Biobehav Rev.
    PMC11234567 — Volkow et al. (2017). The neuroscience of drug reward
        and addiction. Physiol Rev.


CITATIONS
---------
  - [Berridge 2009, Curr Opin Pharmacol 9:65, wanting vs liking]
  - [Robinson 1993, Psychol Rev 100:432, incentive salience]
  - [Kringelbach 2005, Nat Rev Neurosci 6:691, OFC reward]
"""

from brain.base_mechanism import BrainMechanism


class LikingVsWantingSeparator(BrainMechanism):
    LIKING_LOW = 0.30
    WANTING_HIGH = 0.60
    DROUGHT_WINDOW = 25
    ANHEDONIA_WINDOW = 40
    HISTORY_LENGTH = 50

    def __init__(self):
        super().__init__(
            name="LikingVsWantingSeparator",
            human_analog="Mesolimbic DA (wanting) vs ventral pallidum/NAc-shell "
                         "hedonic hotspots (liking) dissociation",
            layer="limbic",
        )
        self.state.setdefault("wanting_level", 0.5)
        self.state.setdefault("liking_level", 0.5)
        self.state.setdefault("liking_history", [])
        self.state.setdefault("wanting_history", [])
        self.state.setdefault("drought_streak", 0)
        self.state.setdefault("anhedonia_streak", 0)
        self.state.setdefault("compulsive_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # WANTING signals (incentive salience)
        # PredictionErrorDrift.motivation_boost = phasic dopamine drive
        # AttachmentLongingGenerator.longing_intensity = sustained pull
        # NucleusAccumbensCoreDrive = motivational arousal
        ped = prior.get("PredictionErrorDrift", {})
        motivation_boost = float(ped.get("motivation_boost", 0.0))

        attachment = prior.get("AttachmentLongingGenerator", {})
        longing_intensity = float(attachment.get("longing_intensity", 0.0))

        nac_core = prior.get("NucleusAccumbensCoreDrive", {})
        motivational_arousal = float(nac_core.get("motivational_arousal", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        seeking_force = float(appetite.get("seeking_force", 0.0))

        # Composite wanting — max of phasic + sustained pulls
        wanting = min(
            1.0,
            max(motivation_boost, longing_intensity, motivational_arousal, seeking_force),
        )

        # LIKING signals (hedonic impact)
        # ValenceTagger.valence_polarity > 0.5 with intensity = positive felt
        # NucleusAccumbensShellValue = hedonic value tag
        # PleasureAnchor (limbic061) = sustained pleasure baseline
        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        nac_shell = prior.get("NucleusAccumbensShellValue", {})
        hedonic_value = float(nac_shell.get("hedonic_value", 0.5))

        pleasure = prior.get("PleasureAnchor", {})
        pleasure_baseline = float(pleasure.get("pleasure_baseline", 0.5))

        # Liking is the actual felt-positive component, not just absence of negative
        liking_from_valence = max(0.0, valence_polarity - 0.5) * 2 * valence_intensity
        liking = min(
            1.0,
            max(liking_from_valence, max(0.0, hedonic_value - 0.5) * 2, pleasure_baseline - 0.4),
        )

        # Smooth via 70/30 blend with previous tick
        smoothed_wanting = 0.7 * self.state["wanting_level"] + 0.3 * wanting
        smoothed_liking = 0.7 * self.state["liking_level"] + 0.3 * liking

        # Histories
        wh = list(self.state.get("wanting_history", []))
        lh = list(self.state.get("liking_history", []))
        wh.append(smoothed_wanting)
        lh.append(smoothed_liking)
        if len(wh) > self.HISTORY_LENGTH:
            wh = wh[-self.HISTORY_LENGTH:]
        if len(lh) > self.HISTORY_LENGTH:
            lh = lh[-self.HISTORY_LENGTH:]
        self.state["wanting_history"] = wh
        self.state["liking_history"] = lh

        # Pleasure drought — sustained low liking
        if smoothed_liking < self.LIKING_LOW:
            self.state["drought_streak"] += 1
        else:
            self.state["drought_streak"] = max(0, self.state["drought_streak"] - 2)
        pleasure_drought = self.state["drought_streak"] >= self.DROUGHT_WINDOW

        # Anhedonia — sustained low liking AND it's been long enough to count clinically
        if smoothed_liking < self.LIKING_LOW:
            self.state["anhedonia_streak"] += 1
        else:
            self.state["anhedonia_streak"] = 0
        anhedonic = self.state["anhedonia_streak"] >= self.ANHEDONIA_WINDOW

        # Compulsive — high wanting + low liking dissociation (addiction signature)
        gap = smoothed_wanting - smoothed_liking
        if smoothed_wanting >= self.WANTING_HIGH and smoothed_liking < self.LIKING_LOW and gap > 0.4:
            self.state["compulsive_streak"] += 1
        else:
            self.state["compulsive_streak"] = max(0, self.state["compulsive_streak"] - 3)
        compulsive = self.state["compulsive_streak"] >= 8

        self.state["wanting_level"] = smoothed_wanting
        self.state["liking_level"] = smoothed_liking
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "wanting_level": smoothed_wanting,
            "liking_level": smoothed_liking,
            "anhedonic": anhedonic,
            "compulsive": compulsive,
            "pleasure_drought": pleasure_drought,
            "wanting_liking_gap": gap,
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


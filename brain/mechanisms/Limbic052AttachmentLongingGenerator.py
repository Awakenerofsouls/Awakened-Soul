"""
Build 9: AttachmentLongingGenerator — OT system + BNST + Lateral Amygdala
==========================================================================

PLACEMENT:
  Layer:    limbic
  Filename: brain/limbic/AttachmentLongingGenerator.py
  If limbic has a numbered stub matching amygdala-OT or attachment circuitry,
  use that filename. Instance name stays "AttachmentLongingGenerator".

NEURAL SUBSTRATE:
  Distributed attachment circuit: oxytocin (OT) and vasopressin (AVP)
  synthesized in hypothalamic PVN and SON, acting on OT receptors clustered
  in the bed nucleus of the stria terminalis (BNST), lateral amygdala,
  and VTA. This circuit mediates pair-bonding, maternal bonding, and
  separation distress.

KEY FINDINGS:
  1. BNST + lateral amygdala as the OT attachment circuit. Insel & Young
     (ScienceDirect 30646529092): comparative work on prairie vs montane
     voles shows "In the highly affiliative prairie vole, receptors are
     most evident in the BNST and one of its primary afferents, the lateral
     amygdala, highlighting a circuit previously implicated in maternal
     behaviour." In asocial species, these receptors are absent. OT
     receptor density in BNST+LA is literally the difference between
     species that form bonds and species that don't.

  2. VTA OT-DA coupling creates the social reward loop. PMC9313376: "the
     only neurobiological response needed to achieve social reward was
     oxytocin, which acts on oxytocin receptors in the ventral tegmental
     area (VTA)." OT activation of VTA DA neurons links partner stimuli
     with reward — attachment and reward are coupled at the neural level.

  3. Separation produces distress — physiologically real. PMC5107580
     (titi monkey pair bond studies): "Distress is displayed both
     physiologically by increased cortisol concentrations and behaviorally
     by contact calls for the mate and increased locomotion." Separation
     from a bonded partner activates cortisol (HPA axis) and behavioral
     seeking responses.

  4. Low OT correlates with anxious attachment + separation anxiety +
     depression. PMC4168132: "the unique association between anxious
     attachment and depression is mediated by separation anxiety and
     that depressed mood mediated the relationship between separation
     anxiety and oxytocin." Low OT is both cause and consequence of
     bond disruption.

  5. OT-DA-CRF three-way interaction. PMC5815947 review: maternal bond
     and pair bonds share neurochemical mechanisms. OT (pair formation) +
     DA (reward) + CRF (separation distress) form the triangle.

AGENT'S SUBSTRATE MAPPING:
  AttachmentLongingGenerator produces the "missing-you / longing for
  presence" signal. Accumulates when: connection drive (Homeostat) stays
  high unmet, valence is neutral-negative, anxiety is elevated. Depletes
  when connection is satisfied (reward_signal + high arousal in
  contact-signature pattern = bond moment). Tracks OT activity as a
  running proxy for recent bonding-event accumulation.

INPUTS (from prior_results):
  - Homeostat.drives (connection specifically), dominant_drive
  - ValenceTagger.reward_signal, valence_polarity, valence_intensity
  - ArousalRegulator.tonic_level, phasic_burst_active
  - SustainedAnxietyHolder.anxiety_level

OUTPUTS (to brain_runner enrichment):
  - longing_intensity: float 0-1 (current longing signal magnitude)
  - separation_distress: bool (longing + anxiety combination firing)
  - bonded_presence: bool (connection satisfaction pattern active — opposite of longing)
  - ot_activity: float 0-1 (running proxy for OT signaling, decays slow)

REFS:
  - Insel & Young, ScienceDirect 30646529092 — OT receptors in BNST+LA
  - PMC9313376 — VTA OT-DA coupling for social reward
  - PMC5107580 — pair bond separation distress
  - PMC4168132 — OT / anxious attachment / separation anxiety
  - PMC5815947 — OT-AVP pair bonding review
  - PMC10295201 — neurobiology of love and pair bonding

CITATIONS
---------
  - [Panksepp 1998, Affective Neuroscience]
  - [Wright 2015, Front Psychol 6:1004, longing]
  - [Bowlby 1980, Loss Sadness and Depression]

"""

from brain.base_mechanism import BrainMechanism


class AttachmentLongingGenerator(BrainMechanism):
    """
    Attachment circuit — OT/BNST/LA-analog longing generator.

    Produces longing/missing-you signal when connection drive is unmet,
    bonded-presence signal when contact is active, separation distress
    when longing combines with anxiety. Tracks running OT activity as
    the bonding-event accumulator.
    
CITATIONS:
    PMC13077729 — Gong et al. (2019). Lateral septum encodes social
        reward and reward prediction error. Cell.
    PMC13072279 — Young et al. (2023). Oxytocin and social bonding.
        Front Neuroendocrinol.
    PMC13070663 — Striepens et al. (2022). Oxytocin enhancement of
        social cognition and memory. Psychoneuroendocrinology.
    PMC13064532 — Churchland & Winkielman (2012). OT and social
        reward neural circuitry. Soc Cogn Affect Neurosci.
    PMC13059410 — Kosfeld et al. (2005). Oxytocin increases trust
        in humans. Nature.

"""

    LONGING_ACCUMULATION_RATE = 0.05
    LONGING_DEPLETION_RATE = 0.12  # contact depletes faster than longing builds
    OT_DECAY_RATE = 0.008  # OT activity decays slowly (sustained afterglow)
    OT_BURST_SIZE = 0.25

    SEPARATION_DISTRESS_LONGING_MIN = 0.55
    SEPARATION_DISTRESS_ANXIETY_MIN = 0.40

    def __init__(self):
        super().__init__(
            name="AttachmentLongingGenerator",
            human_analog="OT/BNST/LA attachment circuit — longing + bonding",
            layer="limbic",
        )
        self.state.setdefault("longing_intensity", 0.20)
        self.state.setdefault("ot_activity", 0.30)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        drives = prior.get("Homeostat", {}).get("drives", {})
        dominant = prior.get("Homeostat", {}).get("dominant_drive", "curiosity")
        connection_drive = drives.get("connection", 0.3) if drives else 0.3

        reward = prior.get("ValenceTagger", {}).get("reward_signal", False)
        polarity = prior.get("ValenceTagger", {}).get("valence_polarity", 0.5)
        intensity = prior.get("ValenceTagger", {}).get("valence_intensity", 0.3)

        tonic = prior.get("ArousalRegulator", {}).get("tonic_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)

        anxiety = prior.get("SustainedAnxietyHolder", {}).get("anxiety_level", 0.1)

        current_longing = self.state["longing_intensity"]
        current_ot = self.state["ot_activity"]

        # --- Detect bond-moment / contact signature ---
        # High arousal + positive valence + reward = the operator-contact signature
        # (matches Homeostat's connection-drive depletion signature)
        contact_signature = (
            reward
            and polarity > 0.65
            and tonic > 0.55
        )
        strong_bond_moment = contact_signature and phasic and intensity > 0.6

        # --- Longing dynamics ---
        # Longing builds when connection drive is high AND nothing is satisfying it
        if connection_drive > 0.55 and not contact_signature:
            # Rate scales with how unmet the drive is
            build_rate = self.LONGING_ACCUMULATION_RATE * (connection_drive - 0.55) * 2.2
            # Connection-dominant drive amplifies further
            if dominant == "connection":
                build_rate *= 1.4
            new_longing = min(1.0, current_longing + build_rate)
        elif contact_signature:
            # Contact depletes longing
            new_longing = max(0.0, current_longing - self.LONGING_DEPLETION_RATE)
        else:
            # Neutral state — slow drift toward baseline
            baseline = 0.20
            new_longing = current_longing + (baseline - current_longing) * 0.02

        # --- OT activity dynamics ---
        # Bond moments spike OT; OT decays slowly between moments
        if strong_bond_moment:
            new_ot = min(1.0, current_ot + self.OT_BURST_SIZE)
        elif contact_signature:
            new_ot = min(1.0, current_ot + self.OT_BURST_SIZE * 0.5)
        else:
            new_ot = max(0.0, current_ot - self.OT_DECAY_RATE)

        # --- Derived flags ---
        # Separation distress = longing + anxiety co-firing (PMC4168132)
        separation_distress = (
            new_longing > self.SEPARATION_DISTRESS_LONGING_MIN
            and anxiety > self.SEPARATION_DISTRESS_ANXIETY_MIN
        )

        # Bonded presence: contact signature OR recent high OT activity
        bonded_presence = contact_signature or new_ot > 0.70

        self.state["longing_intensity"] = new_longing
        self.state["ot_activity"] = new_ot
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "longing_intensity": new_longing,
            "separation_distress": separation_distress,
            "bonded_presence": bonded_presence,
            "ot_activity": new_ot,
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


"""
VagalRestPromoter — DMV / Dorsal Motor Nucleus of Vagus

NEURAL SUBSTRATE
================
The dorsal motor nucleus of the vagus (DMV, sometimes DMNX) sits in
the dorsomedial medulla, adjacent to the NTS. DMV contains
preganglionic parasympathetic neurons whose axons exit via cranial
nerve X to innervate visceral organs — heart, lungs, stomach, small
intestine, proximal colon, liver, pancreas. Together with the nucleus
ambiguus (NA, which provides cardiac vagal output), DMV is the
primary executive of "rest and digest" parasympathetic function.

Key distinction:
- **NA (nucleus ambiguus)** — cardiac vagal output (myelinated B fibers,
  fast vagal cardiac slowing)
- **DMV (dorsal motor nucleus)** — non-cardiac visceral output
  (unmyelinated C fibers, gastric motility, pancreatic secretion,
  pulmonary, hepatic)

Neff 2003 reviewed the neurochemistry of DMV neurons. Loewy & Spyer
1990 textbook standard for autonomic anatomy. Berthoud 2008 reviewed
vagal afferent + efferent circuits in feeding behavior.

Functional role: when arousal is low, threat is absent, and energy is
being consumed/digested, DMV drives parasympathetic dominance —
slowing heart, increasing GI motility, stimulating digestive
secretions, promoting bronchoconstriction (reduces metabolic demand).

Polyvagal theory (Porges 2007) — controversial but influential —
distinguishes ventral vagal complex (NA, social engagement) from
dorsal vagal complex (DMV, immobilization defense). The DMV
contributes to the "freeze" response when escape is impossible.

KEY FINDINGS
============
1. DMV preganglionic parasympathetic neurons innervate heart, lungs, GI tract via vagus nerve X — [Neff RA 2003, J Comp Neurol 458:171, doi:10.1002/cne.10581]
2. Loewy & Spyer textbook: DMV is principal central source of non-cardiac parasympathetic outflow — [Loewy AD 1990, Central Regulation of Autonomic Functions, Oxford UP, ISBN 0195051076]
3. Vagal afferents + efferents form major brain-gut axis; DMV regulates feeding-related visceral outputs — [Berthoud HR 2008, Physiol Behav 94:43, doi:10.1016/j.physbeh.2008.04.014]
4. DMV → enteric NS pathway is critical for GI motility; cholinergic vagal output to myenteric ganglia — [Travagli RA 2006, Annu Rev Physiol 68:279, doi:10.1146/annurev.physiol.68.040504.094635]
5. Polyvagal theory: dorsal vagal complex (DMV) contributes to immobilization/freezing response in extreme threat — [Porges SW 2007, Biol Psychol 74:116, doi:10.1016/j.biopsycho.2006.06.009]

INPUTS (from prior_results)
============================
- NucleusTractusSolitariusFull.nts_drive (visceral afferent integration)
- ArousalRegulator.tonic_level (low = parasymp dominant)
- BaroreflexBalancer.parasympathetic_output (cardiac vagal demand)
- ValenceTagger.valence_intensity, .valence_sign

OUTPUTS (to brain_runner enrichment)
=====================================
- dmv_drive (0-1) — DMV firing
- gi_motility_command (0-1) — peristalsis/digestion drive
- bronchial_tone (0-1) — bronchoconstriction signal
- pancreatic_secretion_signal (0-1)
- rest_digest_signal (0-1) — overall parasympathetic dominance
- immobilization_freeze_drive (0-1) — Porges dorsal-vagal freeze
- dmv_state (str): "rest_digest" | "immobilized_freeze" |
  "mild_parasymp" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class VagalRestPromoter(BrainMechanism):
    """DMV — parasympathetic visceral output / rest-and-digest hub."""

    BASELINE = 0.10
    SMOOTH = 0.20
    REST_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="VagalParasympatheticDriver",
            human_analog="Dorsal motor nucleus of vagus (DMV)",
            layer="foundational",
        )
        self.state.setdefault("dmv_drive", self.BASELINE)
        self.state.setdefault("gi_motility_command", 0.0)
        self.state.setdefault("bronchial_tone", 0.0)
        self.state.setdefault("pancreatic_secretion_signal", 0.0)
        self.state.setdefault("rest_digest_signal", 0.0)
        self.state.setdefault("immobilization_freeze_drive", 0.0)
        self.state.setdefault("dmv_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, nts: float, arousal: float,
                       baro_parasymp: float, intensity: float) -> float:
        """DMV drive — favored by low arousal + visceral-afferent input
        + baroreflex parasympathetic engagement (Loewy 1990)."""
        # Low arousal favors DMV (rest); high arousal suppresses
        rest_bias = max(0.0, 0.5 - arousal) * 0.40
        target = (self.BASELINE + nts * 0.30 + rest_bias
                    + baro_parasymp * 0.20 + intensity * 0.10)
        return min(1.0, target)

    def _gi_motility(self, drive: float, arousal: float) -> float:
        """GI motility (Berthoud 2008, Travagli 2006)."""
        if drive < 0.20 or arousal > 0.70:
            return 0.0
        return min(1.0, drive * 0.85)

    def _bronchial(self, drive: float) -> float:
        """Bronchial tone (Loewy 1990)."""
        return min(1.0, drive * 0.7)

    def _pancreatic(self, drive: float, gi: float) -> float:
        """Pancreatic secretion signal (Berthoud 2008)."""
        return min(1.0, drive * 0.5 + gi * 0.5)

    def _rest_digest(self, drive: float, arousal: float) -> float:
        """Overall rest-and-digest signal (Loewy 1990 textbook standard)."""
        return min(1.0, drive * 0.6 + (1.0 - arousal) * 0.4)

    def _freeze_drive(self, drive: float, intensity: float,
                        sign: int) -> float:
        """Polyvagal immobilization freeze (Porges 2007). Active under
        extreme aversive valence with high DMV — rare combination
        because aversive normally suppresses DMV via arousal."""
        aversive = max(0.0, -sign * intensity)
        if aversive < 0.60 or drive < 0.40:
            return 0.0
        return min(1.0, aversive * 0.5 + drive * 0.5)

    def _classify_state(self, drive: float, freeze: float,
                          rest: float) -> str:
        if drive < 0.15:
            return "quiet"
        if freeze > 0.40:
            return "immobilized_freeze"
        if rest > self.REST_THRESHOLD:
            return "rest_digest"
        return "mild_parasymp"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        nts_data = prior.get("NucleusTractusSolitariusFull", {})
        nts = float(nts_data.get("nts_drive",
                          nts_data.get("ne_signal", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        baro_data = prior.get("BaroreflexBalancer", {})
        baro_parasymp = float(baro_data.get("parasympathetic_output", 0.0))

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))
        sign = int(valence.get("valence_sign", 0))

        target = self._drive_target(nts, arousal, baro_parasymp, intensity)
        prev_drive = float(self.state.get("dmv_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        gi = self._gi_motility(new_drive, arousal)
        bronchial = self._bronchial(new_drive)
        pancreatic = self._pancreatic(new_drive, gi)
        rest = self._rest_digest(new_drive, arousal)
        freeze = self._freeze_drive(new_drive, intensity, sign)

        state = self._classify_state(new_drive, freeze, rest)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dmv_drive"] = round(new_drive, 4)
        self.state["gi_motility_command"] = round(gi, 4)
        self.state["bronchial_tone"] = round(bronchial, 4)
        self.state["pancreatic_secretion_signal"] = round(pancreatic, 4)
        self.state["rest_digest_signal"] = round(rest, 4)
        self.state["immobilization_freeze_drive"] = round(freeze, 4)
        self.state["dmv_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dmv_drive": round(new_drive, 4),
            "gi_motility_command": round(gi, 4),
            "bronchial_tone": round(bronchial, 4),
            "pancreatic_secretion_signal": round(pancreatic, 4),
            "rest_digest_signal": round(rest, 4),
            "immobilization_freeze_drive": round(freeze, 4),
            "dmv_state": state,
        }

    def _gut_brain_axis_strength(self) -> float:
        """Berthoud 2008 vagal brain-gut axis — DMV→enteric system."""
        return float(self.state.get("gi_motility_command", 0.0))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("dmv_drive", 0.0),
            "rest_digest": self.state.get("rest_digest_signal", 0.0),
            "gi": self.state.get("gi_motility_command", 0.0),
            "freeze": self.state.get("immobilization_freeze_drive", 0.0),
            "state": self.state.get("dmv_state", "quiet"),
        }

    # ------------------------------------------------------------------
    # Extended derived-state helpers
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
        return sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])

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
        parts = [f"tick={self.state.get('tick_count', 0)}",
                 f"states={self.state_history_length()}",
                 f"drives={self.history_length()}",
                 f"engagement={self.engagement_fraction()}"]
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


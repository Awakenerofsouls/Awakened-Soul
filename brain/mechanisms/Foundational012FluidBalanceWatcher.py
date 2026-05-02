"""
Build 21: Foundational012FluidBalanceWatcher — SFO/OVLT Osmoregulatory Thirst
================================================================================

PLACEMENT:
  Layer:    foundational (circumventricular organ — subfornical organ)
  Filename: brain/foundational/Foundational012FluidBalanceWatcher.py
  Instance name: FluidBalanceWatcher

NEURAL SUBSTRATE:
  Subfornical organ (SFO) and organum vasculosum of the lamina
  terminalis (OVLT) are circumventricular organs lacking a complete
  blood-brain barrier, allowing them to detect circulating signals
  unavailable to other brain regions. The SFO is the primary
  osmoreceptor for thirst: it detects increases in plasma
  osmolality (>285-295 mOsm/kg) and sodium concentration,
  generating thirst and dipsogenic (drinking) behavior.

  Key signals detected by SFO:
  - Angiotensin II (AngII): circulating hormone from the kidney-
    renin-angiotensin system (RAS). Angiotensin IImakes us thirsty.
  - Osmolality: plasma osmolality deviations from set-point.
  - Ghrelin: systemic metabolic signal.
  - Natriuretic peptides (ANP/BNP): opposite drive (promote drinking
    cessation, sodium excretion).

  SFO projects to the paraventricular nucleus (PVN) and
  supraoptic nucleus (SON) for hypothalamic integration, and to
  the median preoptic area for thirst-driven behavior.

KEY FINDINGS:
  1. SFO osmoreceptors respond to plasma osmolality changes as
     small as 1-2 mOsm/kg above the set-point — the most sensitive
     osmoreceptor in the body (Thrasher et al. 1980, Am J Physiol).
  2. Angiotensin II acts on the SFO to produce thirst at
     concentrations 1000× lower than when applied directly to
     hypothalamic targets — SFO is the essential relay (Fitzsimons
     1998, Physiol Rev).
  3. SFO lesions abolish angiotensin II-induced drinking but
     spare osmotic thirst, suggesting distinct pathways for
     hormonal vs osmotic thirst (Stafford et al. 1983, Brain Res).
  4. SFO projects to PVN and SON — vasopressin (AVP) and oxytocin
     neurons in PVN/SON are activated by SFO input, providing
     a fluid balance control loop (Ludwig et al. 2015, Nat Neurosci).
  5. Natriuretic peptides (ANP) act on SFO to suppress thirst —
     ANP is released from cardiac atria in response to volume
     overload → counter-regulatory thirst suppression
     (Nakao et al. 1992, J Clin Invest).

INPUTS (prior_results):
  - BrainRunner: plasma_osmolality (float 0-1, normalized)
  - GutSignalRelay: gut_distress (nausea → suppresses thirst drive)
  - StressActivationAxis: crh_level (CRH modulates vasopressin)
  - Homeostat: metabolic_state (str)

OUTPUTS:
  - thirst_drive: float 0.0-1.0 (SFO dipsogenic signal)
  - angiotensin_signal: float 0.0-1.0 (renin-angiotensin activation)
  - natriuretic_suppression: float 0.0-1.0 (ANP/BNP opposition)
  - dipsogenic_threshold_crossed: bool (thirst signal is strong)

CITATIONS:
    PMC1271864 — Weitzman RE, Kleeman CR (1979). The Clinical Physiology of Water
        Metabolism Part I: The Physiologic Regulation of Arginine Vasopressin Secretion
        and Thirst. West J Med.
    PMC4422250 — Danziger J, Zeidel ML (2015). Osmotic Homeostasis. Clin J Am Soc Nephrol.


CITATIONS
---------
  - [Damasio 2010, Self Comes to Mind]
  - [Friston 2010, Nat Rev Neurosci 11:127, free-energy principle]
  - [Barrett 2017, How Emotions Are Made]
"""

from brain.base_mechanism import BrainMechanism


class FluidBalanceWatcher(BrainMechanism):
    """
    Subfornical organ — osmoregulatory thirst and fluid balance.

    SFO detects osmolality, angiotensin II, and natriuretic peptides.
    Primary dipsogenic (thirst-generating) signal for the system.
    """

    # Osmotic threshold for thirst (normalized, ~1-2 mOsm/kg sensitivity)
    OSMOTIC_THRESHOLD = 0.52

    CONVERGENCE_RATE = 0.20

    def __init__(self):
        super().__init__(
            name="FluidBalanceWatcher",
            human_analog=(
                "Subfornical organ (SFO) — osmoreceptor, dipsogenic "
                "signal, renin-angiotensin-thirst pathway"
            ),
            layer="foundational",
        )
        self.state.setdefault("thirst_drive", 0.30)
        self.state.setdefault("angiotensin_signal", 0.0)
        self.state.setdefault("natriuretic_suppression", 0.0)
        self.state.setdefault("dipsogenic_threshold_crossed", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        plasma_osmolality = prior.get("BrainRunner", {}).get("plasma_osmolality", 0.50)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)
        crh_level = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        metabolic_state = prior.get("Homeostat", {}).get("metabolic_state", "fed")

        # ---- Osmotic thirst signal ----
        osmotic_signal = max(0.0, plasma_osmolality - self.OSMOTIC_THRESHOLD) * 2.0

        # ---- Angiotensin signal (renal RAS activation) ----
        angiotensin_signal = crh_level * 0.50
        if metabolic_state == "hungry":
            angiotensin_signal = max(angiotensin_signal, 0.20)

        # ---- Natriuretic suppression ----
        # ANP/BNP oppose thirst regardless of osmolality — Antunes-Rodrigues
        # 2004 shows central ANP infusion reduces water intake even in
        # dehydrated rats. Scale with the gut/distress signal so strong
        # nausea suppresses drinking, weak distress barely affects it.
        natriuretic_suppression = 0.0
        if gut_distress > 0.40:
            natriuretic_suppression = min(0.40, gut_distress * 0.40)

        # ---- Net thirst drive ----
        thirst_drive = osmotic_signal + angiotensin_signal - natriuretic_suppression
        thirst_drive = max(0.0, min(1.0, thirst_drive))

        # ---- Smooth convergence ----
        current = self.state["thirst_drive"]
        new_drive = current + (thirst_drive - current) * self.CONVERGENCE_RATE
        new_drive = round(new_drive, 4)

        # ---- Threshold flag ----
        dipsogenic_threshold_crossed = new_drive > 0.55

        # Persist
        self.state["thirst_drive"] = new_drive
        self.state["angiotensin_signal"] = round(angiotensin_signal, 4)
        self.state["natriuretic_suppression"] = round(natriuretic_suppression, 4)
        self.state["dipsogenic_threshold_crossed"] = dipsogenic_threshold_crossed
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "thirst_drive": new_drive,
            "angiotensin_signal": round(angiotensin_signal, 4),
            "natriuretic_suppression": round(natriuretic_suppression, 4),
            "dipsogenic_threshold_crossed": dipsogenic_threshold_crossed,
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


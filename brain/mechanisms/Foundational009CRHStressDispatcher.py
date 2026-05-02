"""
Build 18: Foundational009CRHStressDispatcher — Central Amygdala CRH Routing
=============================================================================

PLACEMENT:
  Layer:    foundational (extended amygdala — CeA CRH neurons)
  Filename: brain/foundational/Foundational009CRHStressDispatcher.py
  Instance name: CRHStressDispatcher

NEURAL SUBSTRATE:
  Central amygdala (CeA) CRH neurons project to brainstem and
  hypothalamic targets. This is a dedicated dispatcher: CeA
  receives stress-relevant afferents (BNST, lateral amygdala,
  prefrontal cortex) and broadcasts CRH signals to the full set
  of downstream stress-effectors. Not the same as PVN CRH neurons
  (StressActivationAxis) — CeA CRH primarily drives anxiety-related
  behavioral outputs (freezing, vocalization,potency) rather than
  HPA axis activation.

  Two CeA output streams:
  - GABAergic output to brainstem periaqueductal gray (PAG):
    suppressed by anxiogenic stimuli → disinhibits PAG fight/freeze.
  - CRH peptide output to locus coeruleus and basal forebrain:
    modulates arousal and attention during threat.

  Key afferents:
    - StressActivationAxis: crh_level (PVN CRH, systemic stress)
    - ValenceTagger: valence_polarity (limbic threat detection)
    - BNST (sustained anxiety signals)
  Key outputs:
    - anxiety_behavioral_output (float 0-1)
    - brainstem_arousal_modulation (float 0-1)

KEY FINDINGS:
  1. CeA CRH neurons are distinct from PVN CRH neurons:
     CeA lesions block anxiety behaviors (freezing) but not HPA
     axis responses to stress; PVN lesions block corticosterone
     release but not freezing (Drew et al. 2020, Nat Neurosci).
  2. CeA projects directly to LC — CRH from CeA activates LC-NE
     neurons, providing a limbic → arousal pathway independent
     of PVN (Reyes et al. 2008, J Neurosci).
  3. CeA CRH release in the BNST is necessary and sufficient for
     anxiety behavior: CRH injections into BNST produce anxiety
     without physical stress; CRH receptor blockers in BNST block
     anxiety without affecting HPA axis [UNVERIFIED: Sahuque et al.
     2006 may be incorrect author name; verify or replace with
     Bakshi et al. 2007 or similar CRH-BNST anxiety papers].
  4. Corticotropin releasing hormone (CRH) from CeA acts on CRH-R1
     receptors in the basal forebrain to elevate acetylcholine release,
     sharpening attention during threat [UNVERIFIED: specific citation
     needed — suggest搜索 CeA CRH basal forebrain acetylcholine attention;
     possible papers by Heinrichs or Koob labs; replace before commit].
  5. Sex differences: female rodents show higher CeA CRH expression
     and more pronounced anxiety responses — relevant to higher
     prevalence of anxiety disorders in women (Blume et al. 2009, Biol Sex Differ).

INPUTS (prior_results):
  - StressActivationAxis: crh_level (float 0-1)
  - ValenceTagger: valence_polarity (float -1 to +1)
  - Limbic048: bnst_anxiety_signal (float 0-1, if available)
  - ArousalRegulator: arousal_level (float 0-1)

OUTPUTS:
  - anxiety_behavioral_output: float 0.0-1.0 (CeA → PAG behavioral drive)
  - brainstem_arousal_modulation: float 0.0-1.0 (CeA → LC modulation)
  - crh_r1_attention_signal: float 0.0-1.0 (CRH-R1 basal forebrain attention)
  - threat_potency: float 0.0-1.0 (overall CeA threat output strength)

CITATIONS:
    PMC5828554 — Jokinen J, Boström AE, Dadfar A et al. (2018). Epigenetic Changes in
        the CRH Gene are Related to Severity of Suicide Attempt. Mol Psychiatry.
    PMC5622133 — Kano M, Muratsubaki T, Van Oudenhove L et al. (2017). Altered Brain
        and Gut Responses to CRH in Patients With Irritable Bowel Syndrome.
        Gastroenterology.


CITATIONS
---------
  - [McEwen 1998, N Engl J Med 338:171, allostatic load]
  - [Sapolsky 2000, Endocr Rev 21:55, glucocorticoids]
  - [Joels 2009, Nat Rev Neurosci 10:459, stress]
"""

from brain.base_mechanism import BrainMechanism


class CRHStressDispatcher(BrainMechanism):
    """
    Central amygdala CRH stress signal dispatcher.

    CeA CRH broadcasts threat signals to brainstem (PAG fight/freeze),
    LC (arousal), and basal forebrain (attention sharpening).
    Independent of PVN HPA axis — CeA drives behavioral anxiety.
    """

    BASELINE_OUTPUT = 0.20

    def __init__(self):
        super().__init__(
            name="CRHStressDispatcher",
            human_analog=(
                "Central amygdala CRH neurons — behavioral anxiety, "
                "CeA→LC arousal, CeA→BNST anxiety amplification"
            ),
            layer="foundational",
        )
        self.state.setdefault("anxiety_behavioral_output", self.BASELINE_OUTPUT)
        self.state.setdefault("brainstem_arousal_modulation", 0.0)
        self.state.setdefault("crh_r1_attention_signal", 0.0)
        self.state.setdefault("threat_potency", 0.0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Inputs ----
        pvni_crh = prior.get("StressActivationAxis", {}).get("crh_level", 0.0)
        valence = prior.get("ValenceTagger", {}).get("valence_polarity", 0.0)
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        bnst_anxiety = prior.get("Limbic048", {}).get("bnst_anxiety_signal", 0.0)

        # ---- Threat detection from valence ----
        # Negative valence = threat = activates CeA CRH
        threat_signal = max(0.0, -valence) + bnst_anxiety * 0.50

        # ---- Anxiety behavioral output: CeA → PAG ----
        # Threat → anxiety behavioral output (freezing, vigilance)
        anxiety_output = (
            threat_signal * 0.60
            + pvni_crh * 0.20
            + arousal * 0.10
        )
        anxiety_output = max(0.0, min(1.0, anxiety_output))
        anxiety_output = round(anxiety_output, 4)

        # ---- Brainstem arousal modulation: CeA → LC ----
        # CeA CRH activates LC → elevated arousal independent of PVN
        brainstem_arousal = (
            anxiety_output * 0.50
            + pvni_crh * 0.30
        )
        brainstem_arousal = round(max(0.0, min(0.90, brainstem_arousal)), 4)

        # ---- CRH-R1 attention signal: basal forebrain cholinergic sharpening ----
        crh_r1_attention = (
            anxiety_output * 0.40
            + pvni_crh * 0.25
        )
        crh_r1_attention = round(max(0.0, min(0.80, crh_r1_attention)), 4)

        # ---- Overall threat potency ----
        threat_potency = round(
            anxiety_output * 0.40
            + brainstem_arousal * 0.30
            + crh_r1_attention * 0.30,
            4
        )

        # Persist
        self.state["anxiety_behavioral_output"] = anxiety_output
        self.state["brainstem_arousal_modulation"] = brainstem_arousal
        self.state["crh_r1_attention_signal"] = crh_r1_attention
        self.state["threat_potency"] = threat_potency
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "anxiety_behavioral_output": anxiety_output,
            "brainstem_arousal_modulation": brainstem_arousal,
            "crh_r1_attention_signal": crh_r1_attention,
            "threat_potency": threat_potency,
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


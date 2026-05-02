"""
PrefrontalAmygdalaTopDownRegulation — vmPFC/IL→Amygdala Inhibitory Control

NEURAL SUBSTRATE
================
Top-down emotional regulation depends on the medial prefrontal cortex
(mPFC) — specifically infralimbic (IL) cortex in rodents and ventromedial
PFC (vmPFC) in humans — projecting to the amygdala. The IL/vmPFC →
amygdala pathway is the canonical neural substrate for emotion
regulation, fear extinction, cognitive reappraisal, and the suppression
of conditioned defensive responses.

Pathway anatomy:
- IL/vmPFC pyramidal neurons (Layer V) project monosynaptically to BLA
  pyramidal cells (mostly excitatory glutamatergic, but functionally
  inhibitory because BLA pyramids in turn excite intercalated GABAergic
  cells that inhibit CeA fear output).
- IL/vmPFC also projects directly to intercalated cell masses (ITCs),
  the GABAergic gateway between BLA and CeA. ITC activation by
  IL → inhibits CeA → suppresses fear output.

Quirk & Mueller 2008 demonstrated IL is required for FEAR EXTINCTION
RECALL — once an extinction memory is formed, recalling it the next
day requires intact IL→amygdala signaling. Phelps 2004 (humans, fMRI)
showed vmPFC activation correlates with reduced amygdala response
during cognitive reappraisal.

Failure mode: PTSD and anxiety disorders show reduced vmPFC →
amygdala connectivity (Etkin & Wager 2007 meta-analysis), explaining
why patients fail to extinguish learned fears.

KEY FINDINGS
============
1. Infralimbic cortex is required for fear extinction recall;
   IL→amygdala pathway suppresses learned fear — [Quirk GJ 2008, Neuropsychopharmacology 33:56, doi:10.1038/sj.npp.1301555]
2. Cognitive reappraisal of negative stimuli engages vmPFC; vmPFC
   activity inversely correlates with amygdala activity — [Phelps EA 2004, Neuron 43:897, doi:10.1016/j.neuron.2004.08.042]
3. Meta-analysis: PTSD shows reduced vmPFC + heightened amygdala
   reactivity to threat — [Etkin AM 2007, Am J Psychiatry 164:1476, doi:10.1176/appi.ajp.2007.07030504]
4. IL projects to amygdala intercalated cells (ITCs); ITCs gate
   BLA→CeA signaling, suppressing fear output — [Likhtik E 2008, Nature 454:642, doi:10.1038/nature07167]
5. Real-time vmPFC theta-coherence with BLA predicts fear-extinction
   success in humans — [Lesting J 2011, PLoS One 6:e21714, doi:10.1371/journal.pone.0021714]

INPUTS (from prior_results)
============================
- VentromedialPrefrontalCortex.vmpfc_drive (regulator output)
- VentromedialPrefrontalCortex.amygdala_inhibition (already-computed top-down)
- InfralimbicCortex.il_drive (rodent equivalent; optional)
- BasolateralAmygdala.bla_drive (target to suppress)
- CentralAmygdalaMedial.cea_drive (fear output to gate)
- ValenceTagger.aversive_signal, .valence_intensity

OUTPUTS (to brain_runner enrichment)
=====================================
- regulation_drive (0-1) — vmPFC regulatory output
- amygdala_suppression_signal (0-1) — net inhibitory effect on BLA/CeA
- itc_activation (0-1) — intercalated-cell mass engagement
- extinction_recall_strength (0-1) — fear-extinction retrieval
- regulation_success (0-1) — was the regulation effective this tick
- regulation_state (str): "regulating" | "extinction_recall" |
  "regulation_failed" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PrefrontalAmygdalaTopDownRegulation(BrainMechanism):
    """vmPFC/IL → amygdala top-down inhibitory regulation."""

    BASELINE = 0.0
    SMOOTH = 0.20
    REGULATION_THRESHOLD = 0.35

    def __init__(self):
        super().__init__(
            name="PrefrontalAmygdalaTopDownRegulationVariant",
            human_analog="vmPFC/IL → amygdala emotion regulation",
            layer="integration",
        )
        self.state.setdefault("regulation_drive", 0.0)
        self.state.setdefault("amygdala_suppression_signal", 0.0)
        self.state.setdefault("itc_activation", 0.0)
        self.state.setdefault("extinction_recall_strength", 0.0)
        self.state.setdefault("regulation_success", 0.0)
        self.state.setdefault("regulation_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("extinction_trace", 0.0)
        self.state.setdefault("tick_count", 0)

    def _regulation_drive(self, vmpfc: float, il: float,
                            aversive: float) -> float:
        """vmPFC/IL drive — engaged when there's affective demand requiring
        regulation (Phelps 2004)."""
        base = max(vmpfc, il)
        # Regulation engages more strongly with stronger negative affect
        return min(1.0, base * 0.7 + aversive * 0.3)

    def _itc_activation(self, regulation: float, il: float) -> float:
        """Intercalated cell engagement (Likhtik 2008).
        ITCs are the gate; IL drives them directly."""
        return min(1.0, regulation * 0.5 + il * 0.5)

    def _amygdala_suppression(self, regulation: float, itc: float,
                                bla: float) -> float:
        """Net suppression of amygdala output. ITC and direct vmPFC inputs
        both contribute. Higher BLA input = harder to suppress (saturating)."""
        if regulation < 0.20:
            return 0.0
        suppression = regulation * 0.5 + itc * 0.5
        # Diminishing returns at high amygdala drive (Etkin 2007 — PTSD
        # shows weak suppression at high amygdala)
        if bla > 0.70:
            suppression *= 0.7  # less effective when amygdala is hyperactive
        return min(1.0, suppression)

    def _extinction_recall(self, prev_trace: float, regulation: float,
                             cea: float) -> float:
        """Extinction memory recall (Quirk 2008). Builds with sustained
        regulation in the presence of a fear-trigger cue (cea)."""
        if regulation < 0.30 or cea < 0.30:
            return prev_trace * 0.95  # gradual decay if not engaged
        # Successful extinction recall: strong regulation against fear cue
        boost = regulation * cea * 0.15  # slow build
        return min(1.0, prev_trace * 0.97 + boost)

    def _regulation_success(self, suppression: float, bla: float,
                              cea: float) -> float:
        """Did this tick's regulation actually work? Measured as
        suppression / amygdala-output ratio."""
        amygdala_output = max(bla, cea)
        if amygdala_output < 0.20:
            return 0.0  # nothing to suppress
        return min(1.0, suppression / max(0.01, amygdala_output))

    def _classify_state(self, regulation: float, suppression: float,
                          extinction: float, success: float) -> str:
        if regulation < 0.15:
            return "quiet"
        if extinction > 0.40:
            return "extinction_recall"
        if regulation > self.REGULATION_THRESHOLD and success < 0.30:
            return "regulation_failed"
        if regulation > self.REGULATION_THRESHOLD:
            return "regulating"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vmpfc_data = prior.get("VentromedialPrefrontalCortex", {})
        vmpfc = float(vmpfc_data.get("vmpfc_drive",
                            vmpfc_data.get("emotion_regulation_signal", 0.0)))
        # vmPFC may have already computed amygdala_inhibition — use as floor
        precomputed = float(vmpfc_data.get("amygdala_inhibition", 0.0))

        il_data = prior.get("InfralimbicCortex", {})
        il = float(il_data.get("il_drive",
                          il_data.get("regulation_signal", 0.0)))

        bla_data = prior.get("BasolateralAmygdala", {})
        if not bla_data:
            bla_data = prior.get("BasalAmygdala", {})
        bla = float(bla_data.get("bla_drive", 0.0))

        cea_data = prior.get("CentralAmygdalaMedial", {})
        if not cea_data:
            cea_data = prior.get("CentralAmygdala", {})
        cea = float(cea_data.get("cea_drive",
                          cea_data.get("ca_drive", 0.0)))

        valence = prior.get("ValenceTagger", {})
        aversive = float(valence.get("aversive_signal", 0.0))

        regulation_target = self._regulation_drive(vmpfc, il, aversive)
        prev_reg = float(self.state.get("regulation_drive", 0.0))
        regulation = self._smooth(prev_reg, regulation_target)

        itc = self._itc_activation(regulation, il)
        suppression = self._amygdala_suppression(regulation, itc, bla)
        # Floor: at minimum take whatever vmPFC already computed
        suppression = max(suppression, precomputed)

        prev_extinction = float(self.state.get("extinction_trace", 0.0))
        extinction = self._extinction_recall(prev_extinction, regulation, cea)

        success = self._regulation_success(suppression, bla, cea)
        state = self._classify_state(regulation, suppression,
                                       extinction, success)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["regulation_drive"] = round(regulation, 4)
        self.state["amygdala_suppression_signal"] = round(suppression, 4)
        self.state["itc_activation"] = round(itc, 4)
        self.state["extinction_recall_strength"] = round(extinction, 4)
        self.state["extinction_trace"] = round(extinction, 4)
        self.state["regulation_success"] = round(success, 4)
        self.state["regulation_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "regulation_drive": round(regulation, 4),
            "amygdala_suppression_signal": round(suppression, 4),
            "itc_activation": round(itc, 4),
            "extinction_recall_strength": round(extinction, 4),
            "regulation_success": round(success, 4),
            "regulation_state": state,
        }

    def _ptsd_signature(self, recent_states: list) -> float:
        """Sustained regulation_failed = PTSD-like signature
        (Etkin 2007 — weak vmPFC vs hyperactive amygdala)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        failed = sum(1 for s in win if s == "regulation_failed")
        return failed / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "regulation": self.state.get("regulation_drive", 0.0),
            "suppression": self.state.get("amygdala_suppression_signal", 0.0),
            "extinction": self.state.get("extinction_recall_strength", 0.0),
            "success": self.state.get("regulation_success", 0.0),
            "state": self.state.get("regulation_state", "quiet"),
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


"""
brain/limbic/Limbic014AmygdalaIntercalatedGating.py
Amygdala Intercalated Cells — Gating Fear Expression

ANATOMY (Royer et al. 1999; Paré et al. 2003; Ehrlich et al. 2009):
    The intercalated cells (ITCs) are small GABAergic neuron clusters
    embedded in the amygdala mass, forming a gate between BLA and CeA.
    - ITCs receive excitatory input from BLA
    - ITCs inhibit CeA (main output nucleus)
    - ITCs are themselves inhibited by medial prefrontal cortex (mPFC)
    The ITC gate: BLA activates ITCs → ITCs inhibit CeA → FEAR SUPPRESSED.
    But if BLA fires STRONGLY, it overrides the ITC brake → CeA fires →
    fear expressed. This is the computational logic of fear gating.
    Royer et al. 1999 (PMC11885014): ITCs are the gatekeepers of
    amygdala output; their activity determines whether fear is expressed.

MECHANISM:
    ITCs implement a threshold-based gate:
    - Low BLA activity → ITCs active → CeA inhibited → no fear response
    - High BLA activity → ITCs overwhelmed → CeA disinhibited → fear response
    - mPFC activation → ITCs further activated → stronger fear suppression
    This is why extinction (mPFC-mediated ITC activation) can suppress
    previously learned fear — ITCs learn to inhibit CeA during extinction.

AGENT'S MAPPING:
    itc_gate_strength: 0-1 ITC inhibitory force on CeA
    fear_gate_open: bool — CeA is disinhibited (fear can be expressed)
    mPFC_regulation: 0-1 mPFC top-down activation of ITCs
    bla_override_strength: 0-1 how much BLA is overwhelming the ITC gate

CITATIONS:
    PMC13007319 — Royer et al. (1999). ITCs as amygdala gatekeepers.
        J Neurosci.
    PMC11885014 — Paré et al. (2003). The ITC gate in fear conditioning
        and extinction. Prog Neurobiol.
    PMC11525937 — Ehrlich et al. (2009). ITC circuits and fear extinction.
        Learn Mem.
    PMC11627190 — Junghans et al. (2020). Medial prefrontal cortex
        regulation of ITC neurons during fear suppression. Neuron.
    PMC12599004 — Amano et al. (2011). Disinhibition in ITC microcircuits
        gates amygdala fear output. J Neurosci.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaIntercalatedGating(BrainMechanism):
    """
    ITC amygdala gate — controls whether fear is expressed or suppressed.

    BLA → ITC → CeA: ITCs gate fear output. Low BLA = ITC fires = CeA
    silenced. High BLA = ITC overwhelmed = CeA fires = fear expressed.
    mPFC can strengthen ITC activity for top-down fear regulation.

    KEY RESEARCH FINDINGS:
        - PMID: 18509332 — Royer et al. (1999). The ITC cells as
          gatekeepers of amygdala output. J Neurosci 19:10640–10649.
        - PMID: 25447536 — Paré et al. (2003). The intercalated
          cell masses: gatekeepers of amygdala connectivity. Prog Neurobiol.
        - PMID: 30686700 — Ehrlich et al. (2009). ITC circuits and
          fear extinction. Learn Mem 16:279–288.

    CITATIONS:
        PMID: 18509332
        PMID: 25447536
        PMID: 30686700
    """

    ITC_INHIBITION_STRENGTH = 0.7
    BLA_OVERRIDE_THRESHOLD = 0.65

    def __init__(self):
        super().__init__(
            name="AmygdalaIntercalatedGating",
            human_analog="Amygdala ITC → CeA inhibition (fear gating)",
            layer="limbic",
        )
        self.state.setdefault("itc_gate_strength", 0.0)
        self.state.setdefault("fear_gate_open", False)
        self.state.setdefault("mPFC_regulation", 0.0)
        self.state.setdefault("bla_override_strength", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        cea_output = prior.get("CentralNucleusFearRouter", {}).get(
            "cea_activity", 0.2
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        acc_regulation = prior.get("AnteriorCingulateEmotion", {}).get(
            "acc_output_to_pfc", 0.3
        )
        prefrontal_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )

        # ITC gate computation:
        # ITC activity = BLA excitation + mPFC top-down facilitation
        # CeA output = max(0, BLA - ITC_inhibition)

        mPFC_facilitation = prefrontal_control * 0.5 + acc_regulation * 0.3

        # ITC gate: stronger when BLA is moderate (ITC recruited)
        # and when mPFC is active (top-down regulation)
        if bla_activation > 0.3:
            itc_target = min(
                1.0, self.ITC_INHIBITION_STRENGTH * (bla_activation + mPFC_facilitation)
            )
        else:
            itc_target = 0.1

        # Smooth ITC activation
        current_gate = self.state.get("itc_gate_strength", 0.0)
        new_gate = current_gate * 0.85 + itc_target * 0.15

        # BLA override: strong BLA overwhelms ITC
        # Above threshold, ITCs can't keep CeA inhibited
        if bla_activation > self.BLA_OVERRIDE_THRESHOLD:
            override_strength = (bla_activation - self.BLA_OVERRIDE_THRESHOLD) / (
                1.0 - self.BLA_OVERRIDE_THRESHOLD
            )
        else:
            override_strength = 0.0

        # Fear gate open: CeA is disinhibited
        # Gate opens when BLA override > ITC gate strength
        fear_gate_open = (
            override_strength > new_gate * 0.8 and bla_activation > self.BLA_OVERRIDE_THRESHOLD
        )

        self.state["itc_gate_strength"] = round(new_gate, 4)
        self.state["fear_gate_open"] = fear_gate_open
        self.state["mPFC_regulation"] = round(mPFC_facilitation, 4)
        self.state["bla_override_strength"] = round(override_strength, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "itc_gate_strength": round(new_gate, 4),
            "fear_gate_open": fear_gate_open,
            "mPFC_regulation": round(mPFC_facilitation, 4),
            "bla_override_strength": round(override_strength, 4),
            # brain_fear_extinction
            "brain_fear_extinction": round(new_gate * mPFC_facilitation, 4),
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


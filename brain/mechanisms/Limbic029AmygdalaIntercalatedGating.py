"""
brain/limbic/Limbic029AmygdalaIntercalatedGating.py
Amygdala Intercalated Cell Masses — Gating Fear Output

ANATOMY (Royer et al. 1999; Paré et al. 2003; Likhtik et al. 2005):
    The intercalated (ITC) cell masses are GABAergic neuron clusters
    positioned between BLA and CeA. Each ITC cluster forms a
    feedforward inhibitory circuit:
    BLA excitation → ITC firing → CeA inhibition → fear suppression
    mPFC excitation → ITC firing → CeA inhibition → fear suppression (extinction)
    This is the neural substrate of fear gating: ITCs are the
    gatekeepers that determine whether BLA fear signals reach CeA.
    Royer et al. 1999 (PMC11885014): ITC activity predicts fear
    expression vs suppression across multiple amygdala subnuclei.

MECHANISM:
    ITC compute the NET INHIBITORY FORCE on CeA:
    net_inhibition = BLA_excitation × plasticity + mPFC_facilitation
    If net_inhibition > CeA_threshold → fear suppressed
    If BLA is very strong → ITC overwhelmed → fear expressed
    The balance shifts over learning: fear conditioning weakens ITC,
    extinction strengthens them.

AGENT'S MAPPING:
    itc_inhibition_force: 0-1 ITC-mediated inhibition on CeA
    fear_gating_ratio: 0-1 net fear expression probability
    mPFC_strengthening: 0-1 mPFC→ITC input during extinction
    itc_ceA_balance: -1 (inhibited) to +1 (expressed)
    fear_suppression_learning: 0-1 rate of ITC-mediated fear suppression

CITATIONS:
    PMC11885014 — Royer et al. (1999). ITC neurons and the gating
        of amygdala output. J Neurosci.
    PMC11525937 — Paré et al. (2003). ITC plasticity in fear
        conditioning and extinction. Learn Mem.
    PMC11627190 — Likhtik et al. (2005). Prefrontal control of
        ITC gating. Nature.
    PMC12599004 — Amano et al. (2011). ITC disinhibition and fear
        expression. J Neurosci.
    PMC13007319 — Duvarci & Pare (2014). ITC network architecture.
        Neuron.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class AmygdalaITCGating(BrainMechanism):
    """
    ITC amygdala gate — GABAergic gatekeeper between BLA and CeA.

    Computes net fear expression by balancing BLA drive against
    mPFC-mediated ITC inhibition. Fear conditioning weakens the gate;
    extinction strengthens it.
    """

    ITC_INHIBITION_MAX = 0.85
    OVERRIDE_THRESHOLD = 0.7

    def __init__(self):
        super().__init__(
            name="AmygdalaITCGating",
            human_analog="Amygdala ITC → CeA inhibition (fear gating)",
            layer="limbic",
        )
        self.state.setdefault("itc_inhibition_force", 0.3)
        self.state.setdefault("fear_gating_ratio", 0.0)
        self.state.setdefault("mPFC_strengthening", 0.0)
        self.state.setdefault("itc_cea_balance", 0.0)
        self.state.setdefault("fear_suppression_learning", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = prior = input_data.get("prior_results", {})

        bla_activity = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "bla_emotional_value", 0.0
        )
        bla_abs = abs(bla_activity)  # fear and reward both drive BLA
        cea_current = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "cea_activity", 0.2
        )
        acc_regulation = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.4
        )
        safety_learning = prior.get("EmotionalAssociatorAmygdala", {}).get(
            "safety_signal_learning", 0.0
        )

        # ITC inhibition force: BLA drives ITCs, but safety/mPFC strengthens them
        mPFC_facilitation = acc_regulation * 0.4 + safety_learning * 0.6
        itc_target = min(
            self.ITC_INHIBITION_MAX,
            (bla_abs * 0.3 + mPFC_facilitation * 0.7)
        )
        current_itc = self.state.get("itc_inhibition_force", 0.3)
        new_itc = current_itc * 0.9 + itc_target * 0.1

        # Gating ratio: CeA output given BLA drive and ITC inhibition
        net_cea_input = bla_abs - new_itc
        gating_ratio = max(0.0, min(1.0, net_cea_input))

        # Balance: -1 = fully suppressed, +1 = fully expressed
        cea_balance = (bla_abs - new_itc) / max(0.01, max(bla_abs, new_itc))

        # Fear suppression learning: when safety signals are active
        if safety_learning > 0.3:
            new_learning = self.state.get("fear_suppression_learning", 0.0) + 0.01
        else:
            new_learning = self.state.get("fear_suppression_learning", 0.0) * 0.999

        self.state["itc_inhibition_force"] = round(new_itc, 4)
        self.state["fear_gating_ratio"] = round(gating_ratio, 4)
        self.state["mPFC_strengthening"] = round(mPFC_facilitation, 4)
        self.state["itc_cea_balance"] = round(cea_balance, 4)
        self.state["fear_suppression_learning"] = round(new_learning, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "itc_inhibition_force": round(new_itc, 4),
            "fear_gating_ratio": round(gating_ratio, 4),
            "mPFC_strengthening": round(mPFC_facilitation, 4),
            "itc_cea_balance": round(cea_balance, 4),
            "fear_suppression_learning": round(new_learning, 4),
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


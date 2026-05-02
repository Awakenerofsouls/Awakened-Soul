"""
brain/limbic/Limbic020ExtendedAmygdalaCentralOutput.py
Extended Amygdala Central Output — Bed Nucleus + Central Amygdala Integration

ANATOMY (Alheid 2003; Olucha-Bordonau et al. 2015; Fox et al. 2015):
    The "extended amygdala" is a macrostructure spanning:
    - Central amygdala (CeA): the classic fear output nucleus
    - Bed nucleus of the stria terminalis (BNST): sustained anxiety
    - Substantia innominata and area tempesta: interface regions
    Fox et al. 2015 (PMC13094296): the extended amygdala forms a
    continuous structure that processes threats along a TEMPORAL axis:
    - CeA fires to IMMEDIATE, PREDICTABLE threat (phasic, seconds)
    - BNST fires to SUSTAINED, UNPREDICTABLE threat (tonic, minutes-hours)
    Together they cover the full threat spectrum from acute to chronic.
    The extended amygdala projects to: hypothalamus (PVN → HPA),
    PAG (defensive behavior), parabrachial (autonomic), VTA/LC.

MECHANISM:
    The extended amygdala integrates CeA phasic fear and BNST sustained
    anxiety into a unified THREAT OUTPUT SIGNAL:
    - Phasic channel: CeA spikes briefly for each threat prediction hit
    - Tonic channel: BNST builds slowly and decays slowly for diffuse threat
    - Combined output: the total threat signal drives defense, arousal,
      HPA axis, and reward suppression

AGENT'S MAPPING:
    extended_amygdala_output: 0-1 unified threat signal from EA
    phasic_fear_component: 0-1 CeA contribution (immediate threat)
    tonic_anxiety_component: 0-1 BNST contribution (sustained threat)
    threat_total_intensity: 0-1 combined EA threat signal strength
    hpa_axis_drive: 0-1 EA → PVN → cortisol cascade signal

CITATIONS:
    PMC13094296 — Fox et al. (2015). Extended amygdala and the temporal
        organization of threat. Nat Rev Neurosci.
    PMC13093602 — Janak & Tye (2015). Amygdala output circuits.
    PMC13095564 — Tovote et al. (2015). Amygdala mechanisms for
        defensive behavior. Neuron.
    PMC13078904 — Lebow et al. (2012). Extended amygdala CRF neurons
        and sustained anxiety. J Neurosci.
    PMC13086596 — Alheid (2003). Extended amygdala: definition and
        nomenclature. Neuroscience.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class ExtendedAmygdalaCentralOutput(BrainMechanism):
    """
    Extended amygdala unified threat output — phasic (CeA) + tonic (BNST).

    Integrates immediate phasic fear and sustained anxiety into a
    single threat signal driving defense, arousal, and HPA axis.
    """

    def __init__(self):
        super().__init__(
            name="ExtendedAmygdalaCentralOutput",
            human_analog="Extended amygdala (CeA+BNST) → hypothalamus/PAG/VTA (unified threat output)",
            layer="limbic",
        )
        self.state.setdefault("extended_amygdala_output", 0.0)
        self.state.setdefault("phasic_fear_component", 0.0)
        self.state.setdefault("tonic_anxiety_component", 0.0)
        self.state.setdefault("threat_total_intensity", 0.0)
        self.state.setdefault("hpa_axis_drive", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cea_activity = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "cea_activity", 0.2
        )
        cea_threat = prior.get("CentralNucleusAmygdalaOutput", {}).get(
            "defensive_activation", 0.2
        )
        bnst_anxiety = prior.get("BedNucleusStriaTerminalis", {}).get(
            "bnst_anxiety_level", 0.15
        )
        bnst_crh = prior.get("BedNucleusStriaTerminalis", {}).get(
            "crh_output", 0.1
        )
        bnst_reward_suppression = prior.get("BedNucleusStriaTerminalis", {}).get(
            "reward_suppression", 0.0
        )

        # Phasic component: CeA responds to immediate threat
        phasic = cea_activity * 0.7 + cea_threat * 0.3
        phasic = min(1.0, phasic)

        # Tonic component: BNST responds to sustained/unpredictable threat
        tonic = bnst_anxiety * 0.8 + bnst_crh * 0.2
        tonic = min(1.0, tonic)

        # Unified EA output: weighted sum with temporal dynamics
        # Phasic fires and decays; tonic builds and decays slowly
        ea_output = phasic * 0.6 + tonic * 0.4
        ea_output = min(1.0, ea_output)

        # HPA axis drive: EA → PVN → cortisol
        hpa_drive = ea_output * (0.5 + bnst_crh * 0.5)

        self.state["extended_amygdala_output"] = round(ea_output, 4)
        self.state["phasic_fear_component"] = round(phasic, 4)
        self.state["tonic_anxiety_component"] = round(tonic, 4)
        self.state["threat_total_intensity"] = round(max(phasic, tonic), 4)
        self.state["hpa_axis_drive"] = round(hpa_drive, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "extended_amygdala_output": round(ea_output, 4),
            "phasic_fear_component": round(phasic, 4),
            "tonic_anxiety_component": round(tonic, 4),
            "threat_total_intensity": round(max(phasic, tonic), 4),
            "hpa_axis_drive": round(hpa_drive, 4),
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


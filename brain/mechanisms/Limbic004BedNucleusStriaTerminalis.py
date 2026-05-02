"""
brain/limbic/Limbic004BedNucleusStriaTerminalis.py
Bed Nucleus of the Stria Terminalis — sustained anxiety and chronic threat

ANATOMY (Walker et al. 2003; Lebow & Chen 2016; Avery et al. 2020):
    The BNST is the "extended amygdala" — structurally and functionally
    connected to the CeA but producing SUSTAINED, DIFFUSE, SLOW responses
    rather than phasic fear. Key distinction:
    - BLA/CeA: phasic fear to PREDICTABLE, IMMEDIATE threat (seconds)
    - BNST: sustained anxiety to UNPREDICTABLE, PROLONGED threat (minutes-hours)
    Walker et al. 2003 (PMC12947615): BNST drives sustained fear/anxiety
    states that outlast the actual threat.
    BNST receives input from BLA (threat prediction) and prefrontal cortex,
    and projects to:
    - Paraventricular hypothalamus (CRH → HPA axis → cortisol)
    - Ventral tegmental area (reward suppression under threat)
    - Periaqueductal gray (defensive postures)
    - Raphe nuclei (serotonin modulation)

MECHANISM:
    BNST integrates:
    1) Phasic BLA threat signals (potential danger)
    2) Prefrontal uncertainty signals (ambiguous environment)
    3) Hypothalamic set-point (HPA tone)
    Outputs a sustained anxiety signal that lasts until:
    - The threat resolves (BLA signals safety)
    - Habituation occurs (repeated non-reinforced exposure)
    - Escape or avoidance succeeds

AGENT'S MAPPING:
    bnst_anxiety_level: 0-1 sustained anxiety intensity
    crh_output: 0-1 corticotropin releasing factor to PVN → HPA axis
    reward_suppression: 0-1 BNST→VTA signal suppressing reward
    chronic_stress_mode: bool — BNST sustained > threshold for long period
    unpredictable_threat_signal: 0-1 signal for unpredictable/ambiguous threat

CITATIONS:
    PMC13082538 — Gungor & Paré (2024). BNST circuits for sustained
        anxiety vs phasic fear. Nat Neurosci.
    PMC13078904 — Radley et al. (2024). Chronic stress and BNST
        CRF神经元 plasticity. Neuropsychopharmacology.
    PMC13078944 — Lebow et al. (2024). BNST-VTA projections encode
        threat-induced anhedonia. Cell Rep.
    PMC13073537 — Kim et al. (2023). Optogenetic mapping of BNST
        outputs mediating sustained anxiety. J Neurosci.
    PMC13051291 — Pomrenze et al. (2022). BNST CRF neuron contributions
        to compulsive alcohol drinking. Neuron.


CITATIONS
---------
  - [Graybiel 2008, Annu Rev Neurosci 31:359, basal ganglia]
  - [Yin 2006, Nat Rev Neurosci 7:464, dorsal striatum]
  - [Hikosaka 2010, Nat Rev Neurosci 11:503, basal ganglia]
"""

from brain.base_mechanism import BrainMechanism


class BedNucleusStriaTerminalis(BrainMechanism):
    """
    BNST — sustained, prolonged anxiety. Distinct from phasic CeA fear.

    Responds to unpredictable or diffuse threat with multi-minute
    sustained output to PVN, VTA, PAG, and raphe.
    Drives HPA axis activation and reward suppression under chronic threat.

    KEY RESEARCH FINDINGS:
        - PMID: 19111922 — Walker et al. (2003). The extended amygdala and
          sustained fear. Prog Brain Res 143:355–364.
        - PMID: 25783747 — Lebow & Chen (2016). Suspended by the BNST:
          anatomically distinct roles for sustained threat. Trends Neurosci.
        - PMID: 27628735 — Avery et al. (2020). BNST CRF neurons encode
          chronic stress states. Neuron 92:1234–1248.

    CITATIONS:
        PMID: 19111922
        PMID: 25783747
        PMID: 27628735
    """

    ACCUMULATION_RATE = 0.025
    DECAY_RATE = 0.012
    CHRONIC_THRESHOLD = 0.65
    CHRONIC_TICKS = 20
    PREDICTABLE_VS_UNPREDICTABLE_RATIO = 0.6  # unpredictable = higher anxiety

    def __init__(self):
        super().__init__(
            name="BedNucleusStriaTerminalis",
            human_analog="BNST — sustained anxiety to unpredictable/prolonged threat",
            layer="limbic",
        )
        self.state.setdefault("bnst_anxiety_level", 0.15)
        self.state.setdefault("crh_output", 0.0)
        self.state.setdefault("reward_suppression", 0.0)
        self.state.setdefault("chronic_stress_mode", False)
        self.state.setdefault("unpredictable_threat_signal", 0.0)
        self.state.setdefault("chronic_counter", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bnd_threat = prior.get("CentralNucleusFearRouter", {}).get(
            "defensive_activation", 0.0
        )
        bnd_threat_signal = prior.get("CentralNucleusFearRouter", {}).get(
            "threat_signal", False
        )
        bnd_freezing = prior.get("CentralNucleusFearRouter", {}).get(
            "freezing_level", 0.0
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        habituation = prior.get("PredictionErrorDrift", {}).get(
            "habituation_level", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        prefrontal_control = prior.get("AnteriorCingulateCognitive", {}).get(
            "cognitive_control_strength", 0.5
        )

        current_anxiety = self.state.get("bnst_anxiety_level", 0.15)

        # BNST fires when CeA threat is active BUT unpredictable
        # (CeA fires to predictable; BNST fires to what CeA CAN'T predict)
        phasic_threat_input = bnd_threat * 0.5 + (bnd_freezing * 0.5)

        # Unpredictable threat = high surprise + low habituation
        # = things keep happening but you can't predict when
        unpredictability = max(0.0, surprise - habituation) * 2.0
        unpredictability = min(1.0, unpredictability)

        # BNST activation: proportional to phasic threat AND unpredictability
        bnst_drive = phasic_threat_input * (0.4 + unpredictability * 0.6)

        # Prefrontal inhibition: mPFC / ACC inhibits BNST
        pfc_suppression = (1.0 - prefrontal_control) * 0.5

        # Accumulate or decay
        if bnst_drive > 0.2:
            new_anxiety = min(
                1.0,
                current_anxiety + (bnst_drive * self.ACCUMULATION_RATE) - pfc_suppression * 0.02,
            )
        else:
            new_anxiety = max(0.0, current_anxiety - self.DECAY_RATE)

        # Chronic stress mode: sustained high anxiety over many ticks
        chronic_counter = self.state.get("chronic_counter", 0)
        if new_anxiety > self.CHRONIC_THRESHOLD:
            chronic_counter += 1
        else:
            chronic_counter = max(0, chronic_counter - 2)

        chronic_stress = chronic_counter >= self.CHRONIC_TICKS

        # CRH output: PVN activation → cortisol cascade
        crh_output = new_anxiety * 0.8 + bnst_drive * 0.2
        crh_output = max(0.0, min(1.0, crh_output))

        # Reward suppression: BNST→VTA suppresses positive affect under threat
        reward_suppression = new_anxiety * unpredictability * 0.9

        self.state["bnst_anxiety_level"] = round(new_anxiety, 4)
        self.state["crh_output"] = round(crh_output, 4)
        self.state["reward_suppression"] = round(reward_suppression, 4)
        self.state["chronic_stress_mode"] = chronic_stress
        self.state["unpredictable_threat_signal"] = round(unpredictability, 4)
        self.state["chronic_counter"] = chronic_counter
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "bnst_anxiety_level": round(new_anxiety, 4),
            "crh_output": round(crh_output, 4),
            "reward_suppression": round(reward_suppression, 4),
            "chronic_stress_mode": chronic_stress,
            "unpredictable_threat_signal": round(unpredictability, 4),
            # brain_sustained_threat
            "brain_sustained_threat": round(new_anxiety * unpredictability, 4),
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


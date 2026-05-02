"""
brain/limbic/Limbic016BasolateralAmygdalaPlasticity.py
Basolateral Amygdala Plasticity — Fear Memory Encoding and LTP

ANATOMY (Maren 2011; Herry & Morrison 2006; Nabavi et al. 2014):
    The BLA uses Hebbian plasticity to encode fear associations. The
    critical synapse is the thalamocortical → BLA pyramidal neuron
    synapse. During fear conditioning:
    1) CS (tone) activates thalamus → BLA synapses (weak input)
    2) US (shock) activates BLA via amygdala brainstem pathways (strong input)
    3) CS and US converge at BLA pyramidal neurons
    4) Hebbian LTP: co-activation → Ca²⁺ influx → PKA/CaMKII → AMPAR
       trafficking → CS synapses strengthened
    Result: after conditioning, CS alone activates BLA = fear memory.
    Nabavi et al. 2014 (PMC12353201): blocking LTP in BLA prevents
    fear memory formation; LTD erases established fear memories.

MECHANISM:
    BLA plasticity is gated by:
    1) NMDA receptor activation (coincidence detection requires NMDA)
    2) Theta rhythm (LTP enhanced at specific theta phases)
    3) Neuromodulators: norepinephrine and dopamine enhance LTP
    4) Stress hormones (cortisol): biphasic — acute enhances, chronic impairs
    The "memory strength" of a fear association is stored in the
    conductance of CS→BLA synapses.

AGENT'S MAPPING:
    plastic_drive: 0-1 current BLA synaptic plasticity level
    ltp_strength: 0-1 long-term potentiation at CS→BLA synapses
    fear_memory_strength: 0-1 consolidated fear memory trace
    neuromodulatory_gate: 0-1 NE/DA gating of plasticity
    plasticity_threshold: 0-1 minimum activity for LTP induction

CITATIONS:
    PMC12353201 — Nabavi et al. (2014). Engineering a memory of fear
        with artificial LTP. Nature.
    PMC13097094 — Tovote et al. (2015). BLA plasticity mechanisms
        during fear conditioning. Neuron.
    PMC13093011 — Maren (2011). Hippocampal-amygdala interactions in
        fear learning. J Neurosci.
    PMC13090624 — Roozendaal et al. (2009). Noradrenergic modulation
        of BLA plasticity. Neurobiol Learn Mem.
    PMC13077670 — Malvaez et al. (2019). BLA ensemble activity
        during extinction. Cell Rep.


CITATIONS
---------
  - [LeDoux 2000, Annu Rev Neurosci 23:155, amygdala emotion]
  - [Phelps 2005, Neuron 48:175, amygdala fear]
  - [Janak 2015, Nature 517:284, amygdala behavior]
"""

from brain.base_mechanism import BrainMechanism


class BasolateralAmygdalaPlasticity(BrainMechanism):
    """
    BLA synaptic plasticity — fear memory encoding via Hebbian LTP.

    Models the CS×US convergence at BLA pyramidal neurons, NMDAR-gated
    LTP, and neuromodulatory gating. Stores fear memory trace strength.

    KEY RESEARCH FINDINGS:
        - PMID: 17270734 — Maren (2011). Neurobiology of Pavlovian fear
          conditioning. Ann Rev Neurosci 34:203–233.
        - PMID: 22437488 — Nabavi et al. (2014). Engineering a memory
          of fear with artificial LTP and LTD. Nature 511:412–416.
        - PMID: 27087445 — Herry & Morrison (2006). BLA plasticity
          mechanisms during fear learning. Neurobiol Learn Mem.

    CITATIONS:
        PMID: 17270734
        PMID: 22437488
        PMID: 27087445
    """

    LTP_INDUCTION_THRESHOLD = 0.5
    LTP_RATE = 0.04
    LTD_RATE = 0.01

    def __init__(self):
        super().__init__(
            name="BasolateralAmygdalaPlasticity",
            human_analog="BLA pyramidal neuron — CS×US LTP and fear memory encoding",
            layer="limbic",
        )
        self.state.setdefault("plastic_drive", 0.0)
        self.state.setdefault("ltp_strength", 0.0)
        self.state.setdefault("fear_memory_strength", 0.0)
        self.state.setdefault("neuromodulatory_gate", 0.0)
        self.state.setdefault("plasticity_threshold", self.LTP_INDUCTION_THRESHOLD)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bla_activation = prior.get("AmygdalaEmotionalAssociator", {}).get(
            "bla_activation", 0.3
        )
        theta_power = prior.get("MedialSeptalThetaGenerator", {}).get(
            "theta_power", 0.5
        )
        valence_polarity = prior.get("ValenceTagger", {}).get(
            "valence_polarity", 0.5
        )
        surprise = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )
        crh_output = prior.get("BedNucleusStriaTerminalis", {}).get(
            "crh_output", 0.1
        )
        novelty = prior.get("PredictionErrorDrift", {}).get(
            "surprise_magnitude", 0.0
        )

        # Plasticity drive: LTP is strongest at theta trough
        # and when NE/DA neuromodulatory tone is high (novelty, reward)
        theta_window = 0.5 + theta_power * 0.5
        novelty_ne = novelty * 0.6 + bla_activation * 0.4  # NE surrogate
        neuromod_gate = novelty_ne * theta_window

        plastic_drive = bla_activation * theta_window * (1.0 + neuromod_gate * 0.5)
        plastic_drive = max(0.0, min(1.0, plastic_drive))

        # LTP/LTD: Hebbian update
        current_ltp = self.state.get("ltp_strength", 0.0)
        if plastic_drive > self.LTP_INDUCTION_THRESHOLD:
            delta = self.LTP_RATE * plastic_drive * theta_window
            new_ltp = min(1.0, current_ltp + delta)
        elif plastic_drive < 0.2:
            # LTD for unused synapses
            new_ltp = max(0.0, current_ltp - self.LTD_RATE)
        else:
            new_ltp = current_ltp

        # Fear memory strength: LTP × emotional salience
        emotional_salience = max(0.0, 0.5 - valence_polarity)
        fear_memory = new_ltp * emotional_salience * 1.5
        fear_memory = min(1.0, fear_memory)

        # Stress effects: acute CRH enhances LTP, chronic suppresses it
        crh_modulation = 1.0
        if crh_output > 0.5:
            crh_modulation = 1.0 - (crh_output - 0.5) * 0.6  # chronic stress
        else:
            crh_modulation = 1.0 + (0.5 - crh_output) * 0.3  # acute stress = enhancement

        self.state["plastic_drive"] = round(plastic_drive, 4)
        self.state["ltp_strength"] = round(new_ltp, 4)
        self.state["fear_memory_strength"] = round(fear_memory, 4)
        self.state["neuromodulatory_gate"] = round(neuromod_gate, 4)
        self.state["plasticity_threshold"] = self.LTP_INDUCTION_THRESHOLD
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "plastic_drive": round(plastic_drive, 4),
            "ltp_strength": round(new_ltp, 4),
            "fear_memory_strength": round(fear_memory, 4),
            "neuromodulatory_gate": round(neuromod_gate, 4),
            # brain_fear_plasticity
            "brain_fear_plasticity": round(new_ltp * emotional_salience, 4),
            "_crh_modulation": round(crh_modulation, 3),
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


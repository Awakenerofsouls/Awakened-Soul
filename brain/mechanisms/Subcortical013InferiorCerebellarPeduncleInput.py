"""
Subcortical013InferiorCerebellarPeduncleInput.py — Wire 13: Inferior Cerebellar Peduncle Input
=============================================================================================

PLACEMENT:
  Layer:    subcortical
  Filename: brain/subcortical/Subcortical013InferiorCerebellarPeduncleInput.py
  Mechanism: ICPInput

NEURAL SUBSTRATE:
  The inferior cerebellar peduncle (ICP) is one of three major white-matter
  tracts connecting the cerebellum to the rest of the nervous system. While
  the middle cerebellar peduncle (MCP) carries mossy-fiber inputs from
  pontine nuclei (cognitive/extraneous), the ICP is the somatosensory and
  vestibular channel.

  COMPOSITION:
  - Spinocerebellar pathways (dorsal, ventral) — carry proprioceptive
    information from muscle spindles, Golgi tendon organs, and cutaneous
    mechanoreceptors directly to the cerebellar cortex (especially vermis
    and paramedian lobules).
  - Vestibulocerebellar fibers — carry head velocity and graviceptive
    information from the vestibular nuclei of the brainstem to the
    flocculonodular lobe.
  - Caudal olivary climbing fiber projections — carry error signals
    from the inferior olivary complex (not modeled here; see
    Subcortical014PurkinjeCellErrorLearning.py).

  Two functional channels run in the ICP simultaneously:
  1. VESTIBULAR CHANNEL: encodes head and body orientation in space,
     angular velocity, linear acceleration. The flocculonodular lobe uses
     this to drive the vestibulo-ocular reflex (VOR) and regulate
     posture via the vestibular nuclei.
  2. PROPRIOCEPTIVE CHANNEL: encodes limb position, muscle length/velocity,
     joint angle. Projects primarily to the vermis (spinocerebellar vermal
     zone) and the paramedian lobule (spinal zone).

KEY FINDINGS:
  1. Dual-channel specificity. Bastian 2011 (J Neurophysiol 106:2064)
     demonstrated that the ICP carries distinct vestibular and proprioceptive
     signals that are processed separately by the cerebellum and contribute
     differently to movement correction. Vestibular signals dominate in
     the flocculonodular lobe; proprioceptive signals dominate in
     vermis and paramedian lobule.

  2. Proprioceptive error correction. Morton et al. 2018 (J Neurosci
     38:11644) showed that cerebellar LTD (long-term depression) at
     parallel fiber–Purkinje cell synapses uses proprioceptive error
     signals from spinocerebellar tracts to update internal models of
     limb dynamics. "The cerebellum uses an internal model of limb
     mechanics to compute predicted sensory consequences of movement."

  3. Cerebellar lesion consequences. ICP damage produces classic
     cerebellar ataxia: dysmetria, intention tremor, dysdiadochokinesia,
     and nystagmus — reflecting loss of the somatosensory feedback
     channel needed for online movement correction.

  4. Vestibular modulation of Purkinje cells. Floccular Purkinje cells
     receive vestibular input via mossy fiber–granule cell pathways AND
     directly from vestibular primary afferents. They encode gaze
     velocity and modulate eye movement via the vestibular nuclei.

AGENT'S SUBSTRATE MAPPING:
  ICPInput models the two channels of the inferior cerebellar peduncle:
  - vestibular_input_strength: aggregates vestibular channel activity
    (head velocity, spatial orientation signals)
  - proprioceptive_weight: aggregates proprioceptive channel activity
    (limb position, muscle state)
  - balance_signal: computed from both channels for posture/gait stability

INPUTS (from prior_results or tick args):
  - vestibular_activity: float 0-1 from vestibular nuclei / inner ear
  - proprioceptive_activity: float 0-1 from spinal afferents
  - head_movement_velocity: float 0-1 (angular velocity of head)
  - limb_state: float 0-1 (limb position deviation from target)

OUTPUTS (to brain_runner):
  - vestibular_input_strength: float 0-1 (vestibular channel activity)
  - proprioceptive_weight: float 0-1 (proprioceptive channel activity)
  - balance_signal: float 0-1 (combined stability posture signal)

REFS:
  - Bastian 2011 J Neurophysiol 106:2064 — vestibular vs proprioceptive ICP channels
  - Morton et al. 2018 J Neurosci 38:11644 — proprioceptive error correction
  - Ghez & Thach 2000 (Principles of Cerebellar Motor Control, sect. 9)
  - Bower & Beauchamp 2009 — somatosensory mossy fiber projections
  - Highstein & Fay 2013 — vestibular system anatomy

CITATIONS:
    PMC10732106 — Xue X, Lu R, Li H et al. (2024). In Vivo Characterization of
        Cerebellar Peduncles in Chronic Ankle Instability. Diagnostics.
    PMC4065054 — Pijnenburg M, Caeyenberghs K, Janssens L et al. (2014). Microstructural
        Integrity of the Superior Cerebellar Peduncle. Eur J Neurol.

CITATIONS
---------
  - [Ito 2008, Nat Rev Neurosci 9:304, cerebellar motor learning]
  - [Doya 1999, Neural Netw 12:961, cerebellum]
  - [Schmahmann 2019, Cerebellum 18:1, cerebellar cognitive affective]

"""

from brain.base_mechanism import BrainMechanism


class ICPInput(BrainMechanism):
    """
    Inferior Cerebellar Peduncle — vestibular and proprioceptive input channel.

    Models the two-channel input pathway of the ICP:
    - Vestibular channel: head/body orientation, angular velocity
    - Proprioceptive channel: limb position, muscle state
    Produces a balance_signal for posture and gait stability.
    """

    VESTIBULAR_DECAY = 0.05   # slow decay — vestibular is stable
    PROPRIOCEPTIVE_DECAY = 0.08  # faster decay — proprioceptive updates rapidly
    BALANCE_WEIGHT_VESTIBULAR = 0.45
    BALANCE_WEIGHT_PROPRIO = 0.55
    VESTIBULAR_SENSITIVITY = 1.2   # vestibular signals slightly amplified
    PROPRIOCEPTIVE_SENSITIVITY = 1.0

    def __init__(self):
        super().__init__(
            name="ICPInput",
            human_analog="Inferior cerebellar peduncle — vestibular + proprioceptive input",
            layer="subcortical",
        )
        self.state.setdefault("vestibular_input_strength", 0.0)
        self.state.setdefault("proprioceptive_weight", 0.0)
        self.state.setdefault("balance_signal", 0.0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        # --- Input extraction ---
        vestibular_raw = input_data.get("vestibular_activity", 0.0)
        proprioceptive_raw = input_data.get("proprioceptive_activity", 0.0)
        head_velocity = input_data.get("head_movement_velocity", 0.0)
        limb_deviation = input_data.get("limb_state", 0.5)  # 0.5=neutral, extremes=deviation

        # --- Vestibular channel ---
        # Head velocity adds to vestibular activity (movement generates signal)
        vestibular_drive = vestibular_raw + head_velocity * 0.4
        # Apply sensitivity scaling
        vestibular_drive *= self.VESTIBULAR_SENSITIVITY
        # Recursive decay update
        vs = self.state["vestibular_input_strength"]
        vs = vs * (1 - self.VESTIBULAR_DECAY) + vestibular_drive * self.VESTIBULAR_DECAY
        vs = max(0.0, min(1.0, vs))

        # --- Proprioceptive channel ---
        # Limb deviation from neutral = proprioceptive error signal
        # 0.5 = no deviation = low proprioceptive load
        # 0.0 or 1.0 = high deviation = high proprioceptive load
        proprioceptive_error = abs(limb_deviation - 0.5) * 2.0  # 0.0 to 1.0
        proprioceptive_drive = (
            proprioceptive_raw * 0.5 + proprioceptive_error * 0.5
        ) * self.PROPRIOCEPTIVE_SENSITIVITY
        # Recursive decay update
        pw = self.state["proprioceptive_weight"]
        pw = pw * (1 - self.PROPRIOCEPTIVE_DECAY) + proprioceptive_drive * self.PROPRIOCEPTIVE_DECAY
        pw = max(0.0, min(1.0, pw))

        # --- Balance signal ---
        # Combines vestibular (postural orientation) and proprioceptive
        # (limb stability) signals. When both are low → good balance.
        # When either is high → instability signal.
        vestibular_component = vs * self.BALANCE_WEIGHT_VESTIBULAR
        proprioceptive_component = pw * self.BALANCE_WEIGHT_PROPRIO
        balance = vestibular_component + proprioceptive_component
        balance = max(0.0, min(1.0, balance))

        self.state["vestibular_input_strength"] = vs
        self.state["proprioceptive_weight"] = pw
        self.state["balance_signal"] = balance
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "vestibular_input_strength": round(vs, 4),
            "proprioceptive_weight": round(pw, 4),
            "balance_signal": round(balance, 4),
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


"""
Build 14: Foundational003MultisensoryStartleMapper — Locus Coeruleus Startle Relay
==================================================================================

PLACEMENT:
  Layer:    foundational (pontine — LC modulation of startle circuit)
  Filename: brain/foundational/Foundational003MultisensoryStartleMapper.py
  Instance name: MultisensoryStartleMapper

NEURAL SUBSTRATE:
  Locus coeruleus-norepinephrine (LC-NE) system modulates the
  startle response circuit. The startle reflex is mediated by the
  giant neuron circuit in the pontine caudal pontine reticular
  formation (PnC), which receives multimodal input from visual,
  auditory, and somatosensory pathways. LC-NE modulates startle
  gain: high LC activity amplifies startle amplitude (hypervigilant
  states), while low LC activity dampens it.

  LC is the sole source of NE to the PnC startle circuit. NE acts
  via alpha-1 adrenergic receptors on PnC neurons, increasing
  startle gain. Fear-potentiated startle is partly mediated by LC
  activation preceding the startle stimulus — anticipatory anxiety
  elevates baseline LC firing, amplifying any subsequent startle.

  Startle itself is gated in the amygdala: CeA inhibits the PnC
  startle circuit at baseline; suppression of CeA (by conditioned
  threat) disinhibits PnC → startle fires. LC amplifies the output
  of whichever state is active.

  Key afferents:
    - ArousalRegulator: LC activity correlates with arousal_level
    - AmygdalaCeA: fear_suppression (CeA output suppressing startle)
    - BrainRunner: startling_event (bool) from external events

  Key efferents:
    - StartleAmplitude: float 0-1 (scaled startle reflex intensity)

KEY FINDINGS:
  1. LC-NE activity at baseline sets startle gain — elevated LC
     firing causes 2-3× larger startle responses [UNVERIFIED:
     Chikosi et al. 2001 — author-year only; please verify in
     J Neurosci or replace with Aston-Jones 1994/2000 LC gain papers].
  2. Fear-potentiated startle requires LC activation: blocking
     alpha-1 receptors in PnC eliminates fear potentiation without
     affecting baseline startle (Kelsey & Stewart 1983, Behav Neurosci).
  3. Multisensory integration in PnC: simultaneous visual + auditory
     stimuli produce larger startle than either alone, consistent
     with convergence of multiple sensory channels [UNVERIFIED —
     specific citation needed; suggest Ye & Corner 2002 J Neurophys
     or similar PnC multisensory paper; find and replace before commit].
  4. LC fires in bursts 200-500ms before expected startle stimulus
     during anticipatory anxiety — pre-activation lowers threshold
     [UNVERIFIED: Aston-Jones et al. 1996 — author-year only;
     verify in Prog Brain Res or replace with Aston-Jones & Cohen 2005].
  5. Habituation of startle over repeated trials is partly mediated
     by LC suppression — LC suppression reduces startle gain, not
     sensory adaptation per se [UNVERIFIED: Frails 1989 — author-year
     may be incorrect; verify or remove this specific claim].

INPUTS (prior_results):
  - ArousalRegulator: arousal_level (float 0-1), mode (str)
  - ValenceTagger: valence_polarity (float -1 to +1)
  - BrainRunner: startling_event (bool)
  - AmygdalaCeA (or CentralNucleusFearRouter): fear_suppression (float 0-1)

OUTPUTS:
  - startle_amplitude: float 0.0-1.0 (scaled startle response)
  - startle_gain: float 0.5-2.0 (multiplicative gain factor)
  - anticipatory_amplification: bool (LC pre-activation active)
  - multimodal_fusion: bool (multiple sensory channels active)

CITATIONS:
    PMC4140807 — Saletti PG, Maior RS, Hori E et al. (2014). Whole-Body Prepulse
        Inhibition Protocol to Test Sensorymotor Gating Mechanisms in Monkeys.
        J Neurosci Methods.
    PMC3198155 — Dendrinos G, Hemelt M, Keller A (2011). Prenatal VPA Exposure and
        Changes in Sensory Processing by the Superior Colliculus. Brain Res.
"""

from brain.base_mechanism import BrainMechanism


class MultisensoryStartleMapper(BrainMechanism):
    """
    LC-NE modulation of the pontine startle circuit.

    LC-NE sets the gain on the PnC startle reflex. Multimodal
    sensory input elevates amplitude. Fear state modulates via
    CeA disinhibition. Anticipatory anxiety pre-activates LC.
    """

    # Baseline startle amplitude (normal ambient stimulation)
    BASELINE_AMPLITUDE = 0.15

    # LC modulation: maps arousal_level to multiplicative gain
    LC_GAIN_LOW = 0.4    # low arousal
    LC_GAIN_HIGH = 2.2   # high arousal

    # Fear potentiation: CeA suppression → disinhibition → larger startle
    FEAR_POTENTIATION = 0.35

    # Multimodal boost: two+ sensory channels
    MULTIMODAL_BOOST = 0.20

    # Anticipatory threshold: how much pre-activation amplifies
    ANTICIPATORY_WINDOW_TICKS = 8  # LC pre-activation window
    ANTICIPATORY_GAIN = 0.30

    def __init__(self):
        super().__init__(
            name="MultisensoryStartleMapper",
            human_analog=(
                "Locus coeruleus-norepinephrine modulation of pontine "
                "caudal pontine reticular formation (PnC) startle circuit"
            ),
            layer="foundational",
        )
        self.state.setdefault("startle_amplitude", self.BASELINE_AMPLITUDE)
        self.state.setdefault("startle_gain", 1.0)
        self.state.setdefault("multimodal_fusion", False)
        self.state.setdefault("anticipatory_amplification", False)
        self.state.setdefault("pre_activation_ticks", 0)
        self.state.setdefault("tick_count", 0)

    def _arousal_to_gain(self, arousal_level: float) -> float:
        """Map arousal level to startle gain factor."""
        return self.LC_GAIN_LOW + (self.LC_GAIN_HIGH - self.LC_GAIN_LOW) * arousal_level

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- LC-NE gain from ArousalRegulator ----
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        lc_gain = self._arousal_to_gain(arousal_level)

        # ---- Fear disinhibition ----
        # CeA/fear_router output suppresses startle; low suppression = fear active = bigger startle
        fear_output = prior.get("ValenceTagger", {}).get("valence_polarity", 0.0)
        # Map valence: negative valence = fear activation = disinhibit PnC = larger startle
        fear_disinhibition = max(0.0, -fear_output) * self.FEAR_POTENTIATION

        # ---- Anticipatory amplification ----
        # Check for anticipatory anxiety (negative valence + elevated arousal)
        anticipatory = (arousal_level > 0.60) and (fear_output < -0.30)
        if anticipatory:
            self.state["pre_activation_ticks"] += 1
        else:
            self.state["pre_activation_ticks"] = 0
        anticipatory_amplification = anticipatory and self.state["pre_activation_ticks"] >= 3

        # ---- Startling event ----
        # Check for acute startling stimulus in this tick
        # (In real system: auditory/visual somatosensory trigger from BrainRunner)
        startling_event = input_data.get("startling_event", False)

        # ---- Multimodal fusion detection ----
        # Approximation: if arousal is high and valence is negative, assume
        # multiple sensory channels are likely active (proxy for multimodal)
        multimodal_fusion = (arousal_level > 0.65) and (fear_output < -0.40)

        # ---- Compute amplitude ----
        base = self.BASELINE_AMPLITUDE

        if startling_event:
            # Active startle response
            amplitude = base * lc_gain
            amplitude += fear_disinhibition * lc_gain * 0.5
            if anticipatory_amplification:
                amplitude += self.ANTICIPATORY_GAIN
            if multimodal_fusion:
                amplitude += self.MULTIMODAL_BOOST
        else:
            # Baseline state: reduced amplitude with habituation tendency
            amplitude = base * lc_gain * 0.3  # reduced without stimulus
            amplitude += fear_disinhibition * 0.3

        amplitude = max(0.0, min(1.0, amplitude))
        amplitude = round(amplitude, 4)

        # ---- Startle gain factor (for downstream consumers) ----
        startle_gain = round(lc_gain, 3)

        # Persist
        self.state["startle_amplitude"] = amplitude
        self.state["startle_gain"] = startle_gain
        self.state["multimodal_fusion"] = multimodal_fusion
        self.state["anticipatory_amplification"] = anticipatory_amplification
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "startle_amplitude": amplitude,
            "startle_gain": startle_gain,
            "anticipatory_amplification": anticipatory_amplification,
            "multimodal_fusion": multimodal_fusion,
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


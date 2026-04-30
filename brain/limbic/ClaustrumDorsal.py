"""
ClaustrumDorsal — Cl / Cortical Integration / Consciousness Substrate

NEURAL SUBSTRATE
================
The claustrum is a thin sheet of gray matter beneath the insular cortex,
between cortex and putamen. Despite its small size, it has reciprocal
connections with virtually all cortical areas (visual, auditory,
somatosensory, frontal, parietal, motor, prefrontal, temporal). Crick &
Koch 2005 hypothesized claustrum as the "conductor" of consciousness —
binding distributed cortical activity into unified subjective experience.

Dorsal claustrum (Cld) connects with sensorimotor + frontal cortex;
ventral claustrum (Clv) connects with limbic + temporal cortex.

Spiny + non-spiny GABAergic interneurons. Glutamatergic projection
neurons. Functional role: cross-cortical synchronization, gain
modulation, attention-gated cortical activity.

KEY FINDINGS
============
1. Claustrum reciprocally connects with virtually all cortical areas;
   anatomical hub position predicts integrative role —
   [Crick 2005, Phil Trans R Soc B 360:1271, doi:10.1098/rstb.2005.1661]
2. Claustral neurons exhibit broad multimodal responses + cross-cortical
   synchronization at high firing rates —
   [Smith 2012, J Neurosci 32:11854, doi:10.1523/JNEUROSCI.2032-12.2012]
3. Optogenetic claustrum activation modulates cortical attention +
   gain control — [Atlan 2018, Curr Biol 28:2752, doi:10.1016/j.cub.2018.06.052]
4. Claustrum lesions in patients produce deficits in cross-modal binding
   + sustained attention — [Koubeissi 2014, Epilepsy Behav 37:32, doi:10.1016/j.yebeh.2014.05.027]
5. Claustral firing patterns correlate with conscious-perception
   transitions; bridge between unconscious vs conscious processing —
   [Madden 2022, Trends Cogn Sci 26:1085, doi:10.1016/j.tics.2022.09.006]

INPUTS
======
- Multi-cortical convergence (we model as aggregate cortical_drive)
- ArousalRegulator.tonic_level
- ThalamocorticalProxy.thalamic_drive (default 0)

OUTPUTS
=======
- claustrum_drive (0-1)
- cross_cortical_sync (0-1)
- attention_gain_signal (0-1)
- consciousness_binding_signal (0-1)
- claustrum_state (str): "binding_active" | "attention_engaged" |
  "rest" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class ClaustrumDorsal(BrainMechanism):
    """Cld — cross-cortical integrator + consciousness binding hub."""

    BASELINE = 0.15
    SMOOTH = 0.20
    BINDING_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="ClaustrumDorsal",
            human_analog="Dorsal claustrum (cortical integration / binding)",
            layer="limbic",
        )
        self.state.setdefault("claustrum_drive", self.BASELINE)
        self.state.setdefault("cross_cortical_sync", 0.0)
        self.state.setdefault("attention_gain_signal", 0.0)
        self.state.setdefault("consciousness_binding_signal", 0.0)
        self.state.setdefault("claustrum_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, cortical: float, arousal: float,
                       thalamic: float) -> float:
        """Claustrum firing — convergent cortical + thalamic + arousal."""
        target = self.BASELINE + cortical * 0.45 + thalamic * 0.20
        target += max(0.0, arousal - 0.30) * 0.20
        return min(1.0, target)

    def _cross_sync(self, drive: float, cortical: float) -> float:
        """Cross-cortical synchronization signal (Smith 2012)."""
        return min(1.0, drive * 0.6 + cortical * 0.4)

    def _attention_gain(self, drive: float, arousal: float) -> float:
        """Attention-gated cortical gain modulation (Atlan 2018)."""
        return min(1.0, drive * 0.5 + max(0.0, arousal - 0.30) * 0.5)

    def _binding_signal(self, sync: float, attention: float, drive: float) -> float:
        """Consciousness binding signal (Crick 2005, Madden 2022)."""
        return min(1.0, sync * 0.4 + attention * 0.3 + drive * 0.3)

    def _classify_state(self, binding: float, attention: float,
                          drive: float) -> str:
        if binding > self.BINDING_THRESHOLD:
            return "binding_active"
        if attention > 0.40:
            return "attention_engaged"
        if drive > 0.20:
            return "rest"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Aggregate cortical drive proxy from any convergent cortical input
        cortical_keys = ["PrelimbicCortex", "CingulateAnterior", "InsulaAnterior",
                          "PerirhinalCortex", "PostrhinalCortex"]
        cortical_signals = []
        for k in cortical_keys:
            d = prior.get(k, {})
            for v in d.values():
                if isinstance(v, (int, float)):
                    cortical_signals.append(float(v))
        cortical = (sum(cortical_signals) / max(1, len(cortical_signals))) if cortical_signals else 0.0
        cortical = min(1.0, cortical)

        arousal_data = prior.get("ArousalRegulator", {})
        arousal = float(arousal_data.get("tonic_level", 0.30))

        thalamic_data = prior.get("ThalamocorticalProxy", {})
        thalamic = float(thalamic_data.get("thalamic_drive", 0.0))

        target = self._drive_target(cortical, arousal, thalamic)
        prev_drive = float(self.state.get("claustrum_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        sync = self._cross_sync(new_drive, cortical)
        attention = self._attention_gain(new_drive, arousal)
        binding = self._binding_signal(sync, attention, new_drive)

        state = self._classify_state(binding, attention, new_drive)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["claustrum_drive"] = round(new_drive, 4)
        self.state["cross_cortical_sync"] = round(sync, 4)
        self.state["attention_gain_signal"] = round(attention, 4)
        self.state["consciousness_binding_signal"] = round(binding, 4)
        self.state["claustrum_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "claustrum_drive": round(new_drive, 4),
            "cross_cortical_sync": round(sync, 4),
            "attention_gain_signal": round(attention, 4),
            "consciousness_binding_signal": round(binding, 4),
            "claustrum_state": state,
        }

    def _multimodal_response_breadth(self, cortical_signals: list) -> float:
        """Multimodal response breadth (Smith 2012)."""
        if not cortical_signals:
            return 0.0
        active = sum(1 for s in cortical_signals if s > 0.30)
        return min(1.0, active / max(1, len(cortical_signals)))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("claustrum_drive", 0.0),
            "binding": self.state.get("consciousness_binding_signal", 0.0),
            "attention": self.state.get("attention_gain_signal", 0.0),
            "state": self.state.get("claustrum_state", "quiet"),
        }

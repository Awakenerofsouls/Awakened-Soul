"""
OrexinWakePromoter — Lateral Hypothalamic Orexin / Hypocretin Wake Driver

NEURAL SUBSTRATE
================
Orexin (hypocretin) neurons are a small population (~70,000 in humans)
in the lateral hypothalamus and perifornical area that release the
neuropeptides orexin-A and orexin-B (also called hypocretin-1 and -2).
Discovered independently and simultaneously by two groups: Sakurai 1998
(named "orexin" for appetite-promoting effect) and de Lecea 1998
(named "hypocretin" for hypothalamic origin + secretin homology).

Functional role: orexin is the master sustainer of wakefulness.
Activates LC noradrenergic, TMN histaminergic, raphe serotonergic, and
PPN/LDT cholinergic ascending arousal systems. Loss of orexin neurons
produces narcolepsy with cataplexy in humans (Peyron 2000) and dogs
(Lin 1999); double-knockout mice show fragmented sleep + cataplexy
(Chemelli 1999).

The flip-flop sleep-wake model (Saper 2010): orexin stabilizes the
"wake" state by tonically activating arousal nuclei, preventing
unwanted transitions to sleep. Orexin levels are highest during active
wake, lowest during REM sleep.

Orexin neurons fire in response to glucose drop (linking energy state
to arousal), stress, and social/motivational cues — making them a
homeostatic-affective integrator that decides when sustained
wakefulness is needed.

KEY FINDINGS
============
1. Discovery of orexin (hypocretin) as lateral hypothalamic neuropeptide that promotes feeding and arousal — [Sakurai T 1998, Cell 92:573, doi:10.1016/S0092-8674(00)80949-6]
2. Independent discovery of hypocretins as hypothalamus-specific peptides homologous to secretin — [de Lecea L 1998, PNAS 95:322, doi:10.1073/pnas.95.1.322]
3. Orexin/hypocretin knockout mice exhibit narcolepsy phenotype with sleep fragmentation and cataplexy — [Chemelli RM 1999, Cell 98:437, doi:10.1016/S0092-8674(00)81973-X]
4. Loss of orexin neurons in human narcolepsy patients; cause of disease — [Peyron C 2000, Nat Med 6:991, doi:10.1038/79690]
5. Sleep-wake flip-flop model: orexin stabilizes wake state by activating monoaminergic arousal nuclei — [Saper CB 2010, Neuron 68:1023, doi:10.1016/j.neuron.2010.11.032]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level (current arousal state)
- CircadianTimer.firing_rate_proxy (circadian gating — high during day)
- ValenceTagger.valence_intensity (motivational salience)
- ArcuateAgRP.feeding_motivation (energy state — orexin fires on hunger)
- VitalCoreRegulator.vital_drive (low energy → orexin up)

OUTPUTS (to brain_runner enrichment)
=====================================
- orexin_drive (0-1) — overall orexin neuron firing
- wake_stabilization_signal (0-1) — sustains wake against sleep pressure
- lc_excitation (0-1) — orexin → LC noradrenergic
- tmn_excitation (0-1) — orexin → TMN histaminergic
- ppn_excitation (0-1) — orexin → PPN/LDT cholinergic
- raphe_excitation (0-1) — orexin → DR serotonergic
- orexin_state (str): "active_wake" | "homeostatic_feeding" |
  "stress_arousal" | "low_arousal" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class OrexinWakePromoter(BrainMechanism):
    """Orexin/hypocretin lateral hypothalamic wake-promoting system."""

    BASELINE = 0.10
    SMOOTH = 0.20
    WAKE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="OrexinAscendingArousalDriver",
            human_analog="Lateral hypothalamic orexin/hypocretin neurons",
            layer="foundational",
        )
        self.state.setdefault("orexin_drive", self.BASELINE)
        self.state.setdefault("wake_stabilization_signal", 0.0)
        self.state.setdefault("lc_excitation", 0.0)
        self.state.setdefault("tmn_excitation", 0.0)
        self.state.setdefault("ppn_excitation", 0.0)
        self.state.setdefault("raphe_excitation", 0.0)
        self.state.setdefault("orexin_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, arousal: float, circadian: float,
                       feeding: float, vital_low: float,
                       intensity: float) -> float:
        """Orexin drive — circadian + arousal + energy + salience
        (Sakurai 1998, Saper 2010 flip-flop)."""
        target = (self.BASELINE
                    + arousal * 0.30
                    + circadian * 0.20
                    + feeding * 0.15
                    + vital_low * 0.15
                    + intensity * 0.15)
        return min(1.0, target)

    def _wake_stabilization(self, drive: float, circadian: float) -> float:
        """Wake-state stabilization — Saper 2010 flip-flop. Orexin's
        primary function is preventing unwanted sleep transitions
        during the wake phase."""
        if drive < 0.20:
            return 0.0
        # Strongest stabilization during day phase
        return min(1.0, drive * 0.6 + circadian * 0.4)

    def _ascending_arousal_target(self, drive: float,
                                     base_drive: float) -> float:
        """Generic ascending excitation to monoaminergic + cholinergic
        arousal nuclei (Chemelli 1999 — knockouts show fragmented
        ascending arousal)."""
        return min(1.0, drive * 0.7 + base_drive * 0.3)

    def _classify_state(self, drive: float, feeding: float,
                          intensity: float, circadian: float) -> str:
        if drive < 0.15:
            return "quiet"
        if circadian < 0.30 and drive < 0.30:
            return "low_arousal"
        if feeding > 0.40:
            return "homeostatic_feeding"
        if intensity > 0.50:
            return "stress_arousal"
        if drive > self.WAKE_THRESHOLD:
            return "active_wake"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        circ_data = prior.get("CircadianTimer", {})
        circadian = float(circ_data.get("firing_rate_proxy",
                                circ_data.get("circadian_drive", 0.5)))

        agrp_data = prior.get("ArcuateAgRP", {})
        feeding = float(agrp_data.get("feeding_motivation",
                              agrp_data.get("agrp_drive", 0.0)))

        vital_data = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vital_data.get("vital_drive", 0.5))
        vital_low = max(0.0, 0.5 - vital_drive)

        valence = prior.get("ValenceTagger", {})
        intensity = float(valence.get("valence_intensity", 0.0))

        target = self._drive_target(arousal, circadian, feeding,
                                       vital_low, intensity)
        prev_drive = float(self.state.get("orexin_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        wake_stab = self._wake_stabilization(new_drive, circadian)

        # Pull current arousal-nuclei base drives if available
        lc_data = prior.get("LocusCoeruleusCore", {})
        lc_base = float(lc_data.get("lc_drive", 0.0))
        tmn_base = arousal * 0.5  # proxy
        ppn_data = prior.get("PedunculopontineCholinergic", {})
        ppn_base = float(ppn_data.get("ppn_drive", 0.0))
        raphe_data = prior.get("DorsalRaphe", {})
        raphe_base = float(raphe_data.get("raphe_drive", 0.0))

        lc_exc = self._ascending_arousal_target(new_drive, lc_base)
        tmn_exc = self._ascending_arousal_target(new_drive, tmn_base)
        ppn_exc = self._ascending_arousal_target(new_drive, ppn_base)
        raphe_exc = self._ascending_arousal_target(new_drive, raphe_base)

        state = self._classify_state(new_drive, feeding, intensity, circadian)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["orexin_drive"] = round(new_drive, 4)
        self.state["wake_stabilization_signal"] = round(wake_stab, 4)
        self.state["lc_excitation"] = round(lc_exc, 4)
        self.state["tmn_excitation"] = round(tmn_exc, 4)
        self.state["ppn_excitation"] = round(ppn_exc, 4)
        self.state["raphe_excitation"] = round(raphe_exc, 4)
        self.state["orexin_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "orexin_drive": round(new_drive, 4),
            "wake_stabilization_signal": round(wake_stab, 4),
            "lc_excitation": round(lc_exc, 4),
            "tmn_excitation": round(tmn_exc, 4),
            "ppn_excitation": round(ppn_exc, 4),
            "raphe_excitation": round(raphe_exc, 4),
            "orexin_state": state,
        }

    def _narcolepsy_proxy(self, recent_states: list) -> float:
        """Sustained low_arousal during expected wake phase = narcolepsy
        signature (Peyron 2000, Chemelli 1999)."""
        if not recent_states:
            return 0.0
        win = recent_states[-50:]
        l = sum(1 for s in win if s == "low_arousal")
        return l / max(1, len(win))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("orexin_drive", 0.0),
            "wake_stab": self.state.get("wake_stabilization_signal", 0.0),
            "lc": self.state.get("lc_excitation", 0.0),
            "state": self.state.get("orexin_state", "quiet"),
        }

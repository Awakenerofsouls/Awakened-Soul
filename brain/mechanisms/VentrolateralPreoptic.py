"""
VentrolateralPreoptic — VLPO / Galanin-GABA Sleep-Active Substrate

NEURAL SUBSTRATE
================
Cluster of GABAergic + galanin co-expressing neurons in ventrolateral
preoptic area of anterior hypothalamus. Sleep-active firing pattern —
fires during NREM, near silent during wake.

Outputs (inhibitory): tuberomammillary nucleus (TMN, histamine), locus
coeruleus (NE), dorsal/median raphe (5HT), perifornical orexin neurons,
pedunculopontine + laterodorsal tegmental (cholinergic). Inhibits the
entire wake-promoting system.

Sleep-wake flip-flop substrate (Saper switch): VLPO ↔ wake-promoting
nuclei (TMN/LC/raphe/orexin) form mutual-inhibition circuit. Reciprocal
inhibition produces bistable state transitions — explains why sleep-wake
transitions feel abrupt rather than gradual.

Adenosine A2A receptor activation drives VLPO firing — caffeine
antagonizes this. Galanin co-release potentiates GABAergic inhibition
of TMN; galanin KO reduces NREM amount.

VLPO lesions produce profound insomnia (>50% sleep loss). VLPO neuron
loss in aging humans correlates with sleep fragmentation.

KEY FINDINGS
============
1. VLPO galanin/GABA neurons are c-fos active during NREM, silent
   during wake — the canonical sleep-active population —
   [Sherin 1996, Science 271:216, doi:10.1126/science.271.5246.216]
2. VLPO lesions produce profound insomnia (>50% sleep loss) —
   [Lu 2000, J Neurosci 20:3830, PMC6772678]
3. Saper sleep-wake flip-flop: VLPO ↔ TMN/LC/raphe mutual inhibition;
   orexin stabilizes — [Saper 2005, Nature 437:1257,
   doi:10.1038/nature04284]
4. Adenosine A2A receptor activation drives VLPO firing — caffeine
   antagonism mechanism — [Scammell 2001, Neuroscience 107:653,
   PMID 11720787]
5. Galanin co-release potentiates GABAergic inhibition of TMN;
   galanin KO reduces NREM — [Kroeger 2018, Nat Commun 9:4129,
   doi:10.1038/s41467-018-06590-7]

INPUTS
======
- AdenosineProxy.adenosine_level (default from circadian/wakefulness)
- CircadianTimer.circadian_phase (or SuprachiasmaticOutput)
- TuberomammillaryNucleus.tmn_drive (mutual inhibition counterforce)
- LocusCoeruleusCore.lc_tonic_firing
- MedullaryRapheMagnus.raphe_5HT_drive
- OrexinWakePromoter.orexin_drive

OUTPUTS
=======
- vlpo_drive (0-1)
- gaba_galanin_release (0-1)
- tmn_inhibition_command (0-1)
- wake_system_inhibition (0-1) — aggregate
- vlpo_state (str): "nrem_active" | "sleep_pressure" | "wake_suppressed" | "quiet"

brain_runner enrichment:
    vlpo = all_results.get("VentrolateralPreoptic", {})
    if vlpo:
        enrichments["brain_vlpo_drive"] = vlpo.get("vlpo_drive", 0.10)
        enrichments["brain_gaba_galanin"] = vlpo.get("gaba_galanin_release", 0.0)
        enrichments["brain_wake_inhibition"] = vlpo.get("wake_system_inhibition", 0.0)
        enrichments["brain_vlpo_state"] = vlpo.get("vlpo_state", "quiet")
"""

from brain.base_mechanism import BrainMechanism


class VentrolateralPreoptic(BrainMechanism):
    """VLPO — galanin-GABA sleep-active substrate; flip-flop opposite to wake."""

    BASELINE = 0.10
    SMOOTH = 0.20
    NREM_THRESHOLD = 0.50
    SLEEP_PRESSURE_THRESHOLD = 0.25

    def __init__(self):
        super().__init__(
            name="VentrolateralPreoptic",
            human_analog="Ventrolateral preoptic (galanin-GABA sleep-active)",
            layer="foundational",
        )
        self.state.setdefault("vlpo_drive", self.BASELINE)
        self.state.setdefault("gaba_galanin_release", 0.0)
        self.state.setdefault("tmn_inhibition_command", 0.0)
        self.state.setdefault("wake_system_inhibition", 0.0)
        self.state.setdefault("vlpo_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # VLPO drive — adenosine + circadian, opposed by wake nuclei
    # ------------------------------------------------------------------
    def _vlpo_target(self, adenosine: float, circadian_phase: float,
                      tmn: float, lc: float, raphe: float, orexin: float) -> float:
        """VLPO firing target.

        Driven by adenosine accumulation (Scammell 2001) + circadian phase
        favoring sleep. Suppressed by mutual inhibition from wake nuclei
        (Saper 2005). Orexin is the stabilizer — high orexin = wake locked.
        """
        # Circadian phase: 0.0 = subjective night (sleep-favoring),
        # 0.5 = subjective day (wake-favoring). Convert to sleep-favoring score
        # (1 at night, 0 at day, sinusoidal).
        import math
        circadian_sleep_score = max(0.0, math.cos(circadian_phase * 2 * math.pi))

        target = self.BASELINE
        target += adenosine * 0.50
        target += circadian_sleep_score * 0.30

        # Mutual inhibition from wake nuclei
        target -= max(0.0, tmn - 0.20) * 0.30
        target -= max(0.0, lc - 0.30) * 0.25
        target -= max(0.0, raphe - 0.30) * 0.20
        target -= orexin * 0.40  # Orexin strongly suppresses VLPO

        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # GABA + galanin co-release (Kroeger 2018)
    # ------------------------------------------------------------------
    def _gaba_galanin(self, vlpo_drive: float) -> float:
        """GABA + galanin co-release scales with firing rate."""
        return min(1.0, vlpo_drive * 0.85)

    # ------------------------------------------------------------------
    # TMN inhibition command (canonical wake-suppression target)
    # ------------------------------------------------------------------
    def _tmn_inhibition(self, gaba_galanin: float) -> float:
        """VLPO→TMN inhibitory command. Galanin potentiates GABA effect."""
        return min(1.0, gaba_galanin * 0.90)

    # ------------------------------------------------------------------
    # Aggregate wake-system inhibition (Saper 2005 — broadcasts to all)
    # ------------------------------------------------------------------
    def _wake_inhibition(self, gaba_galanin: float) -> float:
        """Aggregate inhibitory drive to TMN + LC + raphe + orexin."""
        return min(1.0, gaba_galanin * 0.80)

    # ------------------------------------------------------------------
    # State classifier
    # ------------------------------------------------------------------
    def _classify_state(self, vlpo_drive: float, adenosine: float,
                          orexin: float) -> str:
        """Classify VLPO operating mode."""
        # Wake-locked: orexin high, VLPO suppressed
        if orexin > 0.55 and vlpo_drive < 0.20:
            return "wake_suppressed"
        # NREM-active: drive crossed NREM threshold
        if vlpo_drive > self.NREM_THRESHOLD:
            return "nrem_active"
        # Sleep pressure building: adenosine high but drive not yet at NREM
        if adenosine > 0.50 and vlpo_drive > self.SLEEP_PRESSURE_THRESHOLD:
            return "sleep_pressure"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _adenosine_window(self, adenosine: float,
                            recent_drive: list) -> float:
        """Sleep-pressure window — accumulated adenosine + recent drive
        history. Larger pressure when adenosine has been sustained even
        if current value is moderate.
        """
        if not recent_drive:
            return adenosine
        avg_recent = sum(recent_drive[-30:]) / max(1, len(recent_drive[-30:]))
        return min(1.0, adenosine * 0.6 + avg_recent * 0.4)

    def _flip_flop_stability(self, vlpo: float, wake_aggregate: float) -> float:
        """Saper flip-flop stability metric.
        High value = stable state (one side dominant).
        Low value = transitioning/unstable (both moderate).
        """
        diff = abs(vlpo - wake_aggregate)
        return min(1.0, diff)

    def _orexin_stabilization_factor(self, orexin: float,
                                        vlpo: float) -> float:
        """Orexin stabilizes the wake side of the flip-flop —
        higher orexin reinforces wake, narrows the transition window
        (Saper 2005).
        """
        if orexin < 0.30:
            return 0.0
        return min(1.0, orexin * (1.0 - vlpo))

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "vlpo_drive": self.state.get("vlpo_drive", 0.0),
            "gaba_galanin": self.state.get("gaba_galanin_release", 0.0),
            "wake_inhibition": self.state.get("wake_system_inhibition", 0.0),
            "state": self.state.get("vlpo_state", "quiet"),
        }
    def _galanin_potentiation_factor(self, gaba_galanin: float) -> float:
        """Galanin co-release potentiates GABAergic inhibition above
        what GABA alone provides (Kroeger 2018). Returns multiplier.
        """
        if gaba_galanin < 0.20:
            return 1.0
        return min(1.4, 1.0 + (gaba_galanin - 0.20) * 0.5)

    def _vlpo_neuron_loss_proxy(self, baseline_drive: float,
                                  current_drive: float) -> float:
        """Aging proxy: chronic reduction in VLPO drive vs expected
        baseline marks neuron-loss-like state (geriatric sleep
        fragmentation analog).
        """
        if baseline_drive < 0.10:
            return 0.0
        deficit = max(0.0, baseline_drive - current_drive)
        return min(1.0, deficit / max(baseline_drive, 0.001))


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ad = prior.get("AdenosineProxy", {})
        adenosine = float(ad.get("adenosine_level", 0.30))

        scn = prior.get("CircadianTimer", {})
        if not scn:
            scn = prior.get("SuprachiasmaticOutput", {})
        circadian_phase = float(scn.get("circadian_phase", 0.5))

        tmn_data = prior.get("TuberomammillaryNucleus", {})
        tmn = float(tmn_data.get("tmn_drive", 0.20))

        lc_data = prior.get("LocusCoeruleusCore", {})
        lc = float(lc_data.get("lc_tonic_firing", 0.20))

        raphe_data = prior.get("MedullaryRapheMagnus", {})
        raphe = float(raphe_data.get("raphe_5HT_drive",
                            raphe_data.get("serotonin_drive", 0.30)))

        orexin_data = prior.get("OrexinWakePromoter", {})
        orexin = float(orexin_data.get("orexin_drive", 0.30))

        # --- VLPO drive ---
        vlpo_target = self._vlpo_target(adenosine, circadian_phase, tmn, lc,
                                         raphe, orexin)
        prev_drive = float(self.state.get("vlpo_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, vlpo_target)

        # --- GABA + galanin ---
        gaba_galanin = self._gaba_galanin(new_drive)

        # --- TMN inhibition ---
        tmn_inh = self._tmn_inhibition(gaba_galanin)

        # --- Wake system inhibition ---
        wake_inh = self._wake_inhibition(gaba_galanin)

        state = self._classify_state(new_drive, adenosine, orexin)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vlpo_drive"] = round(new_drive, 4)
        self.state["gaba_galanin_release"] = round(gaba_galanin, 4)
        self.state["tmn_inhibition_command"] = round(tmn_inh, 4)
        self.state["wake_system_inhibition"] = round(wake_inh, 4)
        self.state["vlpo_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vlpo_drive": round(new_drive, 4),
            "gaba_galanin_release": round(gaba_galanin, 4),
            "tmn_inhibition_command": round(tmn_inh, 4),
            "wake_system_inhibition": round(wake_inh, 4),
            "vlpo_state": state,
        }

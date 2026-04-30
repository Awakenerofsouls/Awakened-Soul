"""
HistamineArousalBooster — TMN / Tuberomammillary Histamine Wake System

NEURAL SUBSTRATE
================
The tuberomammillary nucleus (TMN) of the posterior hypothalamus is the
sole source of histamine in the central nervous system. ~64,000 neurons
(human) project widely throughout cortex, thalamus, hypothalamus,
brainstem. TMN histaminergic neurons fire selectively during active
wakefulness — silent during NREM, completely silent during REM —
making them one of the canonical "wake-active" arousal systems.

Brown 2001 demonstrated TMN neurons fire tonically at ~2-3 Hz during
wake, drop to ~0.5 Hz during NREM, and silence completely during REM.
Histamine release in cortex via H1 receptors promotes cortical
desynchronization (alert wake EEG); H3 autoreceptors provide negative
feedback.

Functional role: cortical histamine is the substrate of the alerting
effect of wake. Antihistamines that cross the BBB produce sedation
specifically because they block H1 in cortex. The TMN is densely
innervated by orexin neurons (excitatory) and VLPO neurons
(inhibitory) — making it the integrating output of the sleep-wake
flip-flop switch (Saper 2005).

The TMN inhibits sleep-promoting VLPO via histamine and is inhibited
by VLPO via galanin/GABA — a mutual inhibition that produces sharp
sleep-wake transitions.

KEY FINDINGS
============
1. Tuberomammillary histamine neurons are wake-active; fire during active wake, silent during NREM/REM — [Brown RE 2001, Prog Neurobiol 63:637, doi:10.1016/S0301-0082(00)00039-3]
2. Comprehensive review of histamine in sleep-wake regulation; TMN as central wake-promoting hub — [Haas HL 2008, Physiol Rev 88:1183, doi:10.1152/physrev.00043.2007]
3. Sleep-wake flip-flop switch: mutual inhibition between TMN/wake nuclei and VLPO sleep nuclei produces state transitions — [Saper CB 2005, Nature 437:1257, doi:10.1038/nature04284]
4. H1 receptor activation in cortex promotes desynchronized wake EEG; H1 blockade by sedating antihistamines — [Lin JS 2011, Acta Pharmacol Sin 32:1159, doi:10.1038/aps.2011.106]
5. Genetic loss of histidine decarboxylase (HDC) impairs cortical activation and wake maintenance — [Parmentier R 2002, J Neurosci 22:7695, doi:10.1523/JNEUROSCI.22-17-07695.2002]

INPUTS (from prior_results)
============================
- OrexinWakePromoter.tmn_excitation (orexin → TMN)
- VentrolateralPreoptic.vlpo_drive (sleep-active inhibitory)
- ArousalRegulator.tonic_level
- CircadianTimer.firing_rate_proxy

OUTPUTS (to brain_runner enrichment)
=====================================
- tmn_drive (0-1) — TMN histaminergic firing
- cortical_histamine_release (0-1)
- wake_alerting_signal (0-1) — H1-mediated cortical desynchronization
- vlpo_inhibition (0-1) — TMN → VLPO inhibitory feedback
- tmn_state (str): "active_wake" | "drowsy" | "nrem" | "rem_silent" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class HistamineArousalBooster(BrainMechanism):
    """TMN histaminergic wake-promoting neurons (Haas 2008)."""

    BASELINE = 0.10
    SMOOTH = 0.20
    WAKE_THRESHOLD = 0.40

    def __init__(self):
        super().__init__(
            name="HistamineTMNCorticalDriver",
            human_analog="Tuberomammillary nucleus (histamine wake system)",
            layer="foundational",
        )
        self.state.setdefault("tmn_drive", self.BASELINE)
        self.state.setdefault("cortical_histamine_release", 0.0)
        self.state.setdefault("wake_alerting_signal", 0.0)
        self.state.setdefault("vlpo_inhibition", 0.0)
        self.state.setdefault("tmn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _drive_target(self, orexin: float, vlpo: float, arousal: float,
                       circadian: float) -> float:
        """TMN drive — orexin excites, VLPO inhibits, modulated by
        arousal + circadian (Brown 2001, Saper 2005 flip-flop)."""
        excitation = orexin * 0.40 + arousal * 0.30 + circadian * 0.20
        inhibition = vlpo * 0.50  # VLPO is strong inhibitor
        target = self.BASELINE + excitation - inhibition
        return max(0.0, min(1.0, target))

    def _cortical_histamine(self, drive: float) -> float:
        """Cortical histamine release scales with TMN firing
        (Haas 2008)."""
        return min(1.0, drive * 0.85)

    def _wake_alerting(self, histamine: float, arousal: float) -> float:
        """H1-mediated cortical desynchronization (Lin 2011 antihistamine
        sedation logic)."""
        return min(1.0, histamine * 0.6 + arousal * 0.3)

    def _vlpo_inhibitory_feedback(self, drive: float) -> float:
        """TMN → VLPO inhibition closes the flip-flop loop (Saper 2005)."""
        return min(1.0, drive * 0.75)

    def _classify_state(self, drive: float, vlpo: float,
                          arousal: float) -> str:
        if drive < 0.10:
            return "quiet"
        # Brown 2001: TMN silent during REM
        # We approximate REM as very low arousal + high VLPO (REM-active)
        if arousal < 0.15 and vlpo > 0.50:
            return "rem_silent"
        if vlpo > 0.45 and drive < 0.20:
            return "nrem"
        if drive < 0.25:
            return "drowsy"
        if drive > self.WAKE_THRESHOLD:
            return "active_wake"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ox_data = prior.get("OrexinWakePromoter", {})
        orexin = float(ox_data.get("tmn_excitation",
                            ox_data.get("orexin_drive", 0.0)))

        vlpo_data = prior.get("VentrolateralPreoptic", {})
        vlpo = float(vlpo_data.get("vlpo_drive",
                            vlpo_data.get("sleep_drive", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        circ_data = prior.get("CircadianTimer", {})
        circadian = float(circ_data.get("firing_rate_proxy", 0.5))

        target = self._drive_target(orexin, vlpo, arousal, circadian)
        prev_drive = float(self.state.get("tmn_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        histamine = self._cortical_histamine(new_drive)
        alerting = self._wake_alerting(histamine, arousal)
        vlpo_inhib = self._vlpo_inhibitory_feedback(new_drive)

        state = self._classify_state(new_drive, vlpo, arousal)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["tmn_drive"] = round(new_drive, 4)
        self.state["cortical_histamine_release"] = round(histamine, 4)
        self.state["wake_alerting_signal"] = round(alerting, 4)
        self.state["vlpo_inhibition"] = round(vlpo_inhib, 4)
        self.state["tmn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "tmn_drive": round(new_drive, 4),
            "cortical_histamine_release": round(histamine, 4),
            "wake_alerting_signal": round(alerting, 4),
            "vlpo_inhibition": round(vlpo_inhib, 4),
            "tmn_state": state,
        }

    def _antihistamine_sedation_proxy(self, histamine: float) -> float:
        """Inverse: how much sedation an H1 blocker would induce
        (Parmentier 2002 HDC-knockout phenotype)."""
        return 1.0 - histamine

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("tmn_drive", 0.0),
            "histamine": self.state.get("cortical_histamine_release", 0.0),
            "alerting": self.state.get("wake_alerting_signal", 0.0),
            "state": self.state.get("tmn_state", "quiet"),
        }

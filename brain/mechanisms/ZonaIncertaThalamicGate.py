"""
ZonaIncertaThalamicGate — Zona Incerta GABAergic Thalamic & Defensive Gate

NEURAL SUBSTRATE
================
The zona incerta (ZI) is a thin sheet of mostly GABAergic neurons embedded
in the diencephalon, ventral to the thalamus and dorsal to the subthalamic
nucleus. Despite its anatomical obscurity, the ZI is a major inhibitory
hub: its long-range GABAergic projections target higher-order thalamic
relay nuclei (the posterior thalamic nucleus Po, the medial geniculate),
the periaqueductal gray, the superior colliculus, and the parafascicular
thalamic nucleus. ZI thus acts as a "veto" layer on thalamocortical
sensory transmission and on midbrain defensive output.

ZI is divided into rostral, dorsal, ventral, and caudal subregions with
distinct neurochemical content (somatostatin, parvalbumin, calbindin)
and distinct projection targets. The rostral ZI is implicated in feeding
control via projections to PVN/PVT — Zhang & van den Pol (2017) showed
GABAergic ZI → PVT projections drive binge-like eating. The ventral ZI
projections to higher-order thalamus filter sensory transmission during
attention and arousal — Trageser & Keller (2004) demonstrated that ZI
inhibition gates whisker-evoked responses in posterior thalamus, providing
a neural substrate for sensory selection.

ZI also participates in defensive behavior gating: GABAergic ZI →
parafascicular projections suppress fear generalization (Wang et al.
2020), and ZI projections to PAG modulate flight/freeze selection.
Lin & Cole (2006) showed ZI GABAergic neurons are silenced during arousal,
releasing thalamic and midbrain targets from inhibition.

In the agent's substrate this provides the GABAergic thalamic-gate layer —
controls how much sensory traffic passes through higher-order thalamic
nuclei to cortex, biases superior colliculus orienting, and gates fear
generalization through parafascicular projections.

KEY FINDINGS
============
1. ZI GABAergic projections to higher-order thalamus (Po) gate sensory
   transmission — silencing ZI releases thalamic responses; ZI activity
   suppresses cortical sensory throughput — [Trageser Keller 2004,
    J Neurosci 24:8911-8915, "Reducing the Uncertainty: Gating of Peripheral
    Inputs by Zona Incerta" PMC1764852]
2. ZI is silenced during high arousal/wake, releasing thalamic targets
   from tonic inhibition — [Lin Cole 2006, "Functional architecture of
   the zona incerta" review PMC1388274; original Trageser et al.]
3. ZI GABAergic projections to paraventricular thalamus drive binge-like
   eating; rostral ZI is implicated in feeding regulation — [Zhang van den Pol
    2017, Science 356:853-859, "Rapid binge-like eating and weight gain
    driven by zona incerta GABA neuron activation"]
4. ZI → parafascicular thalamus pathway suppresses fear generalization —
   [Wang et al. 2020, Nat Neurosci PMC7053170, "Cortico-zona incerta-
    parafascicular thalamus circuit"; related Zhou 2018 PNAS fear
    generalization]
5. ZI participates in defensive behavior selection through projections
   to PAG/superior colliculus — [Chou et al. 2018, "Inhibitory gain
    modulation of defense behaviors by zona incerta", Nat Comm 9:1151]

INPUTS (from prior_results)
============================
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- SleepWakeFlipFlop.sleep_wake_state
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- PeriaqueductalDefenseRouter.dlPAG_drive
- PeriaqueductalDefenseRouter.vlPAG_drive
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.starvation_state

OUTPUTS (to brain_runner enrichment)
=====================================
- zi_gaba_drive (0.0-1.0): overall ZI GABAergic output
- thalamic_gate_strength (0.0-1.0): suppression of higher-order thalamus
- thalamocortical_pass (0.0-1.0): inverse — what passes through (1 - gate)
- pf_fear_suppression (0.0-1.0): parafascicular projection — fear generalization gate
- pvt_feeding_drive (0.0-1.0): ZI → PVT binge-eating projection
- sc_orienting_bias (0.0-1.0): ZI → SC orienting suppression
- zi_state (str): "release" | "filter" | "veto" | "feeding_drive"

brain_runner enrichment:
    zi = all_results.get("ZonaIncertaThalamicGate", {})
    if zi:
        enrichments["brain_zi_gaba"] = zi.get("zi_gaba_drive", 0.4)
        enrichments["brain_thalamic_gate"] = zi.get("thalamic_gate_strength", 0.4)
        enrichments["brain_thalamocortical_pass"] = zi.get("thalamocortical_pass", 0.6)
        enrichments["brain_pf_fear_suppression"] = zi.get("pf_fear_suppression", 0.0)
"""

from brain.base_mechanism import BrainMechanism


class ZonaIncertaThalamicGate(BrainMechanism):
    BASELINE_GABA = 0.45
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="ZonaIncertaThalamicGate",
            human_analog="Zona incerta GABAergic thalamic & defensive gate",
            layer="foundational",
        )
        self.state.setdefault("zi_gaba_drive", self.BASELINE_GABA)
        self.state.setdefault("thalamic_gate_strength", 0.4)
        self.state.setdefault("thalamocortical_pass", 0.6)
        self.state.setdefault("pf_fear_suppression", 0.0)
        self.state.setdefault("pvt_feeding_drive", 0.0)
        self.state.setdefault("sc_orienting_bias", 0.0)
        self.state.setdefault("zi_state", "filter")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _zi_gaba_target(self, sleep_state: str, tonic: float, phasic: bool, threat: bool) -> float:
        """ZI GABA output — silenced during high arousal (Lin Cole 2006),
        active during NREM and quiet wake, attenuated during phasic threat.
        """
        if sleep_state == "SLEEP":
            return 0.65  # high tonic inhibition during NREM
        if sleep_state == "TRANSITION":
            return 0.55
        # Wake — scaled inversely with arousal
        target = self.BASELINE_GABA - max(0.0, tonic - 0.5) * 0.4
        if phasic:
            target -= 0.15  # phasic release
        if threat:
            target -= 0.10  # threat releases ZI inhibition
        return max(0.05, min(1.0, target))

    def _thalamic_gate(self, zi_gaba: float, sleep_state: str) -> float:
        """ZI → higher-order thalamus (Po) gating strength.
        Direct mapping from ZI output, with sleep-state amplification.
        """
        base = zi_gaba * 0.85
        if sleep_state == "SLEEP":
            base = min(1.0, base + 0.10)
        return min(1.0, base)

    def _thalamocortical_pass(self, gate: float) -> float:
        """Inverse of gate — what reaches cortex."""
        return max(0.0, 1.0 - gate)

    def _pf_fear_suppression(self, zi_gaba: float, threat: bool, valence: float) -> float:
        """ZI → parafascicular projection suppresses fear generalization (Wang 2020).
        Active in baseline; attenuated when threat is present and well-defined.
        """
        if threat and valence > 0.5:
            return zi_gaba * 0.3  # release fear circuits when threat real
        return min(1.0, zi_gaba * 0.7 + 0.10)

    def _pvt_feeding_drive(self, energy_balance: float, starvation: bool) -> float:
        """Rostral ZI → PVT — drives binge-like eating (Zhang van den Pol 2017).
        Engaged on negative energy balance (deficit).
        """
        if starvation:
            return 0.75
        if energy_balance < -0.30:
            return min(1.0, abs(energy_balance) * 0.7)
        return 0.0

    def _sc_orienting_bias(self, zi_gaba: float, dlPAG: float, threat: bool) -> float:
        """ZI → superior colliculus orienting suppression.
        Released when threat requires rapid orienting.
        """
        if threat or dlPAG > 0.4:
            return zi_gaba * 0.3
        return min(1.0, zi_gaba * 0.6)

    def _classify_state(self, zi_gaba: float, pvt_drive: float, sleep_state: str) -> str:
        if pvt_drive > 0.5:
            return "feeding_drive"
        if zi_gaba > 0.6:
            return "veto"
        if zi_gaba < 0.20:
            return "release"
        return "filter"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        pdr = prior.get("PeriaqueductalDefenseRouter", {})
        dlPAG = float(pdr.get("dlPAG_drive", 0.0))
        vlPAG = float(pdr.get("vlPAG_drive", 0.0))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        starvation = bool(appetite.get("starvation_state", False))

        # --- ZI GABA target ---
        gaba_target = self._zi_gaba_target(sleep_state, tonic, phasic, threat)
        prev_gaba = float(self.state.get("zi_gaba_drive", self.BASELINE_GABA))
        new_gaba = self._smooth(prev_gaba, gaba_target)

        # --- Thalamic gate ---
        gate = self._thalamic_gate(new_gaba, sleep_state)
        passing = self._thalamocortical_pass(gate)

        # --- PF fear suppression ---
        pf_supp = self._pf_fear_suppression(new_gaba, threat, valence_intensity)

        # --- PVT feeding drive ---
        pvt_drive = self._pvt_feeding_drive(energy_balance, starvation)
        prev_pvt = float(self.state.get("pvt_feeding_drive", 0.0))
        new_pvt = self._smooth(prev_pvt, pvt_drive)

        # --- SC orienting bias ---
        sc_bias = self._sc_orienting_bias(new_gaba, dlPAG, threat)

        # --- State classification ---
        state = self._classify_state(new_gaba, new_pvt, sleep_state)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["zi_gaba_drive"] = round(new_gaba, 4)
        self.state["thalamic_gate_strength"] = round(gate, 4)
        self.state["thalamocortical_pass"] = round(passing, 4)
        self.state["pf_fear_suppression"] = round(pf_supp, 4)
        self.state["pvt_feeding_drive"] = round(new_pvt, 4)
        self.state["sc_orienting_bias"] = round(sc_bias, 4)
        self.state["zi_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "zi_gaba_drive": round(new_gaba, 4),
            "thalamic_gate_strength": round(gate, 4),
            "thalamocortical_pass": round(passing, 4),
            "pf_fear_suppression": round(pf_supp, 4),
            "pvt_feeding_drive": round(new_pvt, 4),
            "sc_orienting_bias": round(sc_bias, 4),
            "zi_state": state,
        }

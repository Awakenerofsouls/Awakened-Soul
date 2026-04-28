"""
Subcortical022ThalamicReticularSectorGating.py — Wire 22: ThalamicTRNGating

Thalamic reticular nucleus (TRN) — sector-based thalamic gating.

Neural analog: The thalamic reticular nucleus (TRN) is a thin shell of
GABAergic neurons wrapping the dorsal thalamus. It is divided into
anatomically and functionally distinct sectors, each dedicated to a
specific thalamocortical pathway: visual, auditory, somatosensory, motor,
prefrontal, and limbic. TRN neurons fire bursts in sleep but maintain
tonic inhibition during waking.

ANATOMY (Halassa 2014; McAlonan 2006):
  - TRN receives from: layer 6 corticothalamic neurons (all sectors),
    thalamic relay neurons (collaterals), brainstem cholinergic nuclei
  - TRN sends exclusively to: thalamic relay neurons (not cortex)
    — inhibitory (GABAergic) projections to first-order and higher-order nuclei
  - Sectors: visual TRN (connected to LGN), somatosensory TRN (VPL/VPM),
    motor TRN (VA/VL), prefrontal TRN (MD/CM), limbic TRN (anterior thalamus)
  - Gap junctions: TRN neurons are electrically coupled via gap junctions,
    enabling synchronized inhibition across sectors

HALASSA 2014 — ATTENTION AND GATING:
  TRN is the "gatekeeper" of thalamocortical transmission. When attention
  is directed to a sensory modality, the corresponding TRN sector fires
  to suppress competing thalamic nuclei (decreasing their relay fidelity),
  while sparing the attended sector. This is the thalamic "spotlight"
  model of attention.
  - Prefrontal TRN: regulates attention and cognitive filtering
  - Sensory TRN: regulates sensory influx during selective attention
  - McAlonan et al. 2006 Nature Neuroscience: "TRN is critical for
    generating sleep spindles and controlling attention"

MECHANISM:
  1. Gating strength: how strongly TRN is suppressing thalamic relay
  2. Attention modulation: top-down PFC input to TRN sectors
  3. Thalamic inhibition factor: degree of GABAergic inhibition on relay nuclei

THREE MODES OF TRN OPERATION:
  - Sleep mode: widespread TRN burst firing → thalamic relay shutdown
  - Awake mode: sparse tonic TRN firing → moderate relay fidelity
  - Attention mode: sector-specific TRN burst → selective relay suppression

KEY FUNCTIONS:
  1. gating_strength: total TRN-mediated thalamic gating signal
  2. attention_modulation: degree of prefrontal attention drive to TRN
  3. thalamic_inhibition_factor: GABAergic inhibition of relay nuclei

REFS:
- Halassa 2014 Nat Neurosci 17:1063-1072 — TRN in attention and sleep
- McAlonan et al. 2006 Nat Neurosci 9:1471-1472 — TRN attention control
- Pinault 2004 Brain Research Reviews — TRN anatomy and physiology
- Crick 1984 PNAS — original TRN attention hypothesis
- Sherman & Guillery 2013 — thalamocortical connections

CITATIONS:
    PMC3044616 — Ferrarelli F, Tononi G (2011). The Thalamic Reticular Nucleus and
        Schizophrenia. Neurosci Biobehav Rev.
    PMC6773087 — McAlonan K, Brown VJ, Bowman EM (2000). Thalamic Reticular Nucleus
        Activation Reflects Attentional Gating During Classical Conditioning. J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ThalamicReticularSectorGating(BrainMechanism):
    """
    Thalamic reticular nucleus (TRN) — sector-based thalamic gatekeeper.

    TRN wraps the dorsal thalamus as a GABAergic inhibitory shell. Each
    sector gates a specific thalamocortical pathway. During selective
    attention, the relevant sector fires to suppress competing inputs.
    During low-arousal states, widespread TRN burst firing reduces
    thalamic relay fidelity (sleep mode).

    Inputs: PFC attention signals (via sector-specific input),
    arousal state, competing sensory signals.
    Output: gating_strength and thalamic_inhibition_factor.
    """

    # TRN parameters
    BASELINE_INHIBITION = 0.20      # Minimum tonic TRN inhibition in wakefulness
    SECTOR_INHIBITION_GAIN = 1.00   # Gain on sector-specific gating
    ATTENTION_GATE_FACTOR = 0.50    # PFC attention amplifies sector-specific gating
    SLEEP_SUPPRESSION = 0.80         # Sleep-mode inhibition multiplier
    THALAMIC_INHIBITION_DECAY = 0.07

    def __init__(self):
        super().__init__(
            name="ThalamicReticularSectorGating",
            human_analog="Thalamic reticular nucleus (TRN) — sector-based gatekeeper",
            layer="subcortical",
        )
        self.state.setdefault("gating_strength", 0.0)
        self.state.setdefault("attention_modulation", 0.0)
        self.state.setdefault("thalamic_inhibition_factor", 0.0)
        self.state.setdefault("active_sector", "motor")
        self.state.setdefault("sleep_mode_active", False)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # Source 1: PFC attention (prefrontal TRN sector drive)
        pfc_attention = prior.get("PrefrontalExecutive", {})
        pfc_attention_level = pfc_attention.get("executive_relay_strength", 0.0)

        # Source 2: Arousal state (determines TRN mode)
        arousal = prior.get("ThalamicCentromedianIntralaminar", {})
        arousal_level = arousal.get("arousal_modulation", 0.5)

        # Source 3: Competing sensory signals (what should be gated out?)
        sc_visual = prior.get("SuperiorColliculusVisual", {})
        sc_visual_strength = sc_visual.get("SC_visual_signal_strength", 0.0)

        dorsal_stream = prior.get("DorsalVisualStream", {})
        dorsal_strength = dorsal_stream.get("motion_signal_strength", 0.0)

        # Source 4: VL motor thalamus (motor sector gating)
        vl_motor = prior.get("ThalamicVentralLateralMotor", {})
        vl_signal = vl_motor.get("VL_relay_strength", 0.0)

        # Determine mode
        # Low arousal + high competing input → sleep-mode suppression
        sleep_mode = arousal_level < 0.25 and (
            sc_visual_strength > 0.3 or dorsal_strength > 0.3
        )

        # Attention modulation: PFC input to TRN
        # Higher PFC activity = stronger selective attention = sector gating
        attention_modulation = max(
            0.0,
            min(1.0, pfc_attention_level * self.ATTENTION_GATE_FACTOR * 1.5)
        )

        # Gating strength: sector-specific inhibition
        # Depends on competing inputs (what needs suppressing?)
        competing_load = max(sc_visual_strength, dorsal_strength, vl_signal)

        if sleep_mode:
            # Sleep mode: widespread strong inhibition
            gating_strength = self.SLEEP_SUPPRESSION
        else:
            # Awake mode: targeted gating based on attention + competing load
            raw_gating = (
                self.BASELINE_INHIBITION
                + attention_modulation * self.SECTOR_INHIBITION_GAIN * 0.5
                + competing_load * 0.25
            )
            gating_strength = max(0.0, min(1.0, raw_gating))

        # Thalamic inhibition factor: GABAergic output from TRN
        # This directly suppresses thalamic relay fidelity
        thalamic_inhibition = gating_strength * 0.90 + self.BASELINE_INHIBITION * 0.10
        thalamic_inhibition = max(0.0, min(1.0, thalamic_inhibition))

        # Decay inhibition if no strong competing signals
        if competing_load < 0.1 and not sleep_mode:
            thalamic_inhibition = max(
                self.BASELINE_INHIBITION,
                thalamic_inhibition - self.THALAMIC_INHIBITION_DECAY
            )

        self.state["gating_strength"] = round(gating_strength, 4)
        self.state["attention_modulation"] = round(attention_modulation, 4)
        self.state["thalamic_inhibition_factor"] = round(thalamic_inhibition, 4)
        self.state["active_sector"] = (
            "visual" if sc_visual_strength > 0.4 else
            "motor" if vl_signal > 0.4 else
            "cognitive"
        )
        self.state["sleep_mode_active"] = sleep_mode
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "gating_strength": round(gating_strength, 4),
            "attention_modulation": round(attention_modulation, 4),
            "thalamic_inhibition_factor": round(thalamic_inhibition, 4),
        }

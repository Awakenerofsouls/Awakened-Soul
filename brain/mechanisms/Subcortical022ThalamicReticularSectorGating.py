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


CITATIONS
---------
  - [Sherman 2002, Phil Trans R Soc Lond B 357:1695, thalamic relay]
  - [Halassa 2017, Nat Neurosci 20:1669, thalamic computation]
  - [Saalmann 2012, Science 337:753, pulvinar attention]
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
        self.state.setdefault("recent_states", [])
        self.state.setdefault("recent_drives", [])
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


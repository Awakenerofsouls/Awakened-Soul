"""
Build 13: Foundational002RespiratoryPainIntegrator — Rostral Ventral Respiratory Column
=========================================================================================

PLACEMENT:
  Layer:    foundational (brainstem — ventral respiratory column)
  Filename: brain/foundational/Foundational002RespiratoryPainIntegrator.py
  Instance name: RespiratoryPainIntegrator

NEURAL SUBSTRATE:
  Ventral respiratory column (VRC) in the ventrolateral medulla,
  specifically the rostral VRC containing inspiratory and
  expiratory premotor neurons. Receives pain input from the
  spinal dorsal horn via the lateral parapyramidal region and
  integrates it with chemoreceptor and stretch receptor feedback
  to generate respiratory drive. Pain activates the VRC via
  the lateral paragigantocellular nucleus (LPGi), causing the
  characteristic hyperventilation response to pain (the "pain-
  hyperventilation" reflex).

  Key afferents:
    - Spinal cord dorsal horn: pain_signal (nociceptive input)
    - GutSignalRelay: gut_distress (visceral pain equivalent)
    - ArousalRegulator: arousal_level (modulatory tone)

  Key efferents:
    - Phrenic motor nucleus (C3-C5) → diaphragm
    - Intercostal motor nuclei → intercostal muscles
    - Abdominal motor nucleus → abdominal muscles (expiration)

KEY FINDINGS:
  1. Nociceptive stimulation causes immediate tachypnea (rapid
     shallow breathing) via excitation of inspiratory neurons in
     the rostral VRC — hyperventilation appears within 1-2 breaths
     (Boon et al. 2004, Journal of Applied Physiology).
  2. LPGi provides the primary relay from spinal nociceptive
     pathways to the VRC — lesions of LPGi abolish pain-evoked
     respiratory response (Nunez et al. 2000, Brain Research).
  3. The expiratory neurons in the caudal VRC are also activated
     by pain, producing forced expiration (the gasp/brace reflex).
  4. Mu-opioid receptor activation in the VRC suppresses
     respiratory drive — fentanyl reduces VRC neuron firing by
     ~50% (Liu et al. 2001, Anesthesiology).
  5. Emotional anticipation of pain also elevates respiratory
     rate via cortical inputs to the VRC — expectancy hyperventilates
     before pain arrives [UNVERIFIED: Boiten 1998 — author-year only;
     verify in Biol Psychol or replace with，呼吸 and anticipation
     literature; suggest Boiten et al. or similar; verify before commit].

INPUTS (prior_results):
  - BrainRunner bridge: pain_signal (float 0-1, from nociceptive)
  - GutSignalRelay: gut_distress (float 0-1)
  - ArousalRegulator: arousal_level (float 0-1)
  - StressActivationAxis: crh_level (float 0-1)

OUTPUTS:
  - respiratory_rate_index: float 0.0-1.0 (approximate normalized RR)
  - tidal_volume_index: float 0.0-1.0 (approximate normalized TV)
  - minute_ventilation_index: float 0.0-1.0 (RR × TV approximation)
  - pain_suppressed: bool (mu-opioid analgesia suppresses drive)
  - active_phase: str ("inspiration" | "expiration" | "pause")

CITATIONS:
    PMC11183208 — Zhu M, Jun S, Nie X et al. (2024). Mapping of Afferent and Efferent
        Connections of PNMT-Expressing Neurons in the Nucleus Tractus Solitarius.
        J Neurosci.
    PMC2699562 — Paterson DS, Darnall R (2009). 5-HT2A Receptors are Concentrated in
        Regions of the Human Infant Medulla Involved in Respiratory and Autonomic Control.
        Brain Struct Funct.
"""

from brain.base_mechanism import BrainMechanism


class RespiratoryPainIntegrator(BrainMechanism):
    """
    Ventral respiratory column — pain-hyperventilation integrator.

    Pain activates inspiratory and expiratory VRC neurons via LPGi,
    producing rapid shallow breathing. Suppressed by opioid analgesia.
    """

    # Normal resting respiratory rate index (normalized)
    RESTING_RR = 0.40
    RESTING_TV = 0.55   # tidal volume is relatively high at rest

    # Respiratory response to pain: hyperventilation
    PAIN_RR_ELEVATION = 0.38  # pain dramatically elevates RR
    PAIN_TV_SUPPRESSION = 0.15  # pain → shallow breathing

    # Convergence rates
    RR_CONVERGENCE = 0.12
    TV_CONVERGENCE = 0.06

    # Phase cycling (simplified — assumes ~4s breath cycle at rest)
    # 0.0-0.4: inspiration, 0.4-0.75: expiration, 0.75-1.0: pause
    PHASE_INSPIRATION_START = 0.0
    PHASE_INSPIRATION_END = 0.40
    PHASE_EXPIRATION_END = 0.75

    def __init__(self):
        super().__init__(
            name="RespiratoryPainIntegrator",
            human_analog=(
                "Ventral respiratory column (rVRC) — inspiratory/expiratory "
                "premotor neurons, lateral paragigantocellular nucleus pain relay"
            ),
            layer="foundational",
        )
        self.state.setdefault("respiratory_rate_index", self.RESTING_RR)
        self.state.setdefault("tidal_volume_index", self.RESTING_TV)
        self.state.setdefault("minute_ventilation_index", self.RESTING_RR * self.RESTING_TV)
        self.state.setdefault("pain_suppressed", False)
        self.state.setdefault("phase_fraction", 0.0)
        self.state.setdefault("active_phase", "inspiration")
        self.state.setdefault("tick_count", 0)

    def _phase_cycle(self, fraction: float) -> str:
        """Compute active respiratory phase from fraction within breath cycle."""
        if fraction < self.PHASE_INSPIRATION_END:
            return "inspiration"
        elif fraction < self.PHASE_EXPIRATION_END:
            return "expiration"
        else:
            return "pause"

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # ---- Pain input ----
        pain_signal = prior.get("BrainRunner", {}).get("pain_signal", 0.0)
        gut_distress = prior.get("GutSignalRelay", {}).get("gut_distress", 0.0)
        total_pain = max(pain_signal, gut_distress)

        # ---- Mu-opioid suppression (simulates opioid analgesia) ----
        # If GutSignalRelay reports opioid-like suppression
        gut_suppressed = prior.get("GutSignalRelay", {}).get("opioid_suppressed", False)
        pain_suppressed = total_pain < 0.15 or gut_suppressed

        # ---- Arousal modulation ----
        # High arousal elevates baseline respiratory drive
        arousal_level = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        arousal_modulation = (arousal_level - 0.5) * 0.10

        # ---- Compute target respiratory parameters ----
        if pain_suppressed:
            target_rr = self.RESTING_RR + arousal_modulation
            target_tv = self.RESTING_TV
        else:
            # Pain hyperventilation: elevated rate, suppressed tidal volume (rapid shallow)
            rr_elevation = total_pain * self.PAIN_RR_ELEVATION
            tv_suppression = total_pain * self.PAIN_TV_SUPPRESSION
            target_rr = min(0.95, self.RESTING_RR + rr_elevation + arousal_modulation)
            target_tv = max(0.25, self.RESTING_TV - tv_suppression)

        # ---- Smooth convergence ----
        current_rr = self.state["respiratory_rate_index"]
        new_rr = current_rr + (target_rr - current_rr) * self.RR_CONVERGENCE
        new_rr = round(new_rr, 4)

        current_tv = self.state["tidal_volume_index"]
        new_tv = current_tv + (target_tv - current_tv) * self.TV_CONVERGENCE
        new_tv = round(new_tv, 4)

        # ---- Minute ventilation index (RR × TV approximation) ----
        new_mvi = round(new_rr * new_tv, 4)

        # ---- Phase cycling ----
        # Advance phase fraction based on RR (higher RR = faster cycling)
        # Normalize: at RESTING_RR, one full cycle takes ~20 ticks
        # at MAX_RR (~0.95), one cycle takes ~5 ticks
        cycle_speed = 0.05 + new_rr * 0.30  # fraction advanced per tick
        current_fraction = self.state["phase_fraction"]
        new_fraction = (current_fraction + cycle_speed) % 1.0
        active_phase = self._phase_cycle(new_fraction)

        # Persist
        self.state["respiratory_rate_index"] = new_rr
        self.state["tidal_volume_index"] = new_tv
        self.state["minute_ventilation_index"] = new_mvi
        self.state["pain_suppressed"] = pain_suppressed
        self.state["phase_fraction"] = new_fraction
        self.state["active_phase"] = active_phase
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "respiratory_rate_index": new_rr,
            "tidal_volume_index": new_tv,
            "minute_ventilation_index": new_mvi,
            "pain_suppressed": pain_suppressed,
            "active_phase": active_phase,
        }

"""
Foundational018: VagalRestPromoter

Neural substrate: Dorsal motor nucleus of the vagus (DMNV) and nucleus ambiguus (nAmb)
in the medulla — primary parasympathetic output nuclei.

DMNV projects via the vagus nerve (CN X) to cardiac pacemakers (via intrathoracic ganglia),
lungs, esophagus, and abdominal viscera. nAmb specifically projects to the SA and AV nodes
of the heart for cardiac parasympathetic (bradycardic) control.

The vagus nerve carries ~90% afferent fibers (visceral sensory → NTS) and 10% efferent
motor fibers. Vagal tone is the dominant resting state of cardiac autonomic balance
(rest-and-digest).

CITATIONS:
    PMC4254943 — Tjen-A-Looi SC, Guo ZL, Longhurst JC (2014). GABA in Nucleus Tractus
        Solitarius Participates in Electroacupuncture Modulation of Cardiopulmonary
        Bradycardia Reflex. J Neurophysiol.
    PMC7755078 — Navickaite I, Pauziene N, Pauza DH (2021). Anatomical Evidence of
        Non-Parasympathetic Cardiac Nitrergic Nerve Fibres in Rat. Sci Rep.
"""

from brain.base_mechanism import BrainMechanism


class VagalRestPromoter(BrainMechanism):
    """
    DMNV + nucleus ambiguus — vagal parasympathetic rest promoter.

    Vagal tone drives cardiac parasympathetic output, GI motor activity, and HRV.
    Vagal withdrawal (stress, inflammation, orexin/waking) shifts autonomic balance
    toward sympathetic dominance.
    """

    def __init__(self):
        super().__init__(
            name="VagalRestPromoter",
            human_analog="DMNV + nucleus ambiguus — vagal parasympathetic rest promoter",
            layer="foundational",
        )

        # Internal state
        self.state["cardiac_vagal_tone"] = 0.40
        self.state["gastric_motor_tone"] = 0.35
        self.state["hrv_index"] = 0.40
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        """
        Compute vagal parasympathetic outputs based on autonomic and neuromodulatory inputs.

        Inputs expected from prior_results:
            - BaroreflexTone   (float 0–1): baroreceptor firing rate
            - MetabolicRate    (float 0–1): metabolic / sympathetic drive
            - CytokineSignal   (float 0–1): inflammatory cytokine load
            - LimbicDrive      (float 0–1): limbic / paralimbic top-down drive
            - OrexinLevel      (float 0–1): wak-promoting orexin tone

        Defaults:
            baroreflex=0.50, metabolic=0.30, cytokine=0.0, limbic=0.20, orexin=0.20
        """
        self.state["tick_count"] += 1

        # --- Unpack inputs ---
        baroreflex = float(input_data.get("BaroreflexTone", 0.50))
        metabolic = float(input_data.get("MetabolicRate", 0.30))
        cytokine = float(input_data.get("CytokineSignal", 0.0))
        limbic = float(input_data.get("LimbicDrive", 0.20))
        orexin = float(input_data.get("OrexinLevel", 0.20))

        # --- 1. Cardiac Vagal Tone (leaky integrator) ---
        # Base from baroreceptor-HRV reflex; suppressed by cytokine, orexin, limbic override.
        raw_tone = (
            baroreflex * 0.50
            - cytokine * 0.15
            - orexin * 0.20
            - limbic * 0.10
        )
        # Leaky integration toward computed raw_tone (alpha = 0.8)
        cardiac_vagal_tone = self._leaky_update("cardiac_vagal_tone", raw_tone, alpha=0.8)

        # --- 2. Gastric Motor Tone ---
        # Parasympathetic gut activation driven by vagal output.
        raw_gastric = cardiac_vagal_tone * 0.60
        gastric_motor_tone = self._leaky_update("gastric_motor_tone", raw_gastric, alpha=0.8)

        # --- 3. Respiratory Sinoaortic Reflex ---
        # Baroreflex-HRV coupling strengthened when metabolic demand is low.
        respiratory_sinoaortic_reflex = float(
            baroreflex * 0.40 + (1.0 - metabolic) * 0.30
        )

        # --- 4. HRV Index ---
        # High vagal tone = high heart rate variability = healthy autonomic state.
        raw_hrv = cardiac_vagal_tone * 0.60
        hrv_index = self._leaky_update("hrv_index", raw_hrv, alpha=0.8)

        # --- 5. Visceral Autonomic Balance ---
        # +1 = parasympathetic-dominant, -1 = sympathetic-dominant.
        # Baseline: vagal=0.40, metabolic=0.30, orexin=0.20 → balance ≈ (0.40-0.20)/0.80 = 0.25
        balance = cardiac_vagal_tone - (metabolic * 0.4 + orexin * 0.4)
        # Normalize to [-1, 1] — max theoretical range is -1 to +1 (when vagal=1, met+orex=0 → +1)
        raw_range = 1.0  # conservative normalization bound
        visceral_autonomic_balance = max(-1.0, min(1.0, balance / raw_range))

        # --- Persist state ---
        self.state["cardiac_vagal_tone"] = cardiac_vagal_tone
        self.state["gastric_motor_tone"] = gastric_motor_tone
        self.state["respiratory_sinoaortic_reflex"] = respiratory_sinoaortic_reflex
        self.state["hrv_index"] = hrv_index
        self.state["visceral_autonomic_balance"] = visceral_autonomic_balance
        self.persist_state()

        return {
            "cardiac_vagal_tone": cardiac_vagal_tone,
            "gastric_motor_tone": gastric_motor_tone,
            "respiratory_sinoaortic_reflex": respiratory_sinoaortic_reflex,
            "hrv_index": hrv_index,
            "visceral_autonomic_balance": visceral_autonomic_balance,
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _leaky_update(self, key: str, target: float, alpha: float = 0.8) -> float:
        """
        Exponential moving average (EMA) update toward a target value.

        Args:
            key:    state key to read/write
            target: computed target value
            alpha:  update weight (1 = full replacement, 0 = no update)

        Returns:
            Updated float value clamped to [0.0, 1.0].
        """
        current = float(self.state.get(key, 0.0))
        updated = current + alpha * (target - current)
        return max(0.0, min(1.0, updated))
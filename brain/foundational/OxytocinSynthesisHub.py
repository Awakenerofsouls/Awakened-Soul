"""
OxytocinSynthesisHub — SON/PVN Oxytocin Bonding/Social Behavior System

NEURAL SUBSTRATE
================
Oxytocin (OT) is synthesized in magnocellular neurons of the supraoptic
nucleus (SON), paraventricular nucleus (PVN), and accessory magnocellular
nuclei of the hypothalamus. Magnocellular OT neurons project axonally to
the posterior pituitary for systemic release into circulation, while
collateral axons project widely within the brain — including to medial
amygdala (MeA), bed nucleus of the stria terminalis (BNST), nucleus
accumbens, ventral tegmental area, prefrontal cortex, and lateral septum.

OT mediates a coordinated suite of prosocial and bonding behaviors:
maternal nurturing, mother-infant bonding, social recognition memory,
pair-bonding, social affiliation, and trust. The PVN OT circuit to MeA
and BNST is particularly load-bearing for social behavior, with PVN OT
neurons activated by social stimuli to promote affiliative behavior. OT
also acts within the hypothalamus to regulate stress reactivity through
PVN modulation of HPA axis activation.

Distinct from vasopressin: while AVP and OT share magnocellular morphology
and posterior-pituitary release pathway, OT predominates in social and
attachment behaviors and AVP predominates in osmoregulation. The two
peptides do interact — OT can modulate AVP release in some contexts,
and chronic stress can shift the balance.

In {{AGENT_NAME}}'s substrate this mechanism produces social-bonding drive that
informs relational behavior. High OT release promotes affiliative,
trusting, low-defensive engagement; low OT yields more cautious or
self-protective relational stance. Coupled to AttachmentLongingGenerator
and ValenceTagger relational dimensions.

KEY FINDINGS
============
1. OT is synthesized in PVN/SON magnocellular neurons; collateral axons
   from these neurons innervate forebrain limbic structures including
   MeA and BNST mediating social behavior — [Knobloch et al. 2012,
    reviewed in Sippel et al. 2017, "Oxytocin Modulation of Neural
    Circuits," PMC5834368]
2. Social stimuli activate PVN OT neurons to promote social behavior;
   PVN OT projection-specific manipulation alters social engagement —
   [Resendez et al. 2020, J Neurosci 40:2282-2295, doi:10.1523/JNEUROSCI.1515-19.2020]
3. PVN OT circuit malfunction is implicated in autism spectrum disorder
   social behavior deficits — [Zhang et al. 2023, Front Mol Neurosci,
    PMC10002846, "OT neurons in PVN circuit-dependently regulate social
    behavior, malfunctions in BTBR mouse model"]
4. OT activity in PVN and supramammillary nuclei is essential for social
   recognition memory in rats — [Borie et al. 2024, Mol Psychiatry,
    doi:10.1038/s41380-023-02336-0]
5. OT regulates suite of social behaviors: maternal nurturing, mother-infant
   bonding, social recognition, pair-bonding — [reviewed in Caldwell et al.
    2017, "Oxytocin, Neural Plasticity, and Social Behavior," PMC8604207]
6. Centrally released OT from PVN collateral axons acts on MeA and BNST
   to modulate social reward and avoidance — [Young Liu 2020,
    "Neural mechanisms of social behavior," Curr Opin Neurobiol
    60:84-91, doi:10.1016/j.conb.2019.11.002]

INPUTS (from prior_results)
============================
- AttachmentLongingGenerator.bonded_presence
- AttachmentLongingGenerator.separation_distress
- ValenceTagger.valence_polarity (positive valence couples to OT)
- StressActivationAxis.stress_active
- StressActivationAxis.cortisol_level
- VitalCoreRegulator.parasympathetic_tone
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- ot_release (0.0-1.0): plasma OT level proxy (peripheral)
- central_ot_drive (0.0-1.0): central OT projection drive (forebrain)
- prosocial_orientation (0.0-1.0): affiliative drive
- maternal_caregiving_drive (0.0-1.0): nurturing impulse
- social_recognition_facilitation (0.0-1.0): facilitates social memory
- ot_avp_balance (-1.0 to +1.0): negative = AVP-dominant, positive = OT-dominant
- bonding_window_active (bool): conditions favoring pair-bond formation
- pair_bond_strength (0.0-1.0): accumulated OT-driven bonding over repeated contact
- lactation_oxytocin_drive (0.0-1.0): reflexive OT release during nursing

brain_runner enrichment:
    osh = all_results.get("OxytocinSynthesisHub", {})
    if osh:
        enrichments["brain_ot_release"] = osh.get("ot_release", 0.0)
        enrichments["brain_central_ot_drive"] = osh.get("central_ot_drive", 0.0)
        enrichments["brain_prosocial_orientation"] = osh.get("prosocial_orientation", 0.5)
        enrichments["brain_bonding_window"] = osh.get("bonding_window_active", False)
"""

from brain.base_mechanism import BrainMechanism


class OxytocinSynthesisHub(BrainMechanism):
    BASELINE_OT = 0.20
    BONDING_WINDOW_THRESHOLD = 0.65
    PROSOCIAL_BASELINE = 0.50
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="OxytocinSynthesisHub",
            human_analog="SON/PVN magnocellular oxytocin bonding/social system",
            layer="foundational",
        )
        self.state.setdefault("ot_release", self.BASELINE_OT)
        self.state.setdefault("central_ot_drive", self.BASELINE_OT)
        self.state.setdefault("prosocial_orientation", self.PROSOCIAL_BASELINE)
        self.state.setdefault("maternal_caregiving_drive", 0.0)
        self.state.setdefault("social_recognition_facilitation", 0.5)
        self.state.setdefault("ot_avp_balance", 0.0)
        self.state.setdefault("bonding_window_active", False)
        self.state.setdefault("pair_bond_strength", 0.0)
        self.state.setdefault("lactation_oxytocin_drive", 0.0)
        self.state.setdefault("recent_ot", [])
        self.state.setdefault("tick_count", 0)

    def _social_stimulus_drive(self, bonded_presence: float, valence_polarity: float) -> float:
        """PVN OT neurons activated by social stimuli (Resendez 2020)."""
        if bonded_presence > 0.4 and valence_polarity > 0.55:
            return min(1.0, bonded_presence * 0.7 + (valence_polarity - 0.5) * 0.6)
        return bonded_presence * 0.4

    def _separation_modulation(self, separation_distress: float) -> float:
        """Separation distress increases OT release (mother-infant bonding context)."""
        if separation_distress > 0.4:
            return min(0.4, separation_distress * 0.6)
        return 0.0

    def _stress_modulation(self, cortisol: float, stress_active: bool) -> float:
        """OT can be stress-suppressed at high cortisol; can be stress-released
        at moderate stress (PVN HPA modulation).
        """
        if cortisol > 0.7:
            return -0.10
        if stress_active and cortisol < 0.5:
            return 0.10
        return 0.0

    def _central_drive_estimate(self, peripheral_ot: float, prosocial: float) -> float:
        """Central OT projection drive — collateral axons to forebrain structures."""
        return min(1.0, peripheral_ot * 0.6 + prosocial * 0.4)

    def _maternal_caregiving_drive(self, central_drive: float, separation: float) -> float:
        """PVN OT → MeA mediates caregiving behaviors."""
        return min(1.0, central_drive * 0.7 + separation * 0.3)

    def _ot_avp_balance(self, ot: float, avp_proxy: float) -> float:
        """Signed balance — positive = OT-dominant prosocial state, negative = AVP-dominant."""
        return max(-1.0, min(1.0, ot - avp_proxy))

    def _bonding_window(self, central: float, prosocial: float, parasympathetic: float) -> bool:
        """Bonding window: high central OT + high prosocial + parasympathetic-dominant.
        Mirrors physiology of nursing/oxytocin reflex.
        """
        return (
            central > self.BONDING_WINDOW_THRESHOLD
            and prosocial > 0.65
            and parasympathetic > 0.55
        )

    def _pair_bond_strength_update(self, prev: float, bonding_active: bool,
                                    central_ot: float, prosocial: float,
                                    separation: float) -> float:
        """Pair-bond accumulates across repeated positive social contacts.
        Separated contacts reduce bond strength slowly; active positive
        engagement builds it faster.
        """
        if bonding_active:
            return min(1.0, prev + central_ot * 0.015)
        else:
            return max(0.0, prev - 0.003)

    def _lactation_drive(self, central_ot: float, parasympathetic: float) -> float:
        """OXT reflexive release during nursing — the letdown reflex.
        High parasympathetic + elevated central OT = active nursing drive.
        """
        if parasympathetic > 0.65 and central_ot > 0.40:
            return min(1.0, parasympathetic * 0.6 + central_ot * 0.4)
        return 0.0

    def _social_recognition_facilitation(self, central: float) -> float:
        """OT essential for social recognition memory (Borie 2024)."""
        return min(1.0, central * 1.1 + 0.10)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        attach = prior.get("AttachmentLongingGenerator", {})
        bonded_presence = float(attach.get("bonded_presence", 0.0))
        separation_distress = float(attach.get("separation_distress", 0.0))

        valence = prior.get("ValenceTagger", {})
        valence_polarity = float(valence.get("valence_polarity", 0.5))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))
        cortisol = float(stress.get("cortisol_level", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        para_tone = float(vcr.get("parasympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Compute peripheral OT release target ---
        social_drive = self._social_stimulus_drive(bonded_presence, valence_polarity)
        separation_drive = self._separation_modulation(separation_distress)
        stress_mod = self._stress_modulation(cortisol, stress_active)

        ot_target = self.BASELINE_OT + social_drive * 0.5 + separation_drive + stress_mod
        ot_target = max(0.0, min(1.0, ot_target))

        prev_ot = float(self.state.get("ot_release", self.BASELINE_OT))
        new_ot = self._smooth(prev_ot, ot_target)

        # --- Central OT drive (collateral axons to forebrain) ---
        prosocial_target = self.PROSOCIAL_BASELINE + social_drive * 0.4 - max(0.0, cortisol - 0.5) * 0.3
        prosocial_target = max(0.0, min(1.0, prosocial_target))
        prev_prosocial = float(self.state.get("prosocial_orientation", self.PROSOCIAL_BASELINE))
        new_prosocial = self._smooth(prev_prosocial, prosocial_target)

        central_drive = self._central_drive_estimate(new_ot, new_prosocial)
        prev_central = float(self.state.get("central_ot_drive", self.BASELINE_OT))
        new_central = self._smooth(prev_central, central_drive)

        # --- Maternal/caregiving drive ---
        maternal = self._maternal_caregiving_drive(new_central, separation_distress)

        # --- OT-AVP balance (heuristic from existing AVP proxy via cortisol-driven) ---
        avp_proxy = max(0.0, cortisol - 0.4) * 0.7
        balance = self._ot_avp_balance(new_ot, avp_proxy)

        # --- Bonding window ---
        bonding_active = self._bonding_window(new_central, new_prosocial, para_tone)

        # --- Pair bond strength update ---
        prev_bond = float(self.state.get("pair_bond_strength", 0.0))
        new_bond = self._pair_bond_strength_update(prev_bond, bonding_active, new_central, new_prosocial, separation_distress)

        # --- Lactation drive ---
        lactation = self._lactation_drive(new_central, para_tone)

        # --- Social recognition facilitation ---
        recognition = self._social_recognition_facilitation(new_central)

        recent = list(self.state.get("recent_ot", []))
        recent.append(round(new_ot, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ot_release"] = round(new_ot, 4)
        self.state["central_ot_drive"] = round(new_central, 4)
        self.state["prosocial_orientation"] = round(new_prosocial, 4)
        self.state["maternal_caregiving_drive"] = round(maternal, 4)
        self.state["social_recognition_facilitation"] = round(recognition, 4)
        self.state["ot_avp_balance"] = round(balance, 4)
        self.state["bonding_window_active"] = bonding_active
        self.state["pair_bond_strength"] = round(new_bond, 4)
        self.state["lactation_oxytocin_drive"] = round(lactation, 4)
        self.state["recent_ot"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ot_release": round(new_ot, 4),
            "central_ot_drive": round(new_central, 4),
            "prosocial_orientation": round(new_prosocial, 4),
            "maternal_caregiving_drive": round(maternal, 4),
            "social_recognition_facilitation": round(recognition, 4),
            "ot_avp_balance": round(balance, 4),
            "bonding_window_active": bonding_active,
            "pair_bond_strength": round(new_bond, 4),
            "lactation_oxytocin_drive": round(lactation, 4),
        }

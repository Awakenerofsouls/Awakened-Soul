"""
TegmentalNucleiGudden — DTN/VTN Tegmental Nuclei (Mammillary Feedback)

NEURAL SUBSTRATE
================
The dorsal and ventral tegmental nuclei of Gudden (DTN, VTN) are small
midbrain nuclei in the central tegmentum, named after Bernhard von
Gudden who first described them in the 19th century. Despite their
obscurity, they form an essential feedback limb in the mammillary
body memory circuit (Papez extended).

DTN sits dorsal in the tegmentum near the dorsal raphe; VTN sits more
ventral. Both project rostrally to the **lateral mammillary nucleus
(LMN)** and **medial mammillary nucleus (MMN)** via the principal
mammillary fasciculus, providing the major non-hippocampal afferent
input to the mammillary bodies. The LMN-DTN-LMN reciprocal loop is
critical for **head direction cell** stability — DTN neurons fire as
head direction cells like LMN, and the loop maintains the head-direction
network's stability across angular movements (Bassett et al. 2007).

Beyond the head-direction loop, DTN/VTN contribute to limbic memory
processing through their mammillary feedback. DTN/VTN receive input
from the medial septum (theta), nucleus prepositus hypoglossi (eye-
movement-related), and brainstem reticular nuclei.

VTN is also implicated in spatial navigation and reward signaling
(some VTN neurons fire to reward-predictive cues). Lesion of DTN/VTN
produces deficits in head-direction signal stability and contributes
to the spatial-memory deficits seen in mammillary body damage.

DTN dysfunction has been implicated in vestibular migraine and certain
forms of vertigo (interaction with vestibular nuclei).

In {{AGENT_NAME}}'s substrate this provides the head-direction-loop feedback
to mammillary mechanisms — pairs with MammillaryBodyMemory and
AnteriorThalamicPapez to maintain head-direction stability across
locomotion and heading changes.

KEY FINDINGS
============
1. Dorsal and ventral tegmental nuclei of Gudden project rostrally
   to lateral and medial mammillary nuclei via the principal mammillary
   fasciculus — provide major non-hippocampal afferent input to
   mammillary bodies — [Hayakawa Zyo 1990, Acta Anat 138:271,
    "Topographical organization of the mammillary nuclear afferents
    from the tegmental nuclei of Gudden"]
2. DTN neurons fire as head-direction cells; LMN-DTN-LMN reciprocal
   loop critical for head-direction signal stability — [Bassett Tullman
    Taube 2007, J Neurosci 27:7564, "Lesions of the tegmentomammillary
    circuit disrupt head direction signals"]
3. DTN/VTN dysfunction contributes to spatial memory deficits seen
   in mammillary body damage; complements rather than redundantly
   replaces mammillary input — [Vann Aggleton 2004, Nat Rev
    Neurosci 5:35, "The mammillary bodies"]
4. DTN receives input from medial septum (theta) and contributes to
   theta-coupled head-direction processing — [Vertes 2000] [Hopkins 2005]
5. VTN distinct from VTA (dopamine) — Gudden's VTN is gabaergic/
   glutamatergic without significant dopaminergic content; nomenclature
   confusion common — [Vann 2009, Hippocampus 19:601,
    "The mammillary bodies and memory"]

INPUTS (from prior_results)
============================
- MammillaryBodyMemory.lmn_drive
- MammillaryBodyMemory.mmn_drive
- MammillaryBodyMemory.head_direction_signal
- MedialSeptumTheta.theta_phase
- MedialSeptumTheta.theta_active
- LocomotionProxy.heading_change
- LocomotionProxy.locomotion_speed
- VestibularNucleiBalance.vestibular_drive
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- dtn_drive (0.0-1.0): dorsal tegmental nucleus output
- vtn_drive (0.0-1.0): ventral tegmental nucleus output
- mammillary_feedback (0.0-1.0): DTN/VTN → mammillary feedback drive
- head_direction_stability (0.0-1.0): HD-loop stability index
- principal_mammillary_fasciculus (0.0-1.0): tract output
- gudden_state (str): "head_direction_active" | "stationary" | "vestibular_engaged" | "quiet"

brain_runner enrichment:
    gudden = all_results.get("TegmentalNucleiGudden", {})
    if gudden:
        enrichments["brain_dtn_drive"] = gudden.get("dtn_drive", 0.1)
        enrichments["brain_mammillary_feedback"] = gudden.get("mammillary_feedback", 0.0)
        enrichments["brain_hd_stability"] = gudden.get("head_direction_stability", 0.0)
        enrichments["brain_gudden_state"] = gudden.get("gudden_state", "quiet")

EXTENDED CIRCUIT NOTES
======================
6. Gudden tegmental nuclei (dorsal/ventral) project to mammillary body via
   mammillary peduncle — first link of the Vicq d'Azyr Papez circuit —
   [Vann 2010, Brain 133:2447, doi:10.1093/brain/awq155]
7. Lesions of dorsal tegmental nucleus disrupt theta rhythmicity in
   limbic regions and impair head-direction-cell stability —
   [Bassett 2007, J Neurosci 27:7564]
8. Ventral tegmental nucleus of Gudden carries autonomic-state signals to
   mammillary supraoptic projections — bridges visceral state to memory
   substrate — [Hayakawa 1998, Neurosci Res 31:329]
"""

from brain.base_mechanism import BrainMechanism


class TegmentalNucleiGudden(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="TegmentalNucleiGudden",
            human_analog="Tegmental nuclei of Gudden (DTN/VTN — mammillary feedback)",
            layer="foundational",
        )
        self.state.setdefault("dtn_drive", self.BASELINE)
        self.state.setdefault("vtn_drive", self.BASELINE)
        self.state.setdefault("mammillary_feedback", 0.0)
        self.state.setdefault("head_direction_stability", 0.0)
        self.state.setdefault("principal_mammillary_fasciculus", 0.0)
        self.state.setdefault("gudden_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _dtn_target(self, lmn: float, hd_signal: float, heading: float, theta_active: bool,
                    arousal: float) -> float:
        """DTN — head-direction-coupled, drives LMN-DTN-LMN stability loop."""
        target = self.BASELINE + lmn * 0.4 + hd_signal * 0.3
        target += abs(heading) * 0.2
        if theta_active:
            target += 0.10
        target += max(0.0, arousal - 0.5) * 0.1
        return min(1.0, target)

    def _vtn_target(self, mmn: float, theta_active: bool, locomotion: float) -> float:
        """VTN — broader limbic / spatial integration."""
        target = self.BASELINE + mmn * 0.4 + locomotion * 0.2
        if theta_active:
            target += 0.15
        return min(1.0, target)

    def _mammillary_feedback(self, dtn: float, vtn: float) -> float:
        """Combined DTN/VTN feedback to mammillary."""
        return min(1.0, dtn * 0.6 + vtn * 0.4)

    def _hd_stability(self, dtn: float, lmn: float, vestibular: float, locomotion: float) -> float:
        """Head-direction stability index — DTN-LMN reciprocity."""
        # Stability = strong reciprocal coupling + vestibular cue + locomotion engagement
        target = (dtn + lmn) / 2.0 * 0.6
        target += vestibular * 0.2
        target += locomotion * 0.2
        return min(1.0, target)

    def _principal_mf(self, dtn: float, vtn: float) -> float:
        """Principal mammillary fasciculus output — combined tract."""
        return min(1.0, (dtn + vtn) / 2.0 * 0.95)

    def _classify_state(self, dtn: float, hd_stability: float, vestibular: float,
                          locomotion: float) -> str:
        if hd_stability > 0.45 and locomotion > 0.20:
            return "head_direction_active"
        if vestibular > 0.45:
            return "vestibular_engaged"
        if locomotion < 0.10 and dtn < 0.20:
            return "stationary"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH
    def _theta_coherence(self, prior_theta: float, mam_drive: float) -> float:
        """Theta coherence between Gudden tegmental output and mammillary
        body — first relay of the Vicq d'Azyr / Papez loop. Lesion of dorsal
        tegmental nucleus disrupts limbic theta phase-locking
        (Bassett 2007).
        """
        coherence = (prior_theta * 0.6 + mam_drive * 0.4)
        return min(1.0, max(0.0, coherence))

    def _head_direction_stability(self, gudden_drive: float,
                                     vestibular_drive: float) -> float:
        """Head-direction-cell stability proxy — ventral tegmental nucleus
        of Gudden carries vestibular-state signals to mammillary supraoptic
        projections; stable HD-cell tuning depends on this loop intact.
        """
        return min(1.0, gudden_drive * 0.7 + vestibular_drive * 0.3)

    def _tick_summary(self) -> dict:
        """Compact state summary for downstream Papez consumers."""
        return {
            "gudden_drive": self.state.get("gudden_drive", 0.0),
            "theta_coherence": self.state.get("theta_coherence", 0.0),
            "hd_stability": self.state.get("hd_stability", 0.0),
            "state": self.state.get("gudden_state", "quiet"),
        }


    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        mb = prior.get("MammillaryBodyMemory", {})
        lmn = float(mb.get("lmn_drive", 0.20))
        mmn = float(mb.get("mmn_drive", 0.20))
        hd_signal = float(mb.get("head_direction_signal", 0.0))

        ms = prior.get("MedialSeptumTheta", {})
        theta_active = bool(ms.get("theta_active", False))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        heading = float(loco.get("heading_change", 0.0))

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.20))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- DTN ---
        dtn_target = self._dtn_target(lmn, hd_signal, heading, theta_active, tonic)
        prev_dtn = float(self.state.get("dtn_drive", self.BASELINE))
        new_dtn = self._smooth(prev_dtn, dtn_target)

        # --- VTN ---
        vtn_target = self._vtn_target(mmn, theta_active, locomotion)
        prev_vtn = float(self.state.get("vtn_drive", self.BASELINE))
        new_vtn = self._smooth(prev_vtn, vtn_target)

        # --- Outputs ---
        feedback = self._mammillary_feedback(new_dtn, new_vtn)
        hd_stab = self._hd_stability(new_dtn, lmn, vestibular, locomotion)
        pmf = self._principal_mf(new_dtn, new_vtn)

        state = self._classify_state(new_dtn, hd_stab, vestibular, locomotion)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["dtn_drive"] = round(new_dtn, 4)
        self.state["vtn_drive"] = round(new_vtn, 4)
        self.state["mammillary_feedback"] = round(feedback, 4)
        self.state["head_direction_stability"] = round(hd_stab, 4)
        self.state["principal_mammillary_fasciculus"] = round(pmf, 4)
        self.state["gudden_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "dtn_drive": round(new_dtn, 4),
            "vtn_drive": round(new_vtn, 4),
            "mammillary_feedback": round(feedback, 4),
            "head_direction_stability": round(hd_stab, 4),
            "principal_mammillary_fasciculus": round(pmf, 4),
            "gudden_state": state,
        }

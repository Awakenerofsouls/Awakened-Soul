"""
ParabrachialTasteVisceral — Parabrachial Nucleus Taste/Visceral/CGRP Alarm

NEURAL SUBSTRATE
================
The parabrachial nuclei (PBN) of the dorsolateral pons surround the superior
cerebellar peduncle and serve as a major sensory relay for taste, visceral
malaise, temperature, pain, and itch ascending toward forebrain. PBN divides
into medial (mPBN) and lateral (lPBN) subdivisions with distinct functions:

mPBN — relays gustatory (taste) information from NTS to the parvocellular
ventroposterior taste thalamus (VPMpc) and onward to gustatory cortex.

lPBN — relays viscerosensory information including visceral malaise, pain,
temperature, and itch to amygdala (CeA), hypothalamus, BNST, and thalamus.
The lPBN is thus the principal gateway for interoceptive aversive signals.

Within lPBN, a population of CGRP+ neurons functions as a "general alarm" —
they integrate diverse threat signals (pain, hypoxia, hypercapnia, hypoglycemia,
visceral malaise, temperature stress) and project to CeA to drive defensive,
fear, and aversive behavior. CGRP+ PBN neurons also control meal termination
(satiety) and signal nausea-related anorexia.

PBN receives ascending input from spinal lamina I (nociceptive), NTS (taste,
visceral), and trigeminal sensory complex (face/oral) and modulates breathing
through the Kölliker-Fuse subnucleus.

In Nova's substrate this is the integrative aversive-interoceptive relay —
combining multiple aversive signals into a single "general alarm" output that
drives downstream affect and defense.

KEY FINDINGS
============
1. PBN relays sensory information (visceral malaise, taste, temperature, pain,
   itch) to forebrain — thalamus, hypothalamus, extended amygdala —
   [Norgren 1995, Brain Res Brain Res Rev; reviewed Wikipedia/Parabrachial
    nuclei; ScienceDirect "Parabrachial Nucleus" overview]
2. PBN CGRP+ neurons function as a "general alarm" integrating diverse threat
   signals — [Palmiter 2018, Trends Neurosci 41:280-293, "The Parabrachial
    Nucleus: CGRP Neurons Function as a General Alarm" PMC5929477]
3. PBN is a hub for pain and aversion processing through projections to CeA
   and BNST — [Chiang Bourgeois Bunde 2019, J Neurosci 39:8225-8230,
    doi:10.1523/JNEUROSCI.1162-19.2019]
4. Parabrachial CGRP neurons control meal termination — engaged by
   satiety/nausea signals to suppress feeding — [Campos et al. 2016,
    Nat Neurosci 19:1628-1635, doi:10.1038/nn.4392]
5. mPBN relays gustatory information from NTS to taste thalamus while
   lPBN relays viscerosensory information; functional split between
   subdivisions — [Norgren Nauta in taste neurobiology reviews]
6. Kölliker-Fuse (KF) subnucleus of PBN modulates respiratory pattern —
   PBN-KF is the principal site for threat-driven respiratory suppression
   and the link between interoceptive alarm and respiratory control —
   [Dutschmann Herbert 2021, Respir Physiol Neurobiol 290:103680,
    doi:10.1016/j.resp.2021.103680]

INPUTS (from prior_results)
============================
- AreaPostremaToxinGuard.aversive_interoceptive_signal
- AreaPostremaToxinGuard.nausea_intensity
- DescendingPainGate.expected_pain_modulation
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- ThermoregulationCore.thermal_drive
- CarotidBodyChemosensor.hypoxia_response_active
- AppetiteNPYBalancer.energy_balance_signed
- AppetiteNPYBalancer.post_prandial

OUTPUTS (to brain_runner enrichment)
=====================================
- mpbn_taste_relay (0.0-1.0): gustatory relay drive
- lpbn_visceral_relay (0.0-1.0): viscerosensory relay drive
- cgrp_alarm_drive (0.0-1.0): general alarm output to CeA
- cea_aversive_drive (0.0-1.0): downstream CeA recruitment
- meal_termination_signal (0.0-1.0): satiety/nausea-driven feeding suppression
- nociceptive_relay (0.0-1.0): spinal lamina I → forebrain
- kf_respiratory_modulation (0.0-1.0): KF subnucleus respiratory gating
- alarm_state_active (bool)

brain_runner enrichment:
    pbtv = all_results.get("ParabrachialTasteVisceral", {})
    if pbtv:
        enrichments["brain_cgrp_alarm"] = pbtv.get("cgrp_alarm_drive", 0.0)
        enrichments["brain_pbn_aversive"] = pbtv.get("cea_aversive_drive", 0.0)
        enrichments["brain_meal_termination"] = pbtv.get("meal_termination_signal", 0.0)
        enrichments["brain_pbn_alarm_state"] = pbtv.get("alarm_state_active", False)
"""

from brain.base_mechanism import BrainMechanism


class ParabrachialTasteVisceral(BrainMechanism):
    ALARM_THRESHOLD = 0.55
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="ParabrachialTasteVisceral",
            human_analog="Parabrachial nucleus (medial taste + lateral visceral + CGRP alarm)",
            layer="foundational",
        )
        self.state.setdefault("mpbn_taste_relay", 0.20)
        self.state.setdefault("lpbn_visceral_relay", 0.20)
        self.state.setdefault("cgrp_alarm_drive", 0.0)
        self.state.setdefault("cea_aversive_drive", 0.0)
        self.state.setdefault("meal_termination_signal", 0.0)
        self.state.setdefault("nociceptive_relay", 0.0)
        self.state.setdefault("kf_respiratory_modulation", 0.0)
        self.state.setdefault("alarm_state_active", False)
        self.state.setdefault("alarm_streak", 0)
        self.state.setdefault("recent_alarm", [])
        self.state.setdefault("tick_count", 0)

    def _mpbn_taste_drive(self, energy_balance: float, post_prandial: bool) -> float:
        """mPBN taste relay — engaged during taste processing and post-meal.
        Without real taste input use post-prandial as proxy.
        """
        if post_prandial:
            return 0.65
        if energy_balance > 0.2:
            return 0.40
        return 0.20

    def _lpbn_visceral_drive(self, aversive: float, nausea: float, expected_pain: float) -> float:
        """lPBN visceral relay — combines aversive interoceptive signals."""
        return min(1.0, aversive * 0.5 + nausea * 0.4 + max(0.0, expected_pain) * 0.3)

    def _cgrp_alarm_drive(self, threat: bool, valence_intensity: float, hypoxia: bool,
                          thermal_drive: float, nausea: float, energy_deficit: float) -> float:
        """CGRP+ neurons integrate diverse threat signals (Palmiter 2018)."""
        alarm = 0.0
        if threat:
            alarm += valence_intensity * 0.5
        if hypoxia:
            alarm += 0.30
        if abs(thermal_drive) > 1.0:
            alarm += 0.20
        alarm += nausea * 0.4
        if energy_deficit > 0.4:
            alarm += 0.20
        return min(1.0, alarm)

    def _cea_aversive_drive(self, cgrp_alarm: float) -> float:
        """CGRP-PBN → CeA — driving aversive/defensive output."""
        return min(1.0, cgrp_alarm * 1.05)

    def _meal_termination(self, cgrp_alarm: float, nausea: float, post_prandial: bool) -> float:
        """Campos 2016 — CGRP-PBN drives meal termination."""
        if post_prandial:
            return min(1.0, cgrp_alarm * 0.7 + nausea * 0.6)
        return min(1.0, cgrp_alarm * 0.5 + nausea * 0.5)

    def _nociceptive_relay(self, expected_pain: float, threat: bool) -> float:
        """Spinal lamina I → lPBN → CeA nociceptive relay."""
        if threat:
            return min(1.0, max(0.0, expected_pain) * 0.7 + 0.3)
        return max(0.0, expected_pain) * 0.6

    def _kf_respiratory_modulation(self, cgrp_alarm: float, hypoxia: bool) -> float:
        """Kölliker-Fuse subnucleus — modulates breathing in response to
        interoceptive alarm. Threat/hypoxia → reduced respiratory rate.
        """
        if hypoxia and cgrp_alarm > 0.3:
            return min(1.0, 0.75 + cgrp_alarm * 0.25)
        if cgrp_alarm > 0.5:
            return min(1.0, 0.45 + cgrp_alarm * 0.5)
        return cgrp_alarm * 0.6

    def _alarm_streak_update(self, alarm: float, prev_streak: int) -> int:
        """Track consecutive high-alarm ticks."""
        if alarm > self.ALARM_THRESHOLD:
            return prev_streak + 1
        return max(0, prev_streak - 2)

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ap = prior.get("AreaPostremaToxinGuard", {})
        aversive = float(ap.get("aversive_interoceptive_signal", 0.0))
        nausea = float(ap.get("nausea_intensity", 0.0))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        thermo = prior.get("ThermoregulationCore", {})
        thermal_drive = float(thermo.get("thermal_drive", 0.0))

        cb = prior.get("CarotidBodyChemosensor", {})
        hypoxia = bool(cb.get("hypoxia_response_active", False))

        appetite = prior.get("AppetiteNPYBalancer", {})
        energy_balance = float(appetite.get("energy_balance_signed", 0.0))
        post_prandial = bool(appetite.get("post_prandial", False))
        energy_deficit = max(0.0, -energy_balance)

        # --- Subnucleus drives ---
        mpbn_target = self._mpbn_taste_drive(energy_balance, post_prandial)
        lpbn_target = self._lpbn_visceral_drive(aversive, nausea, expected_pain)
        cgrp_target = self._cgrp_alarm_drive(threat_signal, valence_intensity, hypoxia,
                                              thermal_drive, nausea, energy_deficit)

        prev_mpbn = float(self.state.get("mpbn_taste_relay", 0.20))
        prev_lpbn = float(self.state.get("lpbn_visceral_relay", 0.20))
        prev_cgrp = float(self.state.get("cgrp_alarm_drive", 0.0))

        new_mpbn = self._smooth(prev_mpbn, mpbn_target)
        new_lpbn = self._smooth(prev_lpbn, lpbn_target)
        new_cgrp = self._smooth(prev_cgrp, cgrp_target)

        # --- Downstream CeA recruitment ---
        cea_drive = self._cea_aversive_drive(new_cgrp)

        # --- Meal termination signal ---
        meal_term = self._meal_termination(new_cgrp, nausea, post_prandial)

        # --- Nociceptive relay ---
        nociceptive = self._nociceptive_relay(expected_pain, threat_signal)

        # --- KF respiratory modulation ---
        kf_respiratory = self._kf_respiratory_modulation(new_cgrp, hypoxia)

        # --- Alarm state ---
        alarm_active = new_cgrp > self.ALARM_THRESHOLD
        prev_streak = int(self.state.get("alarm_streak", 0))
        streak = self._alarm_streak_update(new_cgrp, prev_streak)

        recent = list(self.state.get("recent_alarm", []))
        recent.append(round(new_cgrp, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["mpbn_taste_relay"] = round(new_mpbn, 4)
        self.state["lpbn_visceral_relay"] = round(new_lpbn, 4)
        self.state["cgrp_alarm_drive"] = round(new_cgrp, 4)
        self.state["cea_aversive_drive"] = round(cea_drive, 4)
        self.state["meal_termination_signal"] = round(meal_term, 4)
        self.state["nociceptive_relay"] = round(nociceptive, 4)
        self.state["kf_respiratory_modulation"] = round(kf_respiratory, 4)
        self.state["alarm_state_active"] = alarm_active
        self.state["alarm_streak"] = streak
        self.state["recent_alarm"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "mpbn_taste_relay": round(new_mpbn, 4),
            "lpbn_visceral_relay": round(new_lpbn, 4),
            "cgrp_alarm_drive": round(new_cgrp, 4),
            "cea_aversive_drive": round(cea_drive, 4),
            "meal_termination_signal": round(meal_term, 4),
            "nociceptive_relay": round(nociceptive, 4),
            "kf_respiratory_modulation": round(kf_respiratory, 4),
            "alarm_state_active": alarm_active,
        }
"""
RespiratoryPainIntegrator — Parabrachial / Kölliker-Fuse Affective-Respiratory Integration

NEURAL SUBSTRATE
================
The lateral parabrachial nucleus (LPB) and Kölliker-Fuse nucleus (KF) of the
dorsolateral pons are the principal site of integration between nociceptive,
thermoceptive, and respiratory signals. LPB receives ascending nociceptive
input from spinal lamina I dorsal-horn neurons and ascending visceral input
from NTS, then projects forward to the central nucleus of the amygdala (CeA)
and posterior thalamus, providing the affective-emotional dimension of pain.
KF projects back to preBötzinger complex and other brainstem respiratory
nuclei, modulating respiratory pattern in response to noxious or visceral
input — this is why painful stimuli alter breath rate and depth.

LPB also receives warm/cool spinal afferents (LPBd/LPBel split) and projects
to MnPO/POA, contributing thermoregulatory pain dimension. The CeA → LPB
descending connection enables affective state to modulate respiratory and
nociceptive processing — a major pathway by which fear and stress alter
breathing pattern (rapid shallow breathing under threat).

Functional output: provides a "respiratory-affective coupling" signal — how
much current respiratory pattern is being driven by aversive affective load.
This signal is the substrate for sigh generation, breath-holding under stress,
and "gut-feeling" interoceptive components of distress.

KEY FINDINGS
============
1. LPB projects to CeA conveying affective-pain dimension; lesions abolish
   nociceptive emotional response — [Han et al. 2015, Nature 519:357-361]
2. KF modulates preBötC respiratory pattern in response to visceral and
   nociceptive input — [Dutschmann Dick 2012, Compr Physiol 2:2443-2469]
3. LPBd/LPBel functional split routes warm vs cool afferents to MnPO —
   [Nakamura Morrison 2008, Nat Neurosci 11:62-71]
4. CeA → LPB descending input mediates affective modulation of breathing
   under fear states — [Yokota et al. 2015, J Comp Neurol]

INPUTS (from prior_results)
============================
- ValenceTagger.threat_signal
- ValenceTagger.valence_intensity
- VitalCoreRegulator.survival_threat_level
- RespiratoryPacemaker.breath_rate_hz
- RespiratoryPacemaker.inspiratory_drive_amplitude
- DescendingPainGate.expected_pain_modulation
- StressActivationAxis.stress_active

OUTPUTS
=======
- affective_resp_coupling (0.0-1.0): how much breath is being driven by affect
- sigh_imminent (bool): pattern indicates a sigh is due
- breath_holding (bool): inspiratory pause driven by threat
- pain_breath_pattern (str): "normal" | "rapid_shallow" | "guarded" | "sigh_recovery"
- ceA_to_lpb_drive (0.0-1.0)

brain_runner enrichment:
    rpi = all_results.get("RespiratoryPainIntegrator", {})
    if rpi:
        enrichments["brain_affective_resp_coupling"] = rpi.get("affective_resp_coupling", 0.0)
        enrichments["brain_sigh_imminent"] = rpi.get("sigh_imminent", False)
        enrichments["brain_breath_holding"] = rpi.get("breath_holding", False)
        enrichments["brain_pain_breath_pattern"] = rpi.get("pain_breath_pattern", "normal")
"""

from brain.base_mechanism import BrainMechanism


class RespiratoryPainIntegrator(BrainMechanism):
    SIGH_INTERVAL_TICKS = 90       # ~3 min at 2-sec ticks; physiological sigh interval
    BREATH_HOLD_THREAT_THRESHOLD = 0.65
    AFFECTIVE_COUPLING_BASELINE = 0.10

    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="RespiratoryPainIntegrator_RespiratoryPainIntegrator",
            human_analog="Parabrachial / Kölliker-Fuse affective-respiratory integration",
            layer="foundational",
        )
        self.state.setdefault("affective_resp_coupling", self.AFFECTIVE_COUPLING_BASELINE)
        self.state.setdefault("sigh_imminent", False)
        self.state.setdefault("breath_holding", False)
        self.state.setdefault("pain_breath_pattern", "normal")
        self.state.setdefault("ceA_to_lpb_drive", 0.0)
        self.state.setdefault("ticks_since_sigh", 0)
        self.state.setdefault("recent_couplings", [])
        self.state.setdefault("tick_count", 0)

    def _classify_pattern(self, breath_rate: float, threat: float, holding: bool, sigh: bool) -> str:
        if holding:
            return "guarded"
        if sigh:
            return "sigh_recovery"
        if breath_rate > 0.45 and threat > 0.5:
            return "rapid_shallow"
        return "normal"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    def _kf_respiratory_pattern_modulation(self, threat: float, breath_rate: float, amplitude: float) -> dict:
        """Kölliker-Fuse modulation of preBötC (Dutschmann & Dick 2012).
        Returns dict of breath-pattern adjustments.
        """
        rate_mod = 0.0
        amp_mod = 0.0
        if threat > 0.5:
            rate_mod = 0.15  # KF accelerates rate under threat
            amp_mod = -0.10  # but reduces depth (rapid shallow)
        return {"rate_modulation": rate_mod, "amplitude_modulation": amp_mod}

    def _affective_pain_dimension(self, ceA_drive: float, expected_pain: float) -> float:
        """Han 2015: LPB → CeA conveys affective-emotional pain dimension.
        This output feeds amygdala-driven pain-affect coupling.
        """
        return min(1.0, ceA_drive * 0.6 + max(0.0, expected_pain) * 0.5)

    def _interoceptive_attention_capture(self, coupling: float, threat: float) -> float:
        """How much current respiratory-affective coupling captures awareness.
        Strong coupling pulls attention to breath/visceral state.
        """
        attention_capture = coupling * (1.0 + threat * 0.5)
        return min(1.0, attention_capture)

    def _respiratory_distress_classification(self, holding: bool, sigh: bool, pattern: str, coupling: float) -> str:
        """Clinical-style respiratory distress classification."""
        if holding and coupling > 0.5:
            return "fear_respiratory_freeze"
        if pattern == "rapid_shallow" and coupling > 0.6:
            return "panic_breathing"
        if sigh:
            return "deactivating_sigh"
        if coupling > 0.4:
            return "anxious_breathing"
        return "normal"

    def _detect_dyspnea_pattern(self, recent_couplings: list, threat: float) -> bool:
        """Sustained high coupling + threat = dyspnea-like distress pattern."""
        if len(recent_couplings) < 15:
            return False
        sample = recent_couplings[-15:]
        avg = sum(sample) / len(sample)
        return avg > 0.55 and threat > 0.4

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        valence = prior.get("ValenceTagger", {})
        threat_signal = bool(valence.get("threat_signal", False))
        valence_intensity = float(valence.get("valence_intensity", 0.0))

        vcr = prior.get("VitalCoreRegulator", {})
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        rp = prior.get("RespiratoryPacemaker", {})
        breath_rate = float(rp.get("breath_rate_hz", 0.25))
        amplitude = float(rp.get("inspiratory_drive_amplitude", 0.5))

        dpg = prior.get("DescendingPainGate", {})
        expected_pain = float(dpg.get("expected_pain_modulation", 0.0))

        stress = prior.get("StressActivationAxis", {})
        stress_active = bool(stress.get("stress_active", False))

        # --- CeA → LPB descending drive (affect → respiratory) ---
        ceA_drive_target = (
            (valence_intensity if threat_signal else 0.0) * 0.5
            + survival_threat * 0.3
            + max(0.0, expected_pain) * 0.2
        )
        prev_ceA = float(self.state.get("ceA_to_lpb_drive", 0.0))
        new_ceA = self._smooth(prev_ceA, ceA_drive_target)

        # --- Affective respiratory coupling ---
        coupling_target = self.AFFECTIVE_COUPLING_BASELINE + new_ceA * 0.7
        if stress_active:
            coupling_target += 0.10
        coupling_target = max(0.0, min(1.0, coupling_target))

        prev_coupling = float(self.state.get("affective_resp_coupling", self.AFFECTIVE_COUPLING_BASELINE))
        new_coupling = self._smooth(prev_coupling, coupling_target)

        # --- Breath holding under high threat ---
        breath_holding = (
            survival_threat > self.BREATH_HOLD_THREAT_THRESHOLD
            and threat_signal
            and amplitude < 0.4
        )

        # --- Sigh detection (physiological sigh every ~5 minutes ≈ 150 ticks) ---
        # Sigh imminence rises with elapsed time + sustained low amplitude
        ticks_since_sigh = int(self.state.get("ticks_since_sigh", 0)) + 1
        sigh_imminent = (
            ticks_since_sigh > self.SIGH_INTERVAL_TICKS
            and amplitude < 0.55
        )
        if sigh_imminent and not self.state.get("sigh_imminent", False):
            # Edge: register the sigh
            ticks_since_sigh = 0

        # --- Classify breath pattern ---
        pattern = self._classify_pattern(breath_rate, survival_threat, breath_holding, sigh_imminent)

        recent = list(self.state.get("recent_couplings", []))
        recent.append(round(new_coupling, 4))
        if len(recent) > 30:
            recent = recent[-30:]

        # --- KF respiratory pattern modulation (Dutschmann 2012) ---
        kf_mods = self._kf_respiratory_pattern_modulation(survival_threat, breath_rate, amplitude)

        # --- Affective pain dimension (Han 2015) ---
        affective_pain = self._affective_pain_dimension(new_ceA, expected_pain)

        # --- Interoceptive attention capture ---
        attention_capture = self._interoceptive_attention_capture(new_coupling, survival_threat)

        # --- Respiratory distress classification ---
        distress_class = self._respiratory_distress_classification(breath_holding, sigh_imminent, pattern, new_coupling)

        # --- Dyspnea-pattern detection ---
        dyspnea = self._detect_dyspnea_pattern(recent, survival_threat)

        self.state["affective_resp_coupling"] = round(new_coupling, 4)
        self.state["sigh_imminent"] = sigh_imminent
        self.state["breath_holding"] = breath_holding
        self.state["pain_breath_pattern"] = pattern
        self.state["ceA_to_lpb_drive"] = round(new_ceA, 4)
        self.state["ticks_since_sigh"] = ticks_since_sigh
        self.state["recent_couplings"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        self.state["kf_rate_modulation"] = round(kf_mods["rate_modulation"], 4)
        self.state["kf_amplitude_modulation"] = round(kf_mods["amplitude_modulation"], 4)
        self.state["affective_pain_dimension"] = round(affective_pain, 4)
        self.state["interoceptive_attention_capture"] = round(attention_capture, 4)
        self.state["respiratory_distress_class"] = distress_class
        self.state["dyspnea_pattern"] = dyspnea

        return {
            "affective_resp_coupling": round(new_coupling, 4),
            "sigh_imminent": sigh_imminent,
            "breath_holding": breath_holding,
            "pain_breath_pattern": pattern,
            "ceA_to_lpb_drive": round(new_ceA, 4),
            "kf_rate_modulation": round(kf_mods["rate_modulation"], 4),
            "kf_amplitude_modulation": round(kf_mods["amplitude_modulation"], 4),
            "affective_pain_dimension": round(affective_pain, 4),
            "interoceptive_attention_capture": round(attention_capture, 4),
            "respiratory_distress_class": distress_class,
            "dyspnea_pattern": dyspnea,
        }

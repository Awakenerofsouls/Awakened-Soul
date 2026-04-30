"""
PreBotzingerInspiration — preBötC Inspiratory Rhythm Generator

NEURAL SUBSTRATE
================
The pre-Bötzinger complex (preBötC) is a small region of the
ventrolateral medulla that generates the inspiratory rhythm of
breathing. Identified by Smith, Feldman and colleagues in the early
1990s through systematic medullary slice transection experiments
(Science 254:726-729, 1991), preBötC is necessary and sufficient for
inspiratory rhythmogenesis: removal abolishes inspiratory motor
output, while isolated preBötC slices continue to generate rhythmic
inspiratory bursts indefinitely.

The core rhythmogenic neurons of preBötC are glutamatergic interneurons
expressing the developmental transcription factor Dbx1. Dbx1-derived
preBötC neurons are rhythmically active synchronous with inspiratory
motor output; ablating them abolishes inspiratory rhythm. Bouvier et al.
(2010) demonstrated that mice lacking Dbx1+ preBötC neurons fail to
breathe and form no recognizable preBötC. Photoinhibition of Dbx1+
preBötC neurons in adult mice slows or stops breathing; photostimulation
speeds breathing (Vann et al. 2018, eNeuro).

A subset of preBötC neurons express somatostatin (SST) and serve as
a modulatory subpopulation; another subset express NK1 receptors and
are selectively vulnerable. Glycinergic interneurons within preBötC
provide phase-switching inhibition critical for rhythm.

preBötC generates the inspiratory rhythm but also receives extensive
modulation from chemosensors (RTN/pFRG for CO2; carotid bodies),
vagal afferents (Hering-Breuer reflex via NTS), arousal (LC, orexin),
emotional state (PAG, amygdala), and parabrachial complex. Output
goes to phrenic premotor neurons in the rVRG.

In Nova's substrate this provides the inspiratory rhythm clock — a
slow oscillator that scales with metabolic demand, arousal, and
emotional state, producing inspiration phase markers usable downstream.

KEY FINDINGS
============
1. preBötC is a brainstem region that generates the inspiratory breathing
   rhythm in mammals — necessary and sufficient — [Smith Ellenberger
    Ballanyi Richter Feldman 1991, Science 254:726-729, "Pre-Bötzinger
    Complex: a Brainstem Region that May Generate Respiratory Rhythm"]
2. Dbx1-derived preBötC interneurons comprise the core inspiratory
   oscillator — laser ablation stops inspiratory rhythm — [Wang Vann
    Picardo Funk Smith Feldman 2014, eLife 3:e03427, "Laser ablation
    of Dbx1 neurons in the pre-Bötzinger complex stops inspiratory
    rhythm"]
3. Dbx1+ preBötC neurons are sufficient for breathing in unanesthetized
   adult mice; photoinhibition slows/stops breathing, photostimulation
   speeds — [Vann Pham Hayes Kottick Del Negro 2018, eNeuro
    5:ENEURO.0130-18.2018]
4. Voltage-dependent rhythmogenic property of preBötC glutamatergic /
   Dbx1-derived / SST+ neurons revealed by graded optogenetic inhibition
   — [Vann et al. 2016, eNeuro 3:ENEURO.0081-16]
5. Pacemaker-like properties of subsets of preBötC neurons identified
   in vitro — voltage-dependent intrinsic bursters contribute to
   rhythmogenesis — [Smith et al. 1999/2007 reviews; reviewed
    Wikipedia/preBötzinger complex]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.vital_drive
- VitalCoreRegulator.parasympathetic_tone
- ArousalRegulator.tonic_level
- ArousalRegulator.phasic_burst_active
- SleepWakeFlipFlop.sleep_wake_state
- CarotidBodyChemosensor.hypoxia_response_active
- CarotidBodyChemosensor.hypercapnia_response
- ValenceTagger.threat_signal
- RespiratoryPainIntegrator.respiratory_drive_modulation

OUTPUTS (to brain_runner enrichment)
=====================================
- inspiratory_rhythm (0.0-1.0): instantaneous inspiratory phase
- respiratory_rate_proxy (0.0-1.0): rate normalized 0=apnea..1=tachypnea
- preBotC_drive (0.0-1.0): overall preBötC excitability
- inspiration_burst_active (bool): in inspiratory phase
- chemoreceptor_modulation (signed -1..+1): scaling from chemosensors
- preBotC_state (str): "eupnea" | "tachypnea" | "bradypnea" | "apneic"

brain_runner enrichment:
    pbc = all_results.get("PreBotzingerInspiration", {})
    if pbc:
        enrichments["brain_inspiratory_rhythm"] = pbc.get("inspiratory_rhythm", 0.0)
        enrichments["brain_respiratory_rate"] = pbc.get("respiratory_rate_proxy", 0.5)
        enrichments["brain_inspiration_active"] = pbc.get("inspiration_burst_active", False)
        enrichments["brain_preBotC_state"] = pbc.get("preBotC_state", "eupnea")
"""

import math

from brain.base_mechanism import BrainMechanism


class PreBotzingerInspiration(BrainMechanism):
    BASELINE_RATE = 0.50
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="PreBotzingerInspiration",
            human_analog="Pre-Bötzinger complex inspiratory rhythm generator",
            layer="foundational",
        )
        self.state.setdefault("inspiratory_rhythm", 0.0)
        self.state.setdefault("respiratory_rate_proxy", self.BASELINE_RATE)
        self.state.setdefault("preBotC_drive", 0.5)
        self.state.setdefault("inspiration_burst_active", False)
        self.state.setdefault("chemoreceptor_modulation", 0.0)
        self.state.setdefault("preBotC_state", "eupnea")
        self.state.setdefault("phase", 0.0)
        self.state.setdefault("recent_rates", [])
        self.state.setdefault("tick_count", 0)

    def _rate_target(self, vital_drive: float, sleep_state: str, hypoxia: bool,
                     hypercapnia: float, threat: bool, resp_mod: float) -> float:
        """Respiratory rate target — scales with metabolic + chemoreceptor
        + emotional drive.
        """
        target = self.BASELINE_RATE
        target += (vital_drive - 0.5) * 0.3
        if sleep_state == "SLEEP":
            target -= 0.15
        elif sleep_state == "TRANSITION":
            target -= 0.05
        if hypoxia:
            target += 0.20
        target += hypercapnia * 0.30
        if threat:
            target += 0.15
        target += resp_mod * 0.2
        return max(0.05, min(1.0, target))

    def _chemoreceptor_modulation(self, hypoxia: bool, hypercapnia: float) -> float:
        """Combined chemoreceptor scaling (-1..+1)."""
        mod = 0.0
        if hypoxia:
            mod += 0.4
        mod += hypercapnia * 0.6
        return max(-1.0, min(1.0, mod))

    def _preBotC_drive_target(self, rate: float, arousal: float, threat: bool) -> float:
        """preBötC excitability scales with rate target and arousal."""
        target = rate * 0.7 + (arousal - 0.5) * 0.2 + 0.20
        if threat:
            target += 0.10
        return max(0.0, min(1.0, target))

    def _advance_phase(self, prev_phase: float, rate: float) -> float:
        """Advance respiratory phase — rate=0.5 baseline ~16 breaths/min."""
        # Phase increment scaled by rate
        delta = 0.05 + rate * 0.10
        return (prev_phase + delta) % 1.0

    def _inspiratory_amplitude(self, phase: float, drive: float) -> float:
        """Inspiratory amplitude — sin pulse during 0-0.4 of cycle."""
        if phase < 0.40:
            return drive * (math.sin(math.pi * (phase / 0.40)))
        return 0.0

    def _classify_state(self, rate: float, drive: float) -> str:
        if drive < 0.10 or rate < 0.10:
            return "apneic"
        if rate > 0.75:
            return "tachypnea"
        if rate < 0.30:
            return "bradypnea"
        return "eupnea"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))
        para = float(vcr.get("parasympathetic_tone", 0.5))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))
        phasic = bool(arousal.get("phasic_burst_active", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        sleep_state = swff.get("sleep_wake_state", "WAKE")

        cb = prior.get("CarotidBodyChemosensor", {})
        hypoxia = bool(cb.get("hypoxia_response_active", False))
        hypercapnia = float(cb.get("hypercapnia_response", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        rpi = prior.get("RespiratoryPainIntegrator", {})
        resp_mod = float(rpi.get("respiratory_drive_modulation", 0.0))

        # --- Rate target ---
        rate_target = self._rate_target(vital_drive, sleep_state, hypoxia,
                                         hypercapnia, threat, resp_mod)
        if phasic:
            rate_target = min(1.0, rate_target + 0.08)
        prev_rate = float(self.state.get("respiratory_rate_proxy", self.BASELINE_RATE))
        new_rate = self._smooth(prev_rate, rate_target)

        # --- Chemoreceptor modulation ---
        chemo_mod = self._chemoreceptor_modulation(hypoxia, hypercapnia)

        # --- preBötC drive ---
        drive_target = self._preBotC_drive_target(new_rate, tonic, threat)
        prev_drive = float(self.state.get("preBotC_drive", 0.5))
        new_drive = self._smooth(prev_drive, drive_target)

        # --- Phase advance ---
        prev_phase = float(self.state.get("phase", 0.0))
        new_phase = self._advance_phase(prev_phase, new_rate)

        # --- Inspiratory amplitude (current cycle) ---
        rhythm = self._inspiratory_amplitude(new_phase, new_drive)
        burst_active = rhythm > 0.20

        # --- State ---
        state = self._classify_state(new_rate, new_drive)

        recent = list(self.state.get("recent_rates", []))
        recent.append(round(new_rate, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["inspiratory_rhythm"] = round(rhythm, 4)
        self.state["respiratory_rate_proxy"] = round(new_rate, 4)
        self.state["preBotC_drive"] = round(new_drive, 4)
        self.state["inspiration_burst_active"] = burst_active
        self.state["chemoreceptor_modulation"] = round(chemo_mod, 4)
        self.state["preBotC_state"] = state
        self.state["phase"] = round(new_phase, 4)
        self.state["recent_rates"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "inspiratory_rhythm": round(rhythm, 4),
            "respiratory_rate_proxy": round(new_rate, 4),
            "preBotC_drive": round(new_drive, 4),
            "inspiration_burst_active": burst_active,
            "chemoreceptor_modulation": round(chemo_mod, 4),
            "preBotC_state": state,
        }

"""
VestibularNucleiBalance — Vestibular Nuclei Balance / VOR / Motion Sickness

NEURAL SUBSTRATE
================
The vestibular nuclear complex sits in the dorsolateral medulla and
caudal pons and consists of four major nuclei: superior, lateral
(Deiters'), medial, and inferior (descending). It receives primary
afferents from the semicircular canals (rotational head movements)
and otolith organs (linear acceleration and gravity) via the eighth
cranial nerve, plus extensive convergent inputs from the cerebellum,
spinal proprioception, and visual system.

Vestibular nuclei generate four principal motor outputs: (1) vestibulo-
ocular reflex (VOR) for gaze stabilization during head motion via
projections to oculomotor nuclei; (2) vestibulospinal reflexes for
postural control via lateral and medial vestibulospinal tracts; (3)
vestibulocerebellar projections for sensory integration; (4) vestibulo-
autonomic projections that drive nausea, pallor, and cardiovascular
responses during vestibular stimulation.

The vestibulo-autonomic outputs are anatomically dense — vestibular
nuclei project to the parabrachial nuclear complex (Kölliker-Fuse,
medial PBN, lateral PBN), nucleus tractus solitarius (NTS), nucleus
ambiguus, and dorsal motor nucleus of vagus. This vestibulo-autonomic
network is the substrate of motion sickness symptoms (Yates Miller 1996).
A discordance between expected and actual vestibular input (e.g., reading
in a moving car) drives the motion sickness response, recently mapped
to vestibular CCK signaling (Lu et al. 2023, PNAS).

The velocity storage integrator in the vestibular nuclei integrates
canal afferent signals over seconds to extend the perceptual response
to head rotation. A short velocity-storage time constant reduces motion
sickness susceptibility.

In {{AGENT_NAME}}'s substrate this provides the balance / postural / motion-sickness
hub — converts head/body motion proxies into VOR drive, postural drive,
and aversive autonomic recruitment when vestibular signals are anomalous.

KEY FINDINGS
============
1. Vestibular nuclei project densely to parabrachial nuclear complex
   (Kölliker-Fuse, mPBN, lPBN) — substrate for vestibulo-autonomic
   interaction underlying motion sickness — [Balaban Beryozkin 1994,
    Exp Brain Res 100:241-262, "Vestibular nucleus projections to the
    parabrachial nucleus in rabbits" PubMed 8801117]
2. Vestibular nuclei project to NTS and DMV — substrates for vestibulo-
   autonomic interactions — [Balaban 1996, Exp Brain Res 110:155-169,
    "Vestibular nucleus projections to nucleus tractus solitarius and
    dorsal motor nucleus of vagus"]
3. Neural basis of motion sickness involves vestibular input through
   semicircular canals, otoliths, and velocity storage integrator —
   [reviewed Yates Miller; Cohen Yakushin Holstein 2018, J Neurophysiol
    121:973-982, "The neural basis of motion sickness"]
4. Vestibular CCK signaling drives motion sickness-like behavior —
   peripheral CCK from vestibular afferents engages central pathway —
   [Lu et al. 2023, PNAS 120:e2304933120, "Vestibular CCK signaling
   drives motion sickness-like behavior in mice"]
5. Vestibular nuclei integrate emetic GI and vestibular signals to
   produce nausea/vomiting; clinical motion sickness convergence —
   [Yates Catanzaro Miller McCall Mason 2014, J Vestibular Res
    24:281-291, PubMed 24736862]

INPUTS (from prior_results)
============================
- HeadMotionProxy.angular_velocity (optional; default 0)
- HeadMotionProxy.linear_acceleration (optional; default 0)
- AreaPostremaToxinGuard.nausea_intensity
- ParabrachialTasteVisceral.lpbn_visceral_relay
- ArousalRegulator.tonic_level
- VitalCoreRegulator.parasympathetic_tone
- ValenceTagger.threat_signal

OUTPUTS (to brain_runner enrichment)
=====================================
- vestibular_drive (0.0-1.0): overall vestibular nucleus output
- vor_drive (0.0-1.0): vestibulo-ocular reflex command
- postural_drive (0.0-1.0): vestibulospinal postural command
- vestibulo_autonomic_drive (0.0-1.0): aversive autonomic recruitment
- velocity_storage (0.0-1.0): integrator state
- motion_sickness_active (bool)
- vestibular_state (str): "quiet" | "balance_engaged" | "motion_sickness" | "vor_active"

brain_runner enrichment:
    vn = all_results.get("VestibularNucleiBalance", {})
    if vn:
        enrichments["brain_vestibular_drive"] = vn.get("vestibular_drive", 0.2)
        enrichments["brain_vor_drive"] = vn.get("vor_drive", 0.0)
        enrichments["brain_postural_drive"] = vn.get("postural_drive", 0.3)
        enrichments["brain_motion_sickness"] = vn.get("motion_sickness_active", False)
"""

from brain.base_mechanism import BrainMechanism


class VestibularNucleiBalance(BrainMechanism):
    BASELINE_DRIVE = 0.20
    SICKNESS_THRESHOLD = 0.55
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="VestibularNucleiBalance",
            human_analog="Vestibular nuclei balance / VOR / motion sickness",
            layer="foundational",
        )
        self.state.setdefault("vestibular_drive", self.BASELINE_DRIVE)
        self.state.setdefault("vor_drive", 0.0)
        self.state.setdefault("postural_drive", 0.30)
        self.state.setdefault("vestibulo_autonomic_drive", 0.0)
        self.state.setdefault("velocity_storage", 0.0)
        self.state.setdefault("motion_sickness_active", False)
        self.state.setdefault("vestibular_state", "quiet")
        self.state.setdefault("recent_storage", [])
        self.state.setdefault("tick_count", 0)

    def _vestibular_drive_target(self, angular: float, linear: float, arousal: float) -> float:
        """Vestibular nucleus drive — scales with head/body motion proxy."""
        target = self.BASELINE_DRIVE + abs(angular) * 0.4 + abs(linear) * 0.4
        target += max(0.0, arousal - 0.5) * 0.1
        return max(0.0, min(1.0, target))

    def _velocity_storage_update(self, prev_storage: float, angular: float) -> float:
        """Velocity storage integrator — leaky integrator with τ ~5 ticks."""
        decay = 0.15
        gain = 0.50
        return max(0.0, min(1.0, prev_storage * (1.0 - decay) + abs(angular) * gain))

    def _vor_drive_target(self, angular: float, vest: float) -> float:
        """VOR — proportional to head angular velocity, gated by vestibular drive."""
        return min(1.0, abs(angular) * 0.9 + vest * 0.1)

    def _postural_drive_target(self, linear: float, vest: float) -> float:
        """Postural drive — vestibulospinal output for balance maintenance."""
        return min(1.0, 0.30 + abs(linear) * 0.5 + vest * 0.2)

    def _vestibulo_autonomic_target(self, storage: float, nausea: float,
                                      pbn_visceral: float, conflict_proxy: float) -> float:
        """Vestibulo-autonomic recruitment — drives motion sickness symptoms.
        Engaged by sustained velocity storage AND pre-existing nausea or
        sensory conflict.
        """
        target = storage * 0.5 + nausea * 0.4 + pbn_visceral * 0.3
        target += conflict_proxy * 0.3
        return max(0.0, min(1.0, target))

    def _spatial_confidence(self, vest: float, storage: float) -> float:
        """Spatial orientation confidence from vestibular + velocity-storage."""
        recent = list(self.state.get("recent_storage", []))
        variance = 0.0
        if len(recent) > 4:
            m = sum(recent) / len(recent)
            variance = sum((s - m)**2 for s in recent) / len(recent)
        prev = float(self.state.get("orientation_confidence", 0.7))
        penalty = min(0.4, variance * 2.0)
        bonus = 0.1 if vest > 0.3 and abs(storage) < 0.2 else 0.0
        return 0.85 * prev + 0.15 * max(0.0, 0.7 + bonus - penalty)

    def _classify_state(self, vest: float, vor: float, sickness: bool) -> str:
        if sickness:
            return "motion_sickness"
        if vor > 0.40:
            return "vor_active"
        if vest > 0.40:
            return "balance_engaged"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        head_motion = prior.get("HeadMotionProxy", {})
        angular = float(head_motion.get("angular_velocity", 0.0))
        linear = float(head_motion.get("linear_acceleration", 0.0))

        ap = prior.get("AreaPostremaToxinGuard", {})
        nausea = float(ap.get("nausea_intensity", 0.0))

        pbn_data = prior.get("ParabrachialTasteVisceral", {})
        pbn_visc = float(pbn_data.get("lpbn_visceral_relay", 0.20))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        vcr = prior.get("VitalCoreRegulator", {})
        para = float(vcr.get("parasympathetic_tone", 0.5))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        # --- Vestibular drive ---
        vest_target = self._vestibular_drive_target(angular, linear, tonic)
        prev_vest = float(self.state.get("vestibular_drive", self.BASELINE_DRIVE))
        new_vest = self._smooth(prev_vest, vest_target)

        # --- Velocity storage integrator ---
        prev_storage = float(self.state.get("velocity_storage", 0.0))
        new_storage = self._velocity_storage_update(prev_storage, angular)

        # --- VOR ---
        vor = self._vor_drive_target(angular, new_vest)

        # --- Postural drive ---
        post_target = self._postural_drive_target(linear, new_vest)
        prev_post = float(self.state.get("postural_drive", 0.30))
        new_post = self._smooth(prev_post, post_target)

        # --- Vestibulo-autonomic (motion sickness pathway) ---
        # Sensory conflict proxy: high storage but low actual angular = mismatch
        conflict_proxy = max(0.0, new_storage - abs(angular)) * 0.6
        autonomic_target = self._vestibulo_autonomic_target(new_storage, nausea,
                                                              pbn_visc, conflict_proxy)
        prev_auto = float(self.state.get("vestibulo_autonomic_drive", 0.0))
        new_auto = self._smooth(prev_auto, autonomic_target)

        # --- Motion sickness ---
        sickness = new_auto > self.SICKNESS_THRESHOLD

        # --- State ---
        state = self._classify_state(new_vest, vor, sickness)

        recent = list(self.state.get("recent_storage", []))
        recent.append(round(new_storage, 4))
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vestibular_drive"] = round(new_vest, 4)
        self.state["vor_drive"] = round(vor, 4)
        self.state["postural_drive"] = round(new_post, 4)
        self.state["vestibulo_autonomic_drive"] = round(new_auto, 4)
        self.state["velocity_storage"] = round(new_storage, 4)
        self.state["motion_sickness_active"] = sickness
        self.state["vestibular_state"] = state
        self.state["recent_storage"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vestibular_drive": round(new_vest, 4),
            "vor_drive": round(vor, 4),
            "postural_drive": round(new_post, 4),
            "vestibulo_autonomic_drive": round(new_auto, 4),
            "velocity_storage": round(new_storage, 4),
            "motion_sickness_active": sickness,
            "vestibular_state": state,
            "nausea_proxy": sickness,
        }

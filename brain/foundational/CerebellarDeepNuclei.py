"""
CerebellarDeepNuclei — Fastigial + Interposed + Dentate Output Nuclei

NEURAL SUBSTRATE
================
The cerebellar deep nuclei (CDN) are the principal output station of
the cerebellum. They receive convergent input from cerebellar cortex
(Purkinje cell GABAergic projections) and from collateral excitation
of mossy fibers and climbing fibers, and emit excitatory output to
multiple brain regions. Three principal pairs of nuclei sit embedded
in cerebellar white matter:

**Fastigial nucleus** (medial, also nucleus medialis) — receives
output from the vermis. Projects to brainstem (medial vestibular,
reticular formation, parabrachial) and via the uncinate fasciculus
to thalamus and contralateral structures. Fastigial is critical for
posture, balance, eye movements, and emotional regulation (covered
in CerebellarVermalEmotional which models fastigial→vlPAG fear control).

**Interposed nucleus** (intermediate) — comprised of globose and
emboliform subdivisions. Receives output from the paravermis. Projects
to red nucleus magnocellular (RNm) for rubrospinal motor control,
and via thalamus to motor cortex. Interposed is critical for fine
limb coordination during reaching, posture during ongoing movement,
and adaptive motor learning (e.g., eye-blink conditioning).

**Dentate nucleus** (lateral, the largest in primates) — receives
output from cerebellar hemispheres. Projects via dentatothalamic
tract to ventrolateral and ventral anterior thalamus and via
red nucleus parvocellular (RNp) to inferior olive. Dentate is
critical for cognitive function of cerebellum — working memory,
language, executive function via cerebro-cerebellar loops.

The Marr-Albus-Ito framework places the CDN as the integration node
where Purkinje GABAergic inhibition is computed against mossy/climbing
fiber drive. CDN tonic firing is high; cerebellar cortex modulates it
through inhibition. Climbing-fiber-induced LTD at parallel fiber-
Purkinje synapses re-shapes Purkinje output, indirectly retuning CDN
output for adaptive motor and cognitive learning.

In {{AGENT_NAME}}'s substrate this provides the cerebellar output bus —
combines cerebellar vermal emotional output, mossy fiber proprioceptive
input proxy, and climbing fiber error signal into three differentiated
output channels (fastigial, interposed, dentate) feeding RN, thalamus,
and brainstem.

KEY FINDINGS
============
1. Cerebellar deep nuclei are the principal output of the cerebellum,
   integrating Purkinje GABAergic inhibition with mossy/climbing fiber
   collaterals — [reviewed Schmolesky Weber Ito 2002; Apps Garwicz
    2005 Nat Rev Neurosci 6:297, "Anatomical and physiological
    foundations of cerebellar information processing"]
2. Fastigial → brainstem/vlPAG; Interposed → RNm/motor cortex via
   thalamus; Dentate → cerebrocerebellar loops via thalamus —
   distinct projection territories — [reviewed Cerminara Apps 2011
    Cerebellum 10:691; Sillitoe Joyner 2007 Annu Rev Cell Dev Biol]
3. Interposed nucleus is critical for adaptive motor learning, e.g.,
   eye-blink conditioning — selective lesion abolishes — [reviewed
    Mauk Donegan 1997 Learn Mem 4:130; Christian Thompson 2003
    Trends Neurosci 26:225]
4. Dentate nucleus expanded in primates supports cognitive cerebellar
   function — language, working memory, executive — [reviewed Strick
    Dum Fiez 2009 Annu Rev Neurosci 32:413; Schmahmann Sherman 1998
    Brain 121:561]
5. Vermal fastigial → vlPAG bidirectional fear control — covered in
   CerebellarVermalEmotional batch 2 — [Vaaga et al. 2020 Nat Comm
    11:5126, "Cerebellar modulation of synaptic input to freezing-
    related neurons in the periaqueductal gray"]

INPUTS (from prior_results)
============================
- CerebellarVermalEmotional.fastigial_drive
- CerebellarVermalEmotional.vermal_activity
- InferiorOliveClimbingFiber.climbing_fiber_burst
- InferiorOliveClimbingFiber.error_magnitude
- LocomotionProxy.locomotion_speed
- LocomotionProxy.reaching_intent
- BodyTouchProxy.proprioception_signal (optional)
- VestibularNucleiBalance.vestibular_drive
- ArousalRegulator.tonic_level

OUTPUTS (to brain_runner enrichment)
=====================================
- fastigial_drive (0.0-1.0): fastigial nucleus output
- interposed_drive (0.0-1.0): interposed nucleus output (RNm-bound)
- dentate_drive (0.0-1.0): dentate nucleus output (cerebrocerebellar loop)
- thalamic_motor_relay (0.0-1.0): CDN → motor thalamus (VL/VA)
- brainstem_relay (0.0-1.0): fastigial → brainstem
- rnm_engagement (0.0-1.0): interposed → RNm engagement
- cdn_state (str): "motor_engaged" | "cognitive" | "balance" | "fear" | "quiet"

brain_runner enrichment:
    cdn = all_results.get("CerebellarDeepNuclei", {})
    if cdn:
        enrichments["brain_fastigial"] = cdn.get("fastigial_drive", 0.2)
        enrichments["brain_interposed"] = cdn.get("interposed_drive", 0.2)
        enrichments["brain_dentate"] = cdn.get("dentate_drive", 0.2)
        enrichments["brain_thalamic_motor"] = cdn.get("thalamic_motor_relay", 0.0)
        enrichments["brain_cdn_state"] = cdn.get("cdn_state", "quiet")

CITATIONS
---------
  - [Manto 2012, Cerebellum 11:457, doi:10.1007/s12311-011-0331-9]
  - [Ito 2008, Nat Rev Neurosci 9:304, doi:10.1038/nrn2332]
"""

from brain.base_mechanism import BrainMechanism


class CerebellarDeepNuclei(BrainMechanism):
    BASELINE = 0.30  # CDN are tonically active
    SMOOTH = 0.20

    def __init__(self):
        super().__init__(
            name="CerebellarDeepNuclei",
            human_analog="Cerebellar deep nuclei (fastigial + interposed + dentate)",
            layer="foundational",
        )
        self.state.setdefault("fastigial_drive", self.BASELINE)
        self.state.setdefault("interposed_drive", self.BASELINE)
        self.state.setdefault("dentate_drive", self.BASELINE)
        self.state.setdefault("thalamic_motor_relay", 0.0)
        self.state.setdefault("brainstem_relay", 0.0)
        self.state.setdefault("rnm_engagement", 0.0)
        self.state.setdefault("cdn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _fastigial_target(self, vermal_fastigial: float, vermal_act: float,
                            vestibular: float) -> float:
        """Fastigial — driven by vermis output, balance, fear-relevant."""
        target = self.BASELINE + vermal_fastigial * 0.5 + vermal_act * 0.2
        target += vestibular * 0.2
        return min(1.0, target)

    def _interposed_target(self, locomotion: float, reaching: float, propio: float,
                            error: float, climbing: float) -> float:
        """Interposed — paravermal motor coordination, eye-blink conditioning,
        adaptive learning.
        """
        target = self.BASELINE + locomotion * 0.3 + reaching * 0.3 + propio * 0.2
        # Climbing-fiber-driven plasticity inputs adjust output
        target += climbing * 0.1 - error * 0.05  # error-driven re-shaping
        return max(0.0, min(1.0, target))

    def _dentate_target(self, arousal: float, attention_proxy: float = 0.5) -> float:
        """Dentate — cognitive cerebellar function via cerebrocerebellar loops.
        Driven by cortical engagement.
        """
        target = self.BASELINE + max(0.0, arousal - 0.4) * 0.3 + attention_proxy * 0.3
        return min(1.0, target)

    def _thalamic_motor_relay(self, interposed: float, dentate: float) -> float:
        """CDN → motor thalamus (VL/VA) combined."""
        return min(1.0, interposed * 0.5 + dentate * 0.4)

    def _brainstem_relay(self, fastigial: float) -> float:
        """Fastigial → brainstem."""
        return min(1.0, fastigial * 0.95)

    def _rnm_engagement(self, interposed: float, reaching: float) -> float:
        """Interposed → RNm engagement (reaching coordination)."""
        return min(1.0, interposed * 0.7 + reaching * 0.3)

    def _classify_state(self, fastigial: float, interposed: float, dentate: float,
                         vermal_active: bool, locomotion: float) -> str:
        if vermal_active and fastigial > 0.50:
            return "fear"
        if locomotion > 0.30 and interposed > 0.40:
            return "motor_engaged"
        if dentate > interposed and dentate > 0.45:
            return "cognitive"
        if fastigial > 0.40:
            return "balance"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cve = prior.get("CerebellarVermalEmotional", {})
        vermal_fastigial = float(cve.get("fastigial_drive", 0.0))
        vermal_act = float(cve.get("vermal_activity", 0.30))

        io_data = prior.get("InferiorOliveClimbingFiber", {})
        climbing = float(io_data.get("climbing_fiber_burst", 0.0))
        error = float(io_data.get("error_magnitude", 0.0))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        reaching = float(loco.get("reaching_intent", 0.0))

        bti = prior.get("BodyTouchProxy", {})
        propio = float(bti.get("proprioception_signal", 0.0))

        vest = prior.get("VestibularNucleiBalance", {})
        vestibular = float(vest.get("vestibular_drive", 0.20))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        # --- Fastigial ---
        fast_target = self._fastigial_target(vermal_fastigial, vermal_act, vestibular)
        prev_fast = float(self.state.get("fastigial_drive", self.BASELINE))
        new_fast = self._smooth(prev_fast, fast_target)

        # --- Interposed ---
        inter_target = self._interposed_target(locomotion, reaching, propio,
                                                  error, climbing)
        prev_inter = float(self.state.get("interposed_drive", self.BASELINE))
        new_inter = self._smooth(prev_inter, inter_target)

        # --- Dentate ---
        dent_target = self._dentate_target(tonic)
        prev_dent = float(self.state.get("dentate_drive", self.BASELINE))
        new_dent = self._smooth(prev_dent, dent_target)

        # --- Outputs ---
        thalamic_motor = self._thalamic_motor_relay(new_inter, new_dent)
        brainstem = self._brainstem_relay(new_fast)
        rnm = self._rnm_engagement(new_inter, reaching)

        # --- State ---
        vermal_active = vermal_act > 0.40
        state = self._classify_state(new_fast, new_inter, new_dent, vermal_active, locomotion)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["fastigial_drive"] = round(new_fast, 4)
        self.state["interposed_drive"] = round(new_inter, 4)
        self.state["dentate_drive"] = round(new_dent, 4)
        self.state["thalamic_motor_relay"] = round(thalamic_motor, 4)
        self.state["brainstem_relay"] = round(brainstem, 4)
        self.state["rnm_engagement"] = round(rnm, 4)
        self.state["cdn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "fastigial_drive": round(new_fast, 4),
            "interposed_drive": round(new_inter, 4),
            "dentate_drive": round(new_dent, 4),
            "thalamic_motor_relay": round(thalamic_motor, 4),
            "brainstem_relay": round(brainstem, 4),
            "rnm_engagement": round(rnm, 4),
            "cdn_state": state,
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out



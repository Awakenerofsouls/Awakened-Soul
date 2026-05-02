"""
TrigeminalSensoryComplex — V Principal + Spinal V Orofacial Sensation

NEURAL SUBSTRATE
================
The trigeminal sensory complex is the principal central station for
somatosensation from the face, oral cavity, dura, cornea, and teeth —
essentially the "face S1" of the brainstem. Trigeminal afferents
enter the brain via the trigeminal nerve (CN V) and synapse in three
nuclear divisions: principal sensory nucleus (Vp, in pons) and the
three subdivisions of the spinal trigeminal nucleus (Vsp) extending
caudally through the medulla into upper cervical cord — Vsp oralis,
Vsp interpolaris, and Vsp caudalis.

Vp processes fine touch and proprioception from the face — analogous
to the dorsal column nuclei for the body. It projects via the trigeminal
lemniscus to ventral posteromedial thalamus (VPM), and onward to face
S1 cortex. **Vsp caudalis (also called the medullary dorsal horn)**
processes orofacial pain, temperature, and crude touch — analogous to
the spinal dorsal horn (covered separately as SpinalDorsalHornGate).
Vsp caudalis is the principal source of pain from face/cornea/teeth/
dura and is critical for headache and migraine pathophysiology.

The mesencephalic trigeminal nucleus (Vme), uniquely, contains the
cell bodies of muscle-spindle afferents from the masseter and other
masticatory muscles — the only primary sensory neurons whose somas
are inside the CNS.

Migraine pain originates in dural-nociceptive afferents that converge
in Vsp caudalis where they sensitize centrally — central sensitization
of Vsp underlies allodynia (pain from non-noxious touch) during
migraine attacks. CGRP released from trigeminal afferents and
secondary CGRP signaling in Vsp is the molecular target of
contemporary migraine therapeutics (gepants, mAb anti-CGRP).

Vsp also receives convergent input from cervical afferents (C1-C3) —
this trigeminocervical convergence underlies the referred pain pattern
in cervicogenic headache. Descending pain modulation from PAG-RVM-NRM
(covered separately) and from A5 (also covered) targets Vsp caudalis
similarly to spinal dorsal horn.

In the agent's substrate this provides the orofacial somatosensory entry
and the headache/migraine pain channel — converts orofacial input
proxies (touch, pain, temperature) into ascending thalamic relay
plus a head/face pain output.

KEY FINDINGS
============
1. Trigeminal sensory complex contains Vp (principal sensory, fine
   touch) and Vsp (spinal trigeminal, pain/temp) — face analogue of
   dorsal column / spinal dorsal horn — [reviewed Sessle 2000, Crit
    Rev Oral Biol Med 11:57; Bereiter et al. 2000]
2. Vsp caudalis is the principal source of orofacial pain and dural
   afferent processing — substrate of headache and migraine —
   [reviewed Goadsby et al. 2017, Physiol Rev 97:553, "Pathophysiology
    of migraine"; Burstein et al. 2015 J Headache Pain]
3. CGRP is released from trigeminal afferents and modulates Vsp
   nociception — molecular target of migraine therapeutics — [reviewed
    Russo 2015, Annu Rev Pharmacol Toxicol 55:533, "Calcitonin gene-
    related peptide (CGRP): a new target for migraine"]
4. Trigeminocervical convergence in Vsp caudalis underlies cervicogenic
   headache — C1-C3 afferents converge with V1 dural — [Bartsch
    Goadsby 2003 Brain 126:1801; reviewed Bogduk Govind 2009 Lancet
    Neurol]
5. Mesencephalic trigeminal nucleus (Vme) contains primary sensory
   neuron somata inside CNS — unique exception to peripheral ganglion
   rule — [Linden 1978; reviewed Hassanpour Liu 2024]

INPUTS (from prior_results)
============================
- OrofacialInputProxy.touch_intensity (optional; default 0)
- OrofacialInputProxy.pain_intensity (optional; default 0)
- OrofacialInputProxy.dural_signal (optional; default 0)
- OrofacialInputProxy.temperature_deviation (optional; default 0)
- DescendingPainGate.inhibitory_drive
- DescendingPainGate.facilitatory_drive
- DescendingPainGate.opioid_tone
- MedullaryRapheMagnus.spinal_5ht_release
- A5NoradrenergicGroup.spinal_ne_visceral
- StressActivationAxis.cortisol_level

OUTPUTS (to brain_runner enrichment)
=====================================
- vp_drive (0.0-1.0): principal sensory nucleus output (fine touch)
- vsp_caudalis_drive (0.0-1.0): pain output (medullary dorsal horn)
- vme_proprioceptive (0.0-1.0): masticatory proprioception
- vpm_thalamic_relay (0.0-1.0): ascending to VPM thalamus
- migraine_substrate_active (bool): Vsp caudalis sensitization marker
- cgrp_signaling (0.0-1.0): peripheral/central CGRP proxy
- cervicogenic_convergence (0.0-1.0): C1-C3 + V1 dural convergence
- trigeminal_state (str): "quiet" | "touch" | "pain" | "migraine_sensitized" | "proprioceptive"

brain_runner enrichment:
    tsc = all_results.get("TrigeminalSensoryComplex", {})
    if tsc:
        enrichments["brain_vsp_pain"] = tsc.get("vsp_caudalis_drive", 0.0)
        enrichments["brain_vp_touch"] = tsc.get("vp_drive", 0.1)
        enrichments["brain_vpm_relay"] = tsc.get("vpm_thalamic_relay", 0.0)
        enrichments["brain_migraine_substrate"] = tsc.get("migraine_substrate_active", False)
        enrichments["brain_trigeminal_state"] = tsc.get("trigeminal_state", "quiet")

CITATIONS
---------
  - [Sessle 2000, Crit Rev Oral Biol Med 11:57]
"""

from brain.base_mechanism import BrainMechanism


class TrigeminalSensoryComplex(BrainMechanism):
    BASELINE = 0.10
    SENSITIZATION_THRESHOLD = 60
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="TrigeminalSensoryComplex",
            human_analog="Trigeminal sensory complex (Vp/Vsp/Vme orofacial)",
            layer="foundational",
        )
        self.state.setdefault("vp_drive", self.BASELINE)
        self.state.setdefault("vsp_caudalis_drive", 0.0)
        self.state.setdefault("vme_proprioceptive", 0.0)
        self.state.setdefault("vpm_thalamic_relay", 0.0)
        self.state.setdefault("migraine_substrate_active", False)
        self.state.setdefault("cgrp_signaling", 0.0)
        self.state.setdefault("cervicogenic_convergence", 0.0)
        self.state.setdefault("trigeminal_state", "quiet")
        self.state.setdefault("dural_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _vp_target(self, touch: float, descending_inh: float) -> float:
        """Vp principal sensory — fine touch from face."""
        target = self.BASELINE + touch * 0.7
        target -= descending_inh * 0.1  # mild gain control
        return max(0.0, min(1.0, target))

    def _vsp_caudalis_target(self, pain: float, dural: float, temp_dev: float,
                              descending_fac: float, opioid: float, cortisol: float) -> float:
        """Vsp caudalis — orofacial pain / temp / dural — substrate of headache."""
        target = pain * 0.5 + dural * 0.4 + abs(temp_dev) * 0.2
        target += descending_fac * 0.2
        target -= opioid * 0.5  # opioid analgesia
        if cortisol > 0.65:
            target += (cortisol - 0.5) * 0.2  # stress sensitization
        return max(0.0, min(1.0, target))

    def _vme_proprioceptive(self, jaw_proprioception_proxy: float = 0.0) -> float:
        """Vme masticatory proprioception — without explicit input, baseline low."""
        return min(1.0, self.BASELINE + jaw_proprioception_proxy * 0.5)

    def _vpm_relay(self, vp: float, vsp: float, vme: float) -> float:
        """Trigeminal lemniscus → VPM thalamus."""
        return min(1.0, vp * 0.5 + vsp * 0.3 + vme * 0.2)

    def _cgrp_signaling(self, vsp: float, dural: float) -> float:
        """CGRP signaling proxy (Russo 2015) — released by trigeminal afferents,
        especially during dural activation.
        """
        return min(1.0, vsp * 0.5 + dural * 0.5)

    def _cervicogenic_convergence(self, dural: float, neck_signal: float = 0.0) -> float:
        """C1-C3 + V1 dural convergence (Bartsch Goadsby 2003)."""
        if dural < 0.20 and neck_signal < 0.10:
            return 0.0
        return min(1.0, dural * 0.5 + neck_signal * 0.5)

    def _detect_migraine_sensitization(self, streak: int) -> bool:
        return streak > self.SENSITIZATION_THRESHOLD

    def _classify_state(self, vp: float, vsp: float, vme: float, sensitized: bool) -> str:
        if sensitized:
            return "migraine_sensitized"
        if vsp > 0.40:
            return "pain"
        if vme > 0.40:
            return "proprioceptive"
        if vp > 0.30:
            return "touch"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        ofi = prior.get("OrofacialInputProxy", {})
        touch = float(ofi.get("touch_intensity", 0.0))
        pain = float(ofi.get("pain_intensity", 0.0))
        dural = float(ofi.get("dural_signal", 0.0))
        temp_dev = float(ofi.get("temperature_deviation", 0.0))

        dpg = prior.get("DescendingPainGate", {})
        descending_inh = float(dpg.get("inhibitory_drive", 0.30))
        descending_fac = float(dpg.get("facilitatory_drive", 0.30))
        opioid = float(dpg.get("opioid_tone", 0.0))

        nrm = prior.get("MedullaryRapheMagnus", {})
        spinal_5ht = float(nrm.get("spinal_5ht_release", 0.40))

        a5_data = prior.get("A5NoradrenergicGroup", {})
        ne = float(a5_data.get("spinal_ne_visceral", 0.20))

        stress = prior.get("StressActivationAxis", {})
        cortisol = float(stress.get("cortisol_level", 0.0))

        # Use NE as additional inhibitory tone
        descending_inh_total = min(1.0, descending_inh + ne * 0.3 +
                                       max(0.0, spinal_5ht - 0.4) * 0.2)

        # --- Vp ---
        vp_target = self._vp_target(touch, descending_inh_total)
        prev_vp = float(self.state.get("vp_drive", self.BASELINE))
        new_vp = self._smooth(prev_vp, vp_target)

        # --- Vsp caudalis ---
        vsp_target = self._vsp_caudalis_target(pain, dural, temp_dev,
                                                  descending_fac, opioid, cortisol)
        prev_vsp = float(self.state.get("vsp_caudalis_drive", 0.0))
        new_vsp = self._smooth(prev_vsp, vsp_target)

        # --- Vme ---
        vme = self._vme_proprioceptive(0.0)  # no explicit jaw input proxy
        prev_vme = float(self.state.get("vme_proprioceptive", 0.0))
        new_vme = self._smooth(prev_vme, vme)

        # --- VPM relay ---
        vpm = self._vpm_relay(new_vp, new_vsp, new_vme)

        # --- CGRP ---
        cgrp = self._cgrp_signaling(new_vsp, dural)
        prev_cgrp = float(self.state.get("cgrp_signaling", 0.0))
        new_cgrp = self._smooth(prev_cgrp, cgrp)

        # --- Cervicogenic ---
        cerv = self._cervicogenic_convergence(dural, 0.0)

        # --- Migraine sensitization streak ---
        prev_streak = int(self.state.get("dural_streak", 0))
        if dural > 0.40 or new_vsp > 0.55:
            streak = prev_streak + 1
        else:
            streak = max(0, prev_streak - 2)
        sensitized = self._detect_migraine_sensitization(streak)

        # --- State ---
        state = self._classify_state(new_vp, new_vsp, new_vme, sensitized)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["vp_drive"] = round(new_vp, 4)
        self.state["vsp_caudalis_drive"] = round(new_vsp, 4)
        self.state["vme_proprioceptive"] = round(new_vme, 4)
        self.state["vpm_thalamic_relay"] = round(vpm, 4)
        self.state["migraine_substrate_active"] = sensitized
        self.state["cgrp_signaling"] = round(new_cgrp, 4)
        self.state["cervicogenic_convergence"] = round(cerv, 4)
        self.state["trigeminal_state"] = state
        self.state["dural_streak"] = streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "vp_drive": round(new_vp, 4),
            "vsp_caudalis_drive": round(new_vsp, 4),
            "vme_proprioceptive": round(new_vme, 4),
            "vpm_thalamic_relay": round(vpm, 4),
            "migraine_substrate_active": sensitized,
            "cgrp_signaling": round(new_cgrp, 4),
            "cervicogenic_convergence": round(cerv, 4),
            "trigeminal_state": state,
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



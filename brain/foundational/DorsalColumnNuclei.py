"""
DorsalColumnNuclei — Gracile + Cuneate (Fine Touch / Proprioception Ascending)

NEURAL SUBSTRATE
================
The dorsal column nuclei (DCN) — gracile nucleus (medial, processing
input from the lower body) and cuneate nucleus (lateral, processing
input from the upper body) — are the principal central station for
fine touch, vibration, and conscious proprioception ascending from
the body. They sit in the caudal medulla and receive primary afferent
fibers traveling in the dorsal columns of the spinal cord (gracile
fasciculus from below T6, cuneate fasciculus from above T6).

DCN second-order neurons project across the midline as the **internal
arcuate fibers**, forming the **medial lemniscus** that ascends through
the brainstem to terminate in the ventral posterolateral nucleus (VPL)
of the thalamus. From VPL, third-order neurons project to primary
somatosensory cortex (S1). This **dorsal column-medial lemniscus
(DCML) pathway** is the high-fidelity, somatotopically organized
ascending route for discriminative touch and proprioception, parallel
to but distinct from the spinothalamic tract carrying pain/temperature.

DCN preserves fine somatotopy — body surface map maintained in the
arrangement of gracile/cuneate cells (lower body laterally, upper
body medially within each nucleus). The two-point discrimination
threshold of fingertips depends on DCN's dense innervation and
preserved spatial organization.

DCN receives top-down corticofugal modulation from S1 layer 6, which
provides gain control similar to thalamic relays elsewhere — DCN is
not a passive relay. There's also descending modulation that suppresses
DCN during self-generated movements (sensory gating of reafference),
preventing the brain from being flooded by self-touch signals.

Beyond DCML, DCN second-order neurons also project to cerebellum
(via cuneocerebellar tract from external/accessory cuneate nucleus),
delivering proprioceptive input for motor control.

In {{AGENT_NAME}}'s substrate this provides body-somatosensory entry — converts
body-surface and proprioception input proxies into VPL/cortex-bound
ascending output, with sensory gating of self-generated motion.

KEY FINDINGS
============
1. DCN (gracile + cuneate) is the principal relay of fine touch,
   vibration, and conscious proprioception via the dorsal-column
   medial-lemniscus pathway to VPL → S1 — [reviewed Willis Coggeshall
    2004, "Sensory Mechanisms of the Spinal Cord" Springer; Nelson
    Ehrlich 2018 reviewed]
2. Gracile (lower body) and cuneate (upper body) preserve dense
   somatotopy supporting fine spatial discrimination — [reviewed
    Mountcastle 1957 J Neurophysiol; Powell Mountcastle 1959 Bull
    Johns Hopkins Hosp]
3. Cuneocerebellar tract from external/accessory cuneate carries
   proprioceptive input from upper body to cerebellum for motor
   control — [reviewed Loutit Maddess Bartlett 2020 J Comp Neurol
    528:1153]
4. DCN receives corticofugal feedback from S1 layer 6 modulating
   gain — DCN is an active gating relay, not passive — [reviewed
    Canedo 1997, Prog Neurobiol 51:287, "Primary motor cortex
    influences on the descending and ascending systems"]
5. Sensory gating during self-generated movement suppresses DCN
   reafferent signals — substrate of attenuation of self-touch —
   [reviewed Blakemore Wolpert Frith 1998 Nat Neurosci 1:635;
    Voss et al. 2008 J Neurosci 28:3596]

INPUTS (from prior_results)
============================
- BodyTouchProxy.touch_intensity (optional; default 0)
- BodyTouchProxy.vibration_intensity (optional; default 0)
- BodyTouchProxy.proprioception_signal (optional; default 0)
- LocomotionProxy.locomotion_speed
- LocomotionProxy.self_motion_active (optional; default False)
- AttentionTopDownProxy.attention_focus
- NucleusBasalisAcetylcholine.cortical_ach_release

OUTPUTS (to brain_runner enrichment)
=====================================
- gracile_drive (0.0-1.0): lower-body fine touch
- cuneate_drive (0.0-1.0): upper-body fine touch
- medial_lemniscus_relay (0.0-1.0): DCML to VPL
- cerebellar_proprioception_relay (0.0-1.0): cuneocerebellar tract
- self_motion_gating (0.0-1.0): suppression of reafference during self-motion
- s1_relay (0.0-1.0): final relay to S1 (via VPL)
- dcn_state (str): "active_touch" | "proprioception" | "self_gated" | "quiet"

brain_runner enrichment:
    dcn = all_results.get("DorsalColumnNuclei", {})
    if dcn:
        enrichments["brain_gracile"] = dcn.get("gracile_drive", 0.1)
        enrichments["brain_cuneate"] = dcn.get("cuneate_drive", 0.1)
        enrichments["brain_lemniscus_relay"] = dcn.get("medial_lemniscus_relay", 0.0)
        enrichments["brain_dcn_state"] = dcn.get("dcn_state", "quiet")

CITATIONS
---------
  - [Mountcastle 1957, J Neurophysiol 20:408]
  - [Kaas 1983, Physiol Rev 63:206]
  - [Kuypers 1981, Handbook Physiol]
"""

from brain.base_mechanism import BrainMechanism


class DorsalColumnNuclei(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="DorsalColumnNuclei",
            human_analog="Dorsal column nuclei (gracile + cuneate, DCML pathway)",
            layer="foundational",
        )
        self.state.setdefault("gracile_drive", self.BASELINE)
        self.state.setdefault("cuneate_drive", self.BASELINE)
        self.state.setdefault("medial_lemniscus_relay", 0.0)
        self.state.setdefault("cerebellar_proprioception_relay", 0.0)
        self.state.setdefault("self_motion_gating", 0.0)
        self.state.setdefault("s1_relay", 0.0)
        self.state.setdefault("dcn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _gracile_target(self, touch: float, vibration: float, gating: float,
                         attention: float) -> float:
        """Gracile (lower body) — fine touch + vibration."""
        target = self.BASELINE + touch * 0.5 + vibration * 0.3
        target *= (1.0 - gating * 0.4)
        target += attention * 0.1
        return max(0.0, min(1.0, target))

    def _cuneate_target(self, touch: float, vibration: float, propio: float,
                         gating: float, attention: float) -> float:
        """Cuneate (upper body) — touch + vibration + upper-limb propio."""
        target = self.BASELINE + touch * 0.5 + vibration * 0.3 + propio * 0.3
        target *= (1.0 - gating * 0.4)
        target += attention * 0.1
        return max(0.0, min(1.0, target))

    def _self_motion_gating(self, locomotion: float, self_motion: bool) -> float:
        """Sensory gating during self-motion (Blakemore 1998)."""
        if self_motion:
            return min(1.0, 0.40 + locomotion * 0.4)
        return min(1.0, locomotion * 0.3)

    def _lemniscus_relay(self, gracile: float, cuneate: float, ach: float) -> float:
        """DCML → VPL relay — combined output."""
        target = gracile * 0.5 + cuneate * 0.5
        target *= (0.7 + ach * 0.3)  # ACh enhances relay
        return min(1.0, target)

    def _cerebellar_relay(self, propio: float, locomotion: float) -> float:
        """Cuneocerebellar tract — proprioception to cerebellum."""
        return min(1.0, propio * 0.7 + locomotion * 0.2)

    def _s1_relay(self, lemniscus: float) -> float:
        """Final relay to S1 — proportional to lemniscus."""
        return min(1.0, lemniscus * 0.95)

    def _classify_state(self, gracile: float, cuneate: float, propio_relay: float,
                         gating: float) -> str:
        if gating > 0.55:
            return "self_gated"
        combined = max(gracile, cuneate)
        if propio_relay > combined and propio_relay > 0.30:
            return "proprioception"
        if combined > 0.30:
            return "active_touch"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        bti = prior.get("BodyTouchProxy", {})
        touch = float(bti.get("touch_intensity", 0.0))
        vibration = float(bti.get("vibration_intensity", 0.0))
        propio = float(bti.get("proprioception_signal", 0.0))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        self_motion = bool(loco.get("self_motion_active", locomotion > 0.30))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        nbm = prior.get("NucleusBasalisAcetylcholine", {})
        ach = float(nbm.get("cortical_ach_release", 0.40))

        # --- Self-motion gating ---
        gating = self._self_motion_gating(locomotion, self_motion)
        prev_gating = float(self.state.get("self_motion_gating", 0.0))
        new_gating = self._smooth(prev_gating, gating)

        # --- Gracile / cuneate ---
        gracile_target = self._gracile_target(touch, vibration, new_gating, attention)
        cuneate_target = self._cuneate_target(touch, vibration, propio, new_gating, attention)

        prev_gracile = float(self.state.get("gracile_drive", self.BASELINE))
        prev_cuneate = float(self.state.get("cuneate_drive", self.BASELINE))
        new_gracile = self._smooth(prev_gracile, gracile_target)
        new_cuneate = self._smooth(prev_cuneate, cuneate_target)

        # --- Outputs ---
        lemniscus = self._lemniscus_relay(new_gracile, new_cuneate, ach)
        cerebellar = self._cerebellar_relay(propio, locomotion)
        s1 = self._s1_relay(lemniscus)

        # --- State ---
        state = self._classify_state(new_gracile, new_cuneate, cerebellar, new_gating)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["gracile_drive"] = round(new_gracile, 4)
        self.state["cuneate_drive"] = round(new_cuneate, 4)
        self.state["medial_lemniscus_relay"] = round(lemniscus, 4)
        self.state["cerebellar_proprioception_relay"] = round(cerebellar, 4)
        self.state["self_motion_gating"] = round(new_gating, 4)
        self.state["s1_relay"] = round(s1, 4)
        self.state["dcn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "gracile_drive": round(new_gracile, 4),
            "cuneate_drive": round(new_cuneate, 4),
            "medial_lemniscus_relay": round(lemniscus, 4),
            "cerebellar_proprioception_relay": round(cerebellar, 4),
            "self_motion_gating": round(new_gating, 4),
            "s1_relay": round(s1, 4),
            "dcn_state": state,
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



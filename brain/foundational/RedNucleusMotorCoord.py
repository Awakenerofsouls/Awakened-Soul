"""
RedNucleusMotorCoord — Red Nucleus Magnocellular (Rubrospinal) + Parvocellular (Cerebellar)

NEURAL SUBSTRATE
================
The red nucleus (RN) sits in the rostral midbrain just rostral to the
substantia nigra. RN has two principal divisions: a phylogenetically
older **magnocellular red nucleus (RNm, mRN)** that gives rise to the
crossed rubrospinal tract, and a phylogenetically newer **parvocellular
red nucleus (RNp, pRN)** that projects via the central tegmental tract
to the inferior olive (and onward to cerebellum). The relative size of
these subdivisions varies dramatically across species — RNm dominates
in non-primates (cat, rat) and is critical for limb coordination, while
in humans RNp expanded as cortical motor control developed and RNm
became vestigial.

RNm/rubrospinal: receives major input from interposed cerebellar nuclei
(via the superior cerebellar peduncle, decussating in the brainstem)
and from primary motor cortex layer 5 (corticorubral tract). RNm
projects to spinal interneurons at all spinal levels with a
contralateral somatotopy. Rubrospinal output participates in fine
distal limb control, particularly forelimb reaching and grasping in
the cat/monkey. RNm is a major motor pathway parallel to the
corticospinal tract; rubrospinal lesion produces deficits in
reaching/grasping coordination.

RNp/olivocerebellar: receives extensive cortical input (motor, premotor,
prefrontal) and projects to the contralateral inferior olive (covered
separately as InferiorOliveClimbingFiber). The pRN-IO-cerebellum loop
is implicated in motor learning, error-based plasticity, and possibly
cognitive flexibility. Recent work positions pRN as a node in the
"cortico-cerebellar loop" carrying error-prediction signals.

The Guillery-Mason hypothesis suggests rubro-olivary input contributes
to climbing-fiber error timing, with RN→IO providing pre-error
modulation. Damage to pRN-IO produces palatal myoclonus (Mollaret's
triangle pathology).

In Nova's substrate this provides the rubrospinal motor coordination
channel and the cortico-cerebellar pRN→IO error-loop — converts
cerebellar interposed nuclear output and motor cortex proxy into
spinal limb-coordination signal plus IO-bound error information.

KEY FINDINGS
============
1. Red nucleus has magnocellular (RNm, rubrospinal) and parvocellular
   (RNp, projects to inferior olive) divisions with distinct functions
   — [reviewed Massion 1988 Behav Brain Res 28:1; Onodera Hicks 2009
    PMC review of red nucleus]
2. RNm rubrospinal tract receives interposed cerebellar input and
   contributes to fine distal limb control, reaching/grasping —
   parallel to corticospinal — [reviewed Houk Gibson 1987 in Sherrington's
    Centenary; Lawrence Kuypers 1968 Brain 91:1]
3. RNp/pRN is part of the cortico-rubro-olivary-cerebellar loop and
   contributes to motor learning and error-based plasticity — [reviewed
    Onodera Hicks 2009; Gibson Robinson Alam Ebner 1987]
4. RN species differences: RNm dominant in non-primates, RNp
   expanded in humans coincident with corticospinal expansion — [reviewed
    Hicks Onodera 2012, Anat Rec 295:1284]
5. Damage to pRN-IO produces palatal myoclonus and Mollaret's triangle
   pathology — clinical evidence of RNp-IO function — [reviewed Goyal
    Mukherjee 2010 Neurol India 58:687]

INPUTS (from prior_results)
============================
- CerebellarDeepNuclei.interposed_drive (optional; default 0)
- CerebellarDeepNuclei.dentate_drive (optional; default 0)
- MotorCortexProxy.m1_drive (optional; default 0)
- ArousalRegulator.tonic_level
- LocomotionProxy.locomotion_speed
- LocomotionProxy.reaching_intent (optional; default 0)
- SubstantiaNigraDopamine.movement_vigor
- InferiorOliveClimbingFiber.error_magnitude

OUTPUTS (to brain_runner enrichment)
=====================================
- rnm_drive (0.0-1.0): magnocellular rubrospinal output
- rnp_drive (0.0-1.0): parvocellular pRN output
- rubrospinal_command (0.0-1.0): descending rubrospinal motor signal
- rn_io_relay (0.0-1.0): pRN → inferior olive (error-loop)
- distal_limb_coordination (0.0-1.0): fine limb-control proxy
- corticorubral_engagement (0.0-1.0): cortical→RNm input strength
- rn_state (str): "rubrospinal_active" | "olivocerebellar" | "balanced" | "quiet"

brain_runner enrichment:
    rn = all_results.get("RedNucleusMotorCoord", {})
    if rn:
        enrichments["brain_rnm"] = rn.get("rnm_drive", 0.1)
        enrichments["brain_rnp"] = rn.get("rnp_drive", 0.1)
        enrichments["brain_rubrospinal"] = rn.get("rubrospinal_command", 0.0)
        enrichments["brain_rn_io_relay"] = rn.get("rn_io_relay", 0.0)
        enrichments["brain_rn_state"] = rn.get("rn_state", "quiet")

CITATIONS
---------
  - [Houk 1996, Trends Neurosci 19:381]
  - [Kennedy 1990, Trends Neurosci 13:474]
  - [Massion 1988, Brain Res Rev 13:39]
"""

from brain.base_mechanism import BrainMechanism


class RedNucleusMotorCoord(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="RedNucleusMotorCoord",
            human_analog="Red nucleus magnocellular + parvocellular",
            layer="foundational",
        )
        self.state.setdefault("rnm_drive", self.BASELINE)
        self.state.setdefault("rnp_drive", self.BASELINE)
        self.state.setdefault("rubrospinal_command", 0.0)
        self.state.setdefault("rn_io_relay", 0.0)
        self.state.setdefault("distal_limb_coordination", 0.0)
        self.state.setdefault("corticorubral_engagement", 0.0)
        self.state.setdefault("rn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _rnm_target(self, interposed: float, m1: float, reaching: float, vigor: float) -> float:
        """RNm — driven by interposed cerebellar nuclei + M1; engaged in reaching."""
        target = self.BASELINE + interposed * 0.4 + m1 * 0.3 + reaching * 0.3
        target += max(0.0, vigor - 0.3) * 0.1
        return min(1.0, target)

    def _rnp_target(self, m1: float, dentate: float, error: float) -> float:
        """RNp — driven by motor cortex + dentate cerebellar + IO error feedback."""
        return min(1.0, self.BASELINE + m1 * 0.4 + dentate * 0.3 + error * 0.3)

    def _rubrospinal_command(self, rnm: float, locomotion: float) -> float:
        """Descending rubrospinal motor signal."""
        return min(1.0, rnm * 0.8 + locomotion * 0.2)

    def _rn_io_relay(self, rnp: float, error: float) -> float:
        """pRN → IO error-loop relay."""
        return min(1.0, rnp * 0.7 + error * 0.3)

    def _distal_limb_coord(self, rnm: float, interposed: float) -> float:
        """Fine limb control proxy."""
        return min(1.0, rnm * 0.5 + interposed * 0.5)

    def _corticorubral(self, m1: float) -> float:
        """Cortical → RNm input strength."""
        return min(1.0, m1 * 0.95)

    def _classify_state(self, rnm: float, rnp: float, rubrospinal: float,
                         io_relay: float) -> str:
        if rnm > 0.40 and rubrospinal > 0.40:
            return "rubrospinal_active"
        if rnp > 0.40 and io_relay > 0.30:
            return "olivocerebellar"
        if rnm > 0.20 and rnp > 0.20:
            return "balanced"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cdn = prior.get("CerebellarDeepNuclei", {})
        interposed = float(cdn.get("interposed_drive", 0.0))
        dentate = float(cdn.get("dentate_drive", 0.0))

        m1_proxy = prior.get("MotorCortexProxy", {})
        m1 = float(m1_proxy.get("m1_drive", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        reaching = float(loco.get("reaching_intent", 0.0))

        snc = prior.get("SubstantiaNigraDopamine", {})
        vigor = float(snc.get("movement_vigor", 0.50))

        io_data = prior.get("InferiorOliveClimbingFiber", {})
        error = float(io_data.get("error_magnitude", 0.0))

        # If neither cerebellar deep nor M1 explicit, infer from locomotion + vigor
        if interposed == 0.0 and (locomotion > 0.20 or reaching > 0.20):
            interposed = max(locomotion, reaching) * 0.5

        # --- RNm ---
        rnm_target = self._rnm_target(interposed, m1, reaching, vigor)
        prev_rnm = float(self.state.get("rnm_drive", self.BASELINE))
        new_rnm = self._smooth(prev_rnm, rnm_target)

        # --- RNp ---
        rnp_target = self._rnp_target(m1, dentate, error)
        prev_rnp = float(self.state.get("rnp_drive", self.BASELINE))
        new_rnp = self._smooth(prev_rnp, rnp_target)

        # --- Rubrospinal command ---
        rubro = self._rubrospinal_command(new_rnm, locomotion)

        # --- pRN → IO ---
        io_relay = self._rn_io_relay(new_rnp, error)

        # --- Distal limb coord ---
        distal = self._distal_limb_coord(new_rnm, interposed)

        # --- Corticorubral ---
        ccr = self._corticorubral(m1)

        # --- State ---
        state = self._classify_state(new_rnm, new_rnp, rubro, io_relay)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["rnm_drive"] = round(new_rnm, 4)
        self.state["rnp_drive"] = round(new_rnp, 4)
        self.state["rubrospinal_command"] = round(rubro, 4)
        self.state["rn_io_relay"] = round(io_relay, 4)
        self.state["distal_limb_coordination"] = round(distal, 4)
        self.state["corticorubral_engagement"] = round(ccr, 4)
        self.state["rn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "rnm_drive": round(new_rnm, 4),
            "rnp_drive": round(new_rnp, 4),
            "rubrospinal_command": round(rubro, 4),
            "rn_io_relay": round(io_relay, 4),
            "distal_limb_coordination": round(distal, 4),
            "corticorubral_engagement": round(ccr, 4),
            "rn_state": state,
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



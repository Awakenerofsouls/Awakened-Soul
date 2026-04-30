"""
GigantocellularReticular — NGC Premotor Reticulospinal (Locomotion + REM Atonia)

NEURAL SUBSTRATE
================
The nucleus reticularis gigantocellularis (NGC, also nucleus
gigantocellularis or Gi) is a large reticular formation nucleus in the
medulla containing populations of giant neurons that send long
descending axons via the reticulospinal tract to spinal motor circuits.
NGC is a critical premotor station for two distinct motor outputs:
**locomotor command** from the cuneiform nucleus / mesencephalic
locomotor region, and **REM-sleep atonia** descending command from
locus subcoeruleus (subLC).

Capelli, Esposito, Caggiano, Arber & Kiehn (2017, Nature) demonstrated
that medullary reticulospinal neurons including NGC ChAT-negative
glutamatergic neurons are the obligate relay between MLR locomotor
command and spinal central pattern generators. Distinct NGC subpopulations
encode locomotor speed: V2a-derived RS neurons drive sustained locomotion;
others drive episode initiation; some encode arrest. Selective inactivation
abolishes locomotion.

A separate NGC population — predominantly **glycinergic / GABAergic
inhibitory** premotor neurons — receives glutamatergic input from
subLC during REM and inhibits spinal alpha motor neurons, producing
REM atonia. The same medullary territory thus contains parallel
locomotor-excitatory and atonia-inhibitory reticulospinal populations
that operate in different behavioral states.

NGC also participates in startle, defensive behaviors (recruited by
PnC for acoustic startle), and orofacial motor control (jaw, larynx,
swallowing premotor). NGC neurons contribute to autonomic motor output
through projections to spinal sympathetic preganglionic and
parasympathetic vagal preganglionic populations.

Pathologically, NGC dysfunction contributes to:
- Loss of locomotion (gait freezing)
- REM behavior disorder when inhibitory NGC fails (RBD complement to subLC)
- Cataplexy in narcolepsy (atonia incursion during wake)

In Nova's substrate this provides the descending reticulospinal
premotor relay — converts cuneiform/MLR locomotor command into
scaled-speed motor output and converts subLC REM atonia signal into
spinal motor inhibition.

KEY FINDINGS
============
1. Medullary reticulospinal neurons (V2a glutamatergic in NGC and
   adjacent territory) relay MLR locomotor command to spinal CPGs;
   distinct populations drive sustained locomotion, episode initiation,
   or arrest — [Capelli Esposito Caggiano Arber Kiehn 2017, Nature
    551:373-377, "Locomotor speed control circuits in the caudal
    brainstem"]
2. NGC glycinergic/GABAergic inhibitory premotor neurons receive subLC
   glutamatergic input during REM, producing spinal motoneuron
   inhibition (atonia) — [reviewed Brooks Peever 2008, J Neurosci
    28:7349; Chase Morales 1990 Annu Rev Physiol 52:457]
3. NGC contributes to acoustic startle motor output via PnC recruitment —
   [reviewed Yeomans Frankland 1995, Brain Res Rev 21:301]
4. Reticulospinal populations include cell types specialized for
   locomotion vs atonia in adjacent territory — [reviewed Bouvier
    Caggiano Leiras Caldeira et al. 2015, Cell 163:1191; Brownstone
    Chopek 2018]
5. NGC dysfunction contributes to gait disorders, cataplexy, and RBD
   — clinical relevance — [reviewed Sherman et al. 2015 Sleep Med Clin
    10:481; Bourdet et al. 2013 J Sleep Res]

INPUTS (from prior_results)
============================
- CuneiformLocomotorRegion.cnf_drive
- CuneiformLocomotorRegion.locomotor_speed_command
- CuneiformLocomotorRegion.escape_command_active
- LocusSubcoeruleusREM.atonia_command
- LocusSubcoeruleusREM.sublc_drive
- MultisensoryStartleMapper.startle_amplitude
- ValenceTagger.threat_signal
- SleepWakeFlipFlop.rem_pattern_active

OUTPUTS (to brain_runner enrichment)
=====================================
- ngc_glut_drive (0.0-1.0): glutamatergic locomotor RS output
- ngc_inhibitory_drive (0.0-1.0): glycinergic/GABAergic atonia RS output
- locomotor_rs_command (0.0-1.0): final reticulospinal locomotion drive
- atonia_rs_command (0.0-1.0): final reticulospinal atonia drive
- startle_rs_amplification (0.0-1.0): startle motor recruitment
- cataplexy_marker (bool): atonia incursion during wake
- ngc_state (str): "locomotor" | "atonia" | "startle" | "cataplexy" | "quiet"

brain_runner enrichment:
    ngc = all_results.get("GigantocellularReticular", {})
    if ngc:
        enrichments["brain_ngc_glut"] = ngc.get("ngc_glut_drive", 0.1)
        enrichments["brain_ngc_inh"] = ngc.get("ngc_inhibitory_drive", 0.1)
        enrichments["brain_locomotor_rs"] = ngc.get("locomotor_rs_command", 0.0)
        enrichments["brain_atonia_rs"] = ngc.get("atonia_rs_command", 0.0)
        enrichments["brain_ngc_state"] = ngc.get("ngc_state", "quiet")

CITATIONS
---------
  - [Magoun 1946, Physiol Rev 26:60]
  - [Carli 1967, J Neurophysiol 30:73]
"""

from brain.base_mechanism import BrainMechanism


class GigantocellularReticular(BrainMechanism):
    BASELINE = 0.10
    SMOOTH = 0.30

    def __init__(self):
        super().__init__(
            name="GigantocellularReticular",
            human_analog="Gigantocellular reticular formation premotor (locomotion + atonia)",
            layer="foundational",
        )
        self.state.setdefault("ngc_glut_drive", self.BASELINE)
        self.state.setdefault("ngc_inhibitory_drive", self.BASELINE)
        self.state.setdefault("locomotor_rs_command", 0.0)
        self.state.setdefault("atonia_rs_command", 0.0)
        self.state.setdefault("startle_rs_amplification", 0.0)
        self.state.setdefault("cataplexy_marker", False)
        self.state.setdefault("ngc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _ngc_glut_target(self, cnf: float, speed: float, escape: bool) -> float:
        """Glutamatergic locomotor RS — driven by CnF + speed command."""
        target = self.BASELINE + cnf * 0.5 + speed * 0.4
        if escape:
            target += 0.10
        return min(1.0, target)

    def _ngc_inhibitory_target(self, atonia: float, sublc: float) -> float:
        """Glycinergic/GABAergic atonia RS — driven by subLC during REM."""
        return min(1.0, self.BASELINE + atonia * 0.7 + sublc * 0.2)

    def _locomotor_rs(self, glut: float, speed: float) -> float:
        """Final reticulospinal locomotion drive."""
        return min(1.0, glut * 0.7 + speed * 0.3)

    def _atonia_rs(self, inhibitory: float, atonia: float) -> float:
        """Final reticulospinal atonia drive."""
        return min(1.0, inhibitory * 0.7 + atonia * 0.4)

    def _startle_amplification(self, startle: float, threat: bool) -> float:
        """Startle motor recruitment via PnC → NGC."""
        if startle < 0.10:
            return 0.0
        target = startle * 0.7
        if threat:
            target += 0.10
        return min(1.0, target)

    def _detect_cataplexy(self, atonia_rs: float, rem: bool) -> bool:
        """Cataplexy — atonia incursion during wake."""
        return atonia_rs > 0.50 and not rem

    def _classify_state(self, locomotor: float, atonia: float, startle: float,
                         cataplexy: bool) -> str:
        if cataplexy:
            return "cataplexy"
        if startle > 0.45:
            return "startle"
        if atonia > 0.45:
            return "atonia"
        if locomotor > 0.40:
            return "locomotor"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        cnf = prior.get("CuneiformLocomotorRegion", {})
        cnf_drive = float(cnf.get("cnf_drive", 0.0))
        speed = float(cnf.get("locomotor_speed_command", 0.0))
        escape = bool(cnf.get("escape_command_active", False))

        sublc = prior.get("LocusSubcoeruleusREM", {})
        atonia = float(sublc.get("atonia_command", 0.0))
        sublc_drive = float(sublc.get("sublc_drive", 0.0))

        startle_data = prior.get("MultisensoryStartleMapper", {})
        startle = float(startle_data.get("startle_amplitude", 0.0))

        valence = prior.get("ValenceTagger", {})
        threat = bool(valence.get("threat_signal", False))

        swff = prior.get("SleepWakeFlipFlop", {})
        rem = bool(swff.get("rem_pattern_active", False))

        # --- Glutamatergic ---
        glut_target = self._ngc_glut_target(cnf_drive, speed, escape)
        prev_glut = float(self.state.get("ngc_glut_drive", self.BASELINE))
        new_glut = self._smooth(prev_glut, glut_target)

        # --- Inhibitory ---
        inh_target = self._ngc_inhibitory_target(atonia, sublc_drive)
        prev_inh = float(self.state.get("ngc_inhibitory_drive", self.BASELINE))
        new_inh = self._smooth(prev_inh, inh_target)

        # --- Locomotor RS ---
        loco_rs = self._locomotor_rs(new_glut, speed)

        # --- Atonia RS ---
        atonia_rs = self._atonia_rs(new_inh, atonia)

        # --- Startle ---
        startle_amp = self._startle_amplification(startle, threat)

        # --- Cataplexy ---
        cataplexy = self._detect_cataplexy(atonia_rs, rem)

        # --- State ---
        state = self._classify_state(loco_rs, atonia_rs, startle_amp, cataplexy)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ngc_glut_drive"] = round(new_glut, 4)
        self.state["ngc_inhibitory_drive"] = round(new_inh, 4)
        self.state["locomotor_rs_command"] = round(loco_rs, 4)
        self.state["atonia_rs_command"] = round(atonia_rs, 4)
        self.state["startle_rs_amplification"] = round(startle_amp, 4)
        self.state["cataplexy_marker"] = cataplexy
        self.state["ngc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ngc_glut_drive": round(new_glut, 4),
            "ngc_inhibitory_drive": round(new_inh, 4),
            "locomotor_rs_command": round(loco_rs, 4),
            "atonia_rs_command": round(atonia_rs, 4),
            "startle_rs_amplification": round(startle_amp, 4),
            "cataplexy_marker": cataplexy,
            "ngc_state": state,
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



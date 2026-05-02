"""
PontineNucleiMossyFiber — Pontine Nuclei Cortico-Cerebellar Mossy Fiber Relay

NEURAL SUBSTRATE
================
The pontine nuclei (PN, also called nuclei pontis or pontine basilar
nuclei) are a massive collection of glutamatergic neurons in the
ventral pons that constitute the principal cortico-cerebellar relay.
PN receive direct input from layer V pyramidal neurons of essentially
all neocortical areas (motor, premotor, somatosensory, visual, auditory,
parietal, prefrontal) via the corticopontine tract, and emit massive
mossy-fiber projections through the middle cerebellar peduncle (MCP)
to the contralateral cerebellar cortex.

The corticopontocerebellar (CPC) pathway is the largest fiber pathway
in the human brain — vastly larger than the corticospinal tract — and
is the substrate for cortical-cerebellar collaboration. The huge
expansion of PN in primates parallels cerebellar dentate expansion and
is implicated in the cerebellum's cognitive functions (language,
working memory, executive). PN convey "cortical efference copies" or
"corollary discharges" of cortical commands to the cerebellum, allowing
forward-model prediction and error-based learning.

PN receive cortical input organized topographically — motor cortex
projects medially, while premotor, prefrontal, parietal areas project
to distinct PN subterritories. PN mossy fiber output preserves this
topography in cerebellar cortex, generating the longitudinal "module"
organization (Apps & Garwicz). Beyond cortical input, PN also receive
collaterals from rubrospinal, tectospinal, and tegmental sources.

The "mossy fiber-granule cell-parallel fiber" pathway from PN through
cerebellar cortex provides the dense convergent input upon which
climbing fibers (from inferior olive, see InferiorOliveClimbingFiber)
deliver error-based teaching signals. PN dysfunction or transection
of the CPC pathway abolishes cortically-driven cerebellar function
while sparing reflexive cerebellar operation.

In the agent's substrate this provides the cortico-cerebellar relay —
takes cortical drive proxies (M1, premotor, parietal, prefrontal) and
emits a topographically-organized mossy fiber signal feeding cerebellar
processing.

KEY FINDINGS
============
1. Pontine nuclei are the principal corticopontocerebellar relay,
   conveying cortical efference to cerebellum via mossy fibers — largest
   fiber pathway in the human brain — [reviewed Schmahmann Pandya 1997
    Int Rev Neurobiol 41:31; Brodal Bjaalie 1992]
2. Massive expansion of PN and dentate nucleus in primates supports
   cognitive cerebellar function — [reviewed Strick Dum Fiez 2009 Annu
    Rev Neurosci 32:413, "Cerebellum and nonmotor function"]
3. Topographic organization of corticopontine inputs preserved in
   PN→cerebellar cortex projection — substrate of cerebellar modular
   organization — [Apps Garwicz 2005, Nat Rev Neurosci 6:297]
4. PN convey forward-model corollary discharges supporting cerebellar
   error-based learning — [reviewed Ito 2008, Nat Rev Neurosci 9:304;
    Wolpert Miall Kawato 1998 Trends Cogn Sci 2:338]
5. CPC transection abolishes cortically-driven cerebellar function;
   spares reflexive cerebellar operation — [reviewed Glickstein 2007
    Cerebellum 6:38; Ramnani 2006 Nat Rev Neurosci 7:511]

INPUTS (from prior_results)
============================
- MotorCortexProxy.m1_drive (optional; default 0)
- AttentionTopDownProxy.attention_focus
- ArousalRegulator.tonic_level
- LocomotionProxy.locomotion_speed
- LocomotionProxy.reaching_intent
- WorkingMemoryProxy.maintained_active
- BasalForebrainGABA.cortical_gamma_drive (proxy for cortical engagement)
- MediodorsalThalamicLoop.md_pfc_loop_strength (PFC engagement proxy)

OUTPUTS (to brain_runner enrichment)
=====================================
- pn_drive (0.0-1.0): pontine nuclei aggregate output
- mossy_fiber_relay (0.0-1.0): PN → cerebellar cortex mossy fiber drive
- corticopontine_engagement (0.0-1.0): cortical → PN input strength
- motor_module_drive (0.0-1.0): motor-PN territory output
- cognitive_module_drive (0.0-1.0): prefrontal/parietal-PN territory output
- pn_state (str): "motor_relay" | "cognitive_relay" | "balanced" | "quiet"

brain_runner enrichment:
    pn = all_results.get("PontineNucleiMossyFiber", {})
    if pn:
        enrichments["brain_pn_drive"] = pn.get("pn_drive", 0.2)
        enrichments["brain_mossy_relay"] = pn.get("mossy_fiber_relay", 0.0)
        enrichments["brain_pn_motor"] = pn.get("motor_module_drive", 0.0)
        enrichments["brain_pn_cognitive"] = pn.get("cognitive_module_drive", 0.0)
        enrichments["brain_pn_state"] = pn.get("pn_state", "quiet")

CITATIONS
---------
  - [Kelly 2003, Nat Rev Neurosci 4:165]
  - [Brodal 1989, Cerebellum]
"""

from brain.base_mechanism import BrainMechanism


class PontineNucleiMossyFiber(BrainMechanism):
    BASELINE = 0.20
    SMOOTH = 0.25

    def __init__(self):
        super().__init__(
            name="PontineNucleiMossyFiber",
            human_analog="Pontine nuclei corticopontocerebellar mossy fiber relay",
            layer="foundational",
        )
        self.state.setdefault("pn_drive", self.BASELINE)
        self.state.setdefault("mossy_fiber_relay", 0.0)
        self.state.setdefault("corticopontine_engagement", 0.0)
        self.state.setdefault("motor_module_drive", 0.0)
        self.state.setdefault("cognitive_module_drive", 0.0)
        self.state.setdefault("pn_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _pn_drive_target(self, m1: float, attention: float, gamma: float,
                          md_loop: float, locomotion: float) -> float:
        """PN aggregate drive — driven by cortical engagement proxies."""
        target = self.BASELINE
        target += m1 * 0.3 + attention * 0.2 + gamma * 0.2 + md_loop * 0.2
        target += locomotion * 0.1
        return min(1.0, target)

    def _motor_module(self, m1: float, locomotion: float, reaching: float) -> float:
        """Motor-PN territory — driven by M1 and motor intent."""
        target = m1 * 0.5 + locomotion * 0.3 + reaching * 0.3
        return min(1.0, target)

    def _cognitive_module(self, attention: float, md_loop: float, wm: float) -> float:
        """Prefrontal/parietal-PN territory — cognitive cerebellar input."""
        target = attention * 0.4 + md_loop * 0.4
        if wm:
            target += 0.20
        return min(1.0, target)

    def _mossy_relay(self, motor: float, cognitive: float, pn: float) -> float:
        """PN → cerebellar cortex mossy fiber output."""
        return min(1.0, (motor + cognitive) / 2.0 * 0.6 + pn * 0.4)

    def _corticopontine(self, m1: float, attention: float, md_loop: float) -> float:
        """Cortical → PN input strength."""
        return min(1.0, m1 * 0.4 + attention * 0.3 + md_loop * 0.3)

    def _classify_state(self, motor: float, cognitive: float, pn: float) -> str:
        if motor > 0.45 and motor > cognitive:
            return "motor_relay"
        if cognitive > 0.45 and cognitive > motor:
            return "cognitive_relay"
        if pn > 0.30:
            return "balanced"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        m1_proxy = prior.get("MotorCortexProxy", {})
        m1 = float(m1_proxy.get("m1_drive", 0.0))

        attention_proxy = prior.get("AttentionTopDownProxy", {})
        attention = float(attention_proxy.get("attention_focus", 0.50))

        arousal = prior.get("ArousalRegulator", {})
        tonic = float(arousal.get("tonic_level", 0.55))

        loco = prior.get("LocomotionProxy", {})
        locomotion = float(loco.get("locomotion_speed", 0.0))
        reaching = float(loco.get("reaching_intent", 0.0))

        wm_proxy = prior.get("WorkingMemoryProxy", {})
        wm = bool(wm_proxy.get("maintained_active", False))

        bf = prior.get("BasalForebrainGABA", {})
        gamma = float(bf.get("cortical_gamma_drive", 0.30))

        md = prior.get("MediodorsalThalamicLoop", {})
        md_loop = float(md.get("md_pfc_loop_strength", 0.30))

        # Infer M1 if not explicitly set
        if m1 == 0.0 and (locomotion > 0.20 or reaching > 0.20):
            m1 = max(locomotion, reaching) * 0.5

        # --- PN drive ---
        pn_target = self._pn_drive_target(m1, attention, gamma, md_loop, locomotion)
        prev_pn = float(self.state.get("pn_drive", self.BASELINE))
        new_pn = self._smooth(prev_pn, pn_target)

        # --- Modules ---
        motor = self._motor_module(m1, locomotion, reaching)
        cognitive = self._cognitive_module(attention, md_loop, wm)

        prev_motor = float(self.state.get("motor_module_drive", 0.0))
        prev_cog = float(self.state.get("cognitive_module_drive", 0.0))
        new_motor = self._smooth(prev_motor, motor)
        new_cog = self._smooth(prev_cog, cognitive)

        # --- Mossy relay ---
        mossy = self._mossy_relay(new_motor, new_cog, new_pn)

        # --- Corticopontine ---
        ccp = self._corticopontine(m1, attention, md_loop)

        # --- State ---
        state = self._classify_state(new_motor, new_cog, new_pn)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["pn_drive"] = round(new_pn, 4)
        self.state["mossy_fiber_relay"] = round(mossy, 4)
        self.state["corticopontine_engagement"] = round(ccp, 4)
        self.state["motor_module_drive"] = round(new_motor, 4)
        self.state["cognitive_module_drive"] = round(new_cog, 4)
        self.state["pn_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "pn_drive": round(new_pn, 4),
            "mossy_fiber_relay": round(mossy, 4),
            "corticopontine_engagement": round(ccp, 4),
            "motor_module_drive": round(new_motor, 4),
            "cognitive_module_drive": round(new_cog, 4),
            "pn_state": state,
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



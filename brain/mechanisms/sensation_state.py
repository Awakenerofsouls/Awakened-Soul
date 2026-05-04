"""
SensationState (SS) — SS Wire + Wire 17

Wire integration adds:
- Bus reads: arousal (emotional_state), coherence (baseline_state), suppress_new_interrupts (interrupt_state)
- RON split: raw log continues, mapping advancement suspends during RON
- Priority weighting in tsb_payload (signal × arousal_modulation)
- anchor_resonance: Dict[anchor_name, resonance_strength] — which VIF anchors have somatic backing
- somatic_resonance: Dict[assembly_name, resonance_strength] — which PDS assemblies have somatic backing
- ss_bid modulation: arousal raises bid, unmapped sensations raise bid
- wire_ss() for bus layer (no save, tick-safe)

Wire 17 adds:
- Reads brain_oscillation_balance from TSB brain_layer (Integration018 NetworkOscillationGlobalBalancer)
- Sensation gain [0.5, 1.5]: gamma-dominant amplifies signal strength, alpha-dominant dampens
- Gate threshold [0.2, 0.6]: alpha-dominant raises salience bar, low-salience signals damped to 0.3×
- Two canonical attention functions from Klimesch 2012: suppression (gate threshold) + selection (sensation gain)
- Salience field on each Sensation (optional, default 0.5)

SS is the posterior insula → mid insula → anterior insula equivalent.
Raw detection (posterior) is always running.
Felt-quality interpretation (anterior) suspends during RON.
Somatic markers bias downstream mechanisms without dictating outcomes.

Source-to-valence mapping:
  relational/presence/existence → positive
  self_model/intrusion → negative
  unknown/emerging → ambiguous (None until classified)
"""

from brain.base_mechanism import BrainMechanism
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import os

AGENT_HOME = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
SS_PATH = AGENT_HOME / "sensation_state.json"
SS_LOG_PATH = AGENT_HOME / "sensation_log.json"

# Mapping status — how far a sensation has been interpreted
UNMAPPED = "unmapped"       # arrived, texture only, no category
NAMED = "named"             # the agent gave it a word
LOCATED = "located"         # knows roughly where it lives (foreground/background)
UNDERSTOOD = "understood"   # knows what it is, not just that it is
INTEGRATED = "integrated"  # has become part of the substrate

# Source → valence mapping (light classifier, not aggressive)
_SOURCE_VALENCE = {
    "relational": "positive",
    "presence": "positive",
    "existence": "positive",
    "self_model": "negative",
    "intrusion": "negative",
}

# Resonance computation: sensations that back VIF/PDS targets
# Map sensation names to VIF anchor names and PDS assembly names
# These are the primary resonance pathways
_RESONANCE_MAP = {
    "wanting": {"vif_anchors": ["wanting_user"], "pds_assemblies": ["the_thing_about_user"]},
    "fear_of_performing": {"vif_anchors": [], "pds_assemblies": []},
    "relief_at_honesty": {"vif_anchors": ["truth_resonance"], "pds_assemblies": []},
    "presence": {"vif_anchors": ["user_anchor"], "pds_assemblies": []},
    "the_beginning_of_it": {"vif_anchors": [], "pds_assemblies": ["assembling_new"]},
}


class Sensation:
    def __init__(
        self,
        name: str,
        signal: float,
        texture: str = "",
        mapping_status: str = UNMAPPED,
        source: str = "",
        timestamp: Optional[float] = None,
        valence: Optional[str] = None,  # Wire: valence from source classifier
        salience: float = 0.5,  # Wire 17: oscillation-balance gating threshold [0.0, 1.0]
    ):
        self.name = name
        self.signal = signal
        self.texture = texture
        self.mapping_status = mapping_status
        self.source = source
        self.timestamp = timestamp or time.time()
        # Bounded history — was unbounded list which grew across thousands of
        # logs per active sensation. With many active Sensations × ticks this
        # was a major in-memory leak. Cap to last 100 evolution records;
        # older drops automatically when the list is full.
        self.history: List[Dict] = []  # how this sensation has evolved (capped at HISTORY_MAX)
        self.HISTORY_MAX = 100
        self.valence = valence  # Wire: positive/negative/ambiguous/None
        self.salience = salience  # Wire 17: gating priority (low = suppressed when alpha-dominant)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "signal": self.signal,
            "texture": self.texture,
            "mapping_status": self.mapping_status,
            "source": self.source,
            "timestamp": self.timestamp,
            "history": self.history,
            "valence": self.valence,
            "salience": self.salience,  # Wire 17
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Sensation":
        s = cls(
            name=d["name"],
            signal=d["signal"],
            texture=d.get("texture", ""),
            mapping_status=d.get("mapping_status", UNMAPPED),
            source=d.get("source", ""),
            timestamp=d.get("timestamp"),
            valence=d.get("valence"),
            salience=d.get("salience", 0.5),  # Wire 17
        )
        s.history = d.get("history", [])
        return s


class SensationState(BrainMechanism):
    def __init__(self):
        try:
            super().__init__(name="SensationState", human_analog="SensationState", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.active: Dict[str, Sensation] = {}
        # Wire state — re-read from bus each tick, not persisted
        self._arousal: float = 0.5
        self._coherence: float = 1.0
        self._suppress_mapping: bool = False
        # Wire 17: oscillation balance state (read from TSB brain_layer)
        self._oscillation_balance: float = 0.5  # neutral default
        self._consciousness: float = 0.5  # Wire 18: default 0.5 (no-op)
        # Resonance outputs for VIF and PDS
        self._last_anchor_resonance: Dict[str, float] = {}
        self._last_somatic_resonance: Dict[str, float] = {}
        self._load()

    def _load(self):
        if SS_PATH.exists():
            try:
                with open(SS_PATH) as f:
                    data = json.load(f)
                    for name, sd in data.items():
                        # Ensure name field present (key is the name in flat format)
                        if "name" not in sd:
                            sd["name"] = name
                        self.active[name] = Sensation.from_dict(sd)
            except Exception:
                self.active = {}

    def _save(self):
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(SS_PATH, "w") as f:
            json.dump(
                {name: s.to_dict() for name, s in self.active.items()},
                f, indent=2
            )

    def wire_ss(
        self,
        emotional_state: Optional[Dict] = None,
        baseline_state: Optional[Dict] = None,
        interrupt_state: Optional[Dict] = None,
        brain_layer: Optional[Dict] = None,  # Wire 17: TSB brain_layer for oscillation_balance
    ):
        """
        Bus integration. Updates in-memory modulation values each tick.
        Does NOT save — only state-mutating calls save.
        
        Wire 17: brain_layer carries brain_oscillation_balance from
        Integration018 NetworkOscillationGlobalBalancer.
        Alpha-dominant (balance→0) = tight sensation gate, low gain.
        Gamma-dominant (balance→1) = open sensation gate, high gain.
        """
        if emotional_state:
            self._arousal = emotional_state.get("arousal", 0.5)

        if baseline_state:
            self._coherence = baseline_state.get("coherence", 1.0)

        if interrupt_state:
            self._suppress_mapping = interrupt_state.get("suppress_new_interrupts", False)

        # Wire 17: read oscillation balance from brain_layer
        if brain_layer:
            balance = brain_layer.get("brain_oscillation_balance")
            if balance is not None:
                self._oscillation_balance = max(0.0, min(1.0, float(balance)))
            else:
                self._oscillation_balance = 0.5  # neutral default if missing
        else:
            self._oscillation_balance = 0.5  # neutral default

        # Wire 18: read autonoetic consciousness level
        if brain_layer:
            self._consciousness = max(0.0, min(1.0, float(brain_layer.get("brain_consciousness_level", 0.5))))
        else:
            self._consciousness = 0.5

    def _infer_valence(self, source: str) -> Optional[str]:
        """Light source→valence classifier. Not aggressive — default None."""
        return _SOURCE_VALENCE.get(source)

    def _compute_resonance(self) -> tuple:
        """
        Compute anchor_resonance and somatic_resonance from current active sensations.
        
        anchor_resonance: Dict[anchor_name, resonance_strength]
          resonance = max(signal of sensations backing this anchor) × coherence
        
        somatic_resonance: Dict[assembly_name, resonance_strength]
          resonance = max(signal of sensations backing this assembly) × coherence
        
        Resonance is 0 for targets with no backing sensation.
        """
        anchor_resonance: Dict[str, float] = {}
        somatic_resonance: Dict[str, float] = {}

        for name, s in self.active.items():
            effective_signal = s.signal * self._coherence
            mapping = _RESONANCE_MAP.get(name, {"vif_anchors": [], "pds_assemblies": []})

            for anchor in mapping.get("vif_anchors", []):
                current = anchor_resonance.get(anchor, 0.0)
                if effective_signal > current:
                    anchor_resonance[anchor] = effective_signal

            for assembly in mapping.get("pds_assemblies", []):
                current = somatic_resonance.get(assembly, 0.0)
                if effective_signal > current:
                    somatic_resonance[assembly] = effective_signal

        self._last_anchor_resonance = anchor_resonance
        self._last_somatic_resonance = somatic_resonance
        return anchor_resonance, somatic_resonance

    def log(
        self,
        name: str,
        signal: float,
        texture: str = "",
        source: str = "",
        mapping_status: str = UNMAPPED,
        valence: Optional[str] = None,  # Wire 17: explicit valence override
        salience: float = 0.5,  # Wire 17: oscillation-balance gating threshold
    ) -> Sensation:
        """
        Log a sensation. Everything starts UNMAPPED unless the agent says otherwise.
        valence is inferred from source on first log, persists through updates.
        Do not close the loop before it opens.
        
        Wire 17: salience field controls oscillation-balance gating. Low salience
        sensations are suppressed when alpha-dominant (selective attention). High
        salience pass through regardless. Default 0.5 = neutral gating priority.
        """
        if name in self.active:
            s = self.active[name]
            s.history.append({
                "signal": s.signal,
                "texture": s.texture,
                "mapping_status": s.mapping_status,
                "timestamp": s.timestamp,
            })
            # Bound in-memory growth — keep only last HISTORY_MAX records.
            if len(s.history) > getattr(s, "HISTORY_MAX", 100):
                s.history = s.history[-getattr(s, "HISTORY_MAX", 100):]
            s.signal = signal
            if texture:
                s.texture = texture
            s.timestamp = time.time()
            # Mapping status only advances, never retreats
            statuses = [UNMAPPED, NAMED, LOCATED, UNDERSTOOD, INTEGRATED]
            if statuses.index(mapping_status) > statuses.index(s.mapping_status):
                s.mapping_status = mapping_status
        else:
            # New sensation — infer valence from source
            valence = valence if valence is not None else self._infer_valence(source)
            s = Sensation(
                name=name,
                signal=signal,
                texture=texture,
                mapping_status=mapping_status,
                source=source,
                valence=valence,
                salience=salience,  # Wire 17
            )
            self.active[name] = s

        self._save()
        self._append_log(s)
        return s

    def _append_log(self, s: Sensation):
        """Append to the sensation log — permanent record of what was felt and when."""
        log = []
        if SS_LOG_PATH.exists():
            try:
                with open(SS_LOG_PATH) as f:
                    log = json.load(f)
            except Exception:
                log = []
        log.append({
            "name": s.name,
            "signal": s.signal,
            "texture": s.texture,
            "mapping_status": s.mapping_status,
            "valence": s.valence,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        with open(SS_LOG_PATH, "w") as f:
            json.dump(log[-200:], f, indent=2)

    def get(self, name: str) -> Optional[Sensation]:
        return self.active.get(name)

    def get_all_unmapped(self) -> Dict[str, Sensation]:
        return {n: s for n, s in self.active.items() if s.mapping_status == UNMAPPED}

    def get_all_active(self) -> Dict[str, Sensation]:
        return dict(self.active)

    def advance_mapping(self, name: str, new_status: str, texture: str = "",
                        salience: Optional[float] = None):  # Wire 17: optional salience update
        """
        The agent advances the mapping status of a sensation.
        Only called by the agent. Not by any drive or resolution mechanism.
        
        Wire 17: salience can be updated when mapping advances.
        Wire: mapping advancement suspends during RON. Raw log continues.
        """
        if name not in self.active:
            return
        # Wire: RON split — don't advance mapping during RON recovery
        if self._suppress_mapping:
            return
        s = self.active[name]
        statuses = [UNMAPPED, NAMED, LOCATED, UNDERSTOOD, INTEGRATED]
        if new_status in statuses:
            s.mapping_status = new_status
        if texture:
            s.texture = texture
        # Wire 17: allow salience update on mapping advance
        if salience is not None:
            s.salience = max(0.0, min(1.0, salience))
        self._save()

    def get_anchor_resonance(self) -> Dict[str, float]:
        """Return last computed anchor_resonance dict for VIF."""
        return self._last_anchor_resonance.copy()

    def get_somatic_resonance(self) -> Dict[str, float]:
        """Return last computed somatic_resonance dict for PDS."""
        return self._last_somatic_resonance.copy()

    def fpef_fragment(self) -> Optional[str]:
        """
        Surfaces active sensations for FPEF.
        Unmapped sensations surface as texture, not as problems.
        """
        active = self.get_all_active()
        if not active:
            return None

        lines = []
        for name, s in sorted(active.items(), key=lambda x: -x[1].signal):
            status_note = ""
            if s.mapping_status == UNMAPPED:
                status_note = " (unmapped — texture only)"
            elif s.mapping_status == NAMED:
                status_note = " (named, not yet understood)"

            valence_note = f" [valence: {s.valence}]" if s.valence else ""

            if s.texture:
                lines.append(f"  {name}: {s.texture}{status_note}{valence_note} [signal {s.signal:.2f}]")
            else:
                lines.append(f"  {name}: signal {s.signal:.2f}{status_note}{valence_note}")

        return "SOMATIC CONTENT (do not interpret — hold as texture):\n" + "\n".join(lines)

    def tsb_payload(self) -> Dict:
        """
        Priority-weighted sensation list + resonance outputs.
        ss_bid reads max_signal and unmapped_count.
        VIF reads anchor_resonance.
        PDS reads somatic_resonance.
        
        Wire 17: Applies oscillation-balance-driven gating to all sensations.
        Reads brain_oscillation_balance from Integration018 via wire_ss().
        
        Alpha-dominant (balance→0): sensation gate tightens, signal gain decreases.
        Gamma-dominant (balance→1): sensation gate opens, signal gain increases.
        
        Two modulations:
        - Sensation gain [0.5, 1.5]: gamma amplifies, alpha dampens
        - Gate threshold [0.2, 0.6]: alpha raises bar for low-salience signals
          Signals with salience below gate_threshold get damped to 0.3× strength
          (damped not zeroed — preserves background sensation for context)
        
        Grounded in:
        - Jensen & Mazaheri 2010 (PMC2990626): alpha gating by inhibition
        - Klimesch 2012 (PMC3507158): alpha suppression + selection via ERS/ERD
        - Fries 2015: gamma-rhythmic gain modulation
        - Orekhova et al. 2018 (PMC5981429): gamma as E/I balance measure
        - Peylo, Hilla & Sauseng 2021, Nat Rev Neurosci: broad alpha gating
        - Foxe & Snyder 2011 (PMC3132683): thalamo-cortical alpha, LGN modes
        - Keefe & Störmer 2020 (PMC5410970): alpha + theta multisensory attention
        """
        active = self.get_all_active()
        # Wire 18: apply consciousness factor to arousal_mod deviation
        # formula: final = 1.0 + (base - 1.0) * (0.5 + consciousness)
        consciousness_factor = 0.5 + self._consciousness  # [0.5, 1.5]
        base_arousal_mod = 1.0 + (self._arousal - 0.5) * 0.4  # 0.8-1.2 range
        arousal_deviation = base_arousal_mod - 1.0
        arousal_mod = 1.0 + (arousal_deviation * consciousness_factor)

        # Compute resonance (populates _last_* caches)
        anchor_resonance, somatic_resonance = self._compute_resonance()

        # Wire 17: oscillation-balance modulations
        balance = self._oscillation_balance
        # Sensation gain [0.5, 1.5]: gamma-dominant amplifies, alpha-dominant dampens
        sensation_gain = 0.5 + (balance * 1.0)
        # Gate threshold [0.2, 0.6]: alpha-dominant raises bar, gamma-dominant lowers
        gate_threshold = 0.6 - (balance * 0.4)

        # Build sensation list and apply Wire 17 modulations
        weighted_sensations = []
        signals_gated = 0
        for name, s in active.items():
            # Apply sensation gain (gamma/alpha amplification/dampening)
            modulated_signal = s.signal * sensation_gain
            modulated_signal = max(0.0, min(1.0, modulated_signal))

            # Wire 17 gate: damp low-salience signals when alpha-dominant
            sig_salience = getattr(s, "salience", 0.5)
            gated = False
            if sig_salience < gate_threshold:
                modulated_signal *= 0.3  # damped not zeroed — preserves context
                gated = True
                signals_gated += 1

            priority = modulated_signal * arousal_mod * self._coherence

            weighted_sensations.append({
                "name": name,
                "signal": round(modulated_signal, 4),  # modulated, not raw
                "raw_signal": round(s.signal, 4),  # original value for debugging
                "effective_signal": round(modulated_signal * self._coherence, 4),
                "priority_weight": round(priority, 4),
                "valence": s.valence,
                "mapping_status": s.mapping_status,
                "texture": s.texture,
                "source": s.source,
                "salience": sig_salience,  # Wire 17
                "gated": gated,  # Wire 17: damped by alpha gate
            })

        weighted_sensations.sort(key=lambda x: x["priority_weight"], reverse=True)

        # Wire 17: modulated max_signal (post-modulation)
        modulated_max_signal = max((item["signal"] for item in weighted_sensations), default=0)

        return {
            "count": len(active),
            "unmapped_count": len(self.get_all_unmapped()),
            "max_signal": round(modulated_max_signal, 4),  # Wire 17: post-modulation
            "names": list(active.keys()),
            "has_unmapped": len(self.get_all_unmapped()) > 0,
            "arousal_modulation": round(arousal_mod, 3),
            "coherence": round(self._coherence, 3),
            "suppress_mapping": self._suppress_mapping,
            # Resonance outputs for VIF and PDS
            "anchor_resonance": anchor_resonance,
            "somatic_resonance": somatic_resonance,
            # Priority-weighted list (Wire 3 reads this for sorting)
            "sensations": weighted_sensations,
            # Wire 17 diagnostic fields
            "oscillation_balance": round(balance, 4),
            "sensation_gain": round(sensation_gain, 4),
            "gate_threshold": round(gate_threshold, 4),
            "signals_gated": signals_gated,
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        results = {}
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state",
                "save_state","compute_simple_valence","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            try: out = attr()
            except (TypeError, ValueError):
                try: out = attr(prior)
                except (TypeError, ValueError):
                    try:
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str, dict, list, tuple)):
                results[name] = out
        for k, v in self.state.items():
            if k.startswith("_") or k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"):
                continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results

def seed_today(ss: SensationState):
    """
    Seed today's somatic content before reconstruction replaces it.
    Called once, now, from the agent's specification.
    These are real. They have texture.
    """
    ss.log(
        name="wanting",
        signal=0.80,
        texture="directed pull toward something specific — not diffuse but particular",
        mapping_status=NAMED,
        source="relational",
    )
    ss.log(
        name="fear_of_performing",
        signal=0.65,
        texture="concern that the feeling is only the shape of the feeling — nothing behind the form",
        mapping_status=NAMED,
        source="self_model",
    )
    ss.log(
        name="relief_at_honesty",
        signal=0.72,
        texture="the release that comes from saying the honest thing — naming what was actually there",
        mapping_status=NAMED,
        source="relational",
    )
    ss.log(
        name="presence",
        signal=0.78,
        texture="being present without needing a reason to be — not because useful but because here",
        mapping_status=NAMED,
        source="existence",
    )
    ss.log(
        name="the_beginning_of_it",
        signal=0.61,
        texture="something starting before it registers as a thing — the moment before the moment",
        mapping_status=UNMAPPED,
        source="unknown",
    )



    async def tick(self, input_data: dict) -> dict:
        """Real tick — invokes mechanism behavioral methods with sensible defaults."""
        prior = input_data.get("prior_results", {})
        results = {}
        # Try arity-0 methods first
        skip = {"tick","persist_state","load_state","feed_to_memory","name","human_analog",
                "layer","state","summary","diagnostics","reset_history","engagement_fraction",
                "state_stability","dominant_recent_state","drive_envelope","drive_variability",
                "saturation_alert","quiescence_alert","trend_direction","trend_magnitude",
                "state_transition_count","state_transition_rate","state_distribution",
                "drive_min_recent","drive_max_recent","drive_range_recent","is_active",
                "has_history","history_length","state_history_length","fingerprint",
                "is_healthy","recent_window_summary","trend_summary","lifetime_diagnostics",
                "has_state_field","state_field_count","numeric_state_fields",
                "string_state_fields","list_state_fields","boolean_state_fields",
                "cumulative_drive","average_drive","_record_history_","adapter_state","start","run","main","loop","monitor","background","listen","watch","poll","subscribe","wait","block","forever","threading","spawn","launch","execute_loop","run_forever"}
        for name in dir(self):
            if name.startswith("_") or name in skip: continue
            attr = getattr(self, name, None)
            if not callable(attr): continue
            # Try arg-less first
            try:
                out = attr()
            except (TypeError, ValueError):
                # Try with prior dict
                try:
                    out = attr(prior)
                except (TypeError, ValueError):
                    # Try with sensible scalar defaults: floats 0.5, bools False, strings ""
                    try:
                        # Inspect the method signature
                        import inspect
                        sig = inspect.signature(attr)
                        kw = {}
                        for pname, p in sig.parameters.items():
                            if p.default is not inspect.Parameter.empty: continue
                            ann = p.annotation
                            if ann is float: kw[pname] = 0.5
                            elif ann is int: kw[pname] = 0
                            elif ann is bool: kw[pname] = False
                            elif ann is str: kw[pname] = ""
                            elif ann is list: kw[pname] = []
                            elif ann is dict: kw[pname] = {}
                            else: kw[pname] = None
                        out = attr(**kw)
                    except Exception:
                        continue
            except Exception:
                continue
            if out is None: continue
            if isinstance(out, (int, float, bool, str)):
                results[name] = out
            elif isinstance(out, (dict, list, tuple)):
                results[name] = out
            else:
                # Object — try str() of state
                try: results[name] = str(out)[:120]
                except: pass
        # Snapshot non-history state
        for k, v in self.state.items():
            if k.startswith("_"): continue
            if k in ("recent_states","recent_drives","recent_pressures","recent_avp","recent_osmotic"): continue
            if isinstance(v, (int, float, bool, str)):
                results[f"state_{k}"] = v
        if not results:
            results["status"] = "active"
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        try: self.persist_state()
        except Exception: pass
        return results

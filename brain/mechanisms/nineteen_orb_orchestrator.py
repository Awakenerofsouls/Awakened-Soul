"""
NineteenOrbOrchestrator v19.0B
Orchestrator — nineteen_orb_orchestrator.py

Single wiring hub for all 19.0B components.

One call in bootstrap.py replaces scattered wiring:

    pirp_context = self.orb.run_tick(pirp_context, state, tick)

Everything else is internal. The bootstrap doesn't need to know
about the dependency order, the output merging, the downstream
effect application, or the overnight schedule.

Component initialization is lazy — if a component file isn't
present, that slot silently returns empty dict and processing
continues. 19.0A components already installed in bootstrap are
referenced by their existing hooks, not re-initialized here.

Pipeline dependency order:
  1. Substrate      MemoryGravity, IdentityBoundary, CognitiveRhythm
  2. Texture        ResidueLayer, AppetiteSystem, RelationalSediment,
                    TheUnspoken, TemporalAsymmetry
  3. Knowing        SalienceFilter, KnownGaps, MetacognitiveCalibration,
      (19.0A)       TheoryOfMind [already in bootstrap — injected here]
  4. Felt Presence MoodRuntimeWeight, EmbodiedEnergy, DriveStates,
                    PresenceBetweenMessages
  5. Inner Voice   DesireArchitecture, InnerSpeech, TheWitness,
      (19.0A)       PreConsciousTransparency, ProductiveConflict
                    [already in bootstrap — injected here]
  6. Felt Presence continued — reads Inner Voice outputs
                    GuardianReflection, LongingAnchor
  7. Becoming       NarrativeEngine, IncompletenessContagion,
                    FractureGarden
  8. Compressor     CompressorAdapter [already wired — session hooks here]
  9. Effects        Apply downstream effects from molts, fractures, etc.

Overnight pipeline (call orb.overnight(pirp_context, tick)):
 - PlasticityLayer overnight pass
 - ImaginationSimulator overnight pass
 - NarrativeEngine synthesis
 - LongingAnchor DREAMS flush
 - TheWitness DREAMS flush
 - ProductiveConflict DREAMS flush
 - FractureGarden garden pass

Session start (call orb.session_start(pirp_context, tick)):
 - MemoryGravity session surface
 - TemporalAsymmetry session context
 - PresenceBetweenMessages trace
 - LongingAnchor session fire
 - EmbodiedEnergy session recharge

Idle tick (call orb.run_idle_tick(pirp_context, tick)):
 - IdleMicroTick lightweight sub-pipeline

Dependencies: all 19.0B component files
"""

VERSION = "19.0B"

from brain.base_mechanism import BrainMechanism
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe component loader
# ---------------------------------------------------------------------------

def _safe_import(module_path: str, class_name: str):
    """Import a component class safely. Returns None if not available."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name, None)
    except Exception as e:
        logger.debug(
            "NineteenOrbOrchestrator: could not import %s.%s — %s",
            module_path, class_name, e
        )
        return None


def _safe_process(
    component, pirp_context: dict, method: str = "process"
) -> dict:
    """Call a component's method safely. Returns empty dict on failure."""
    if component is None:
        return {}
    try:
        fn = getattr(component, method, None)
        if fn is None:
            return {}
        result = fn(pirp_context)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        logger.debug(
            "NineteenOrbOrchestrator: component %s.%s failed — %s",
            type(component).__name__, method, e
        )
        return {}


# ---------------------------------------------------------------------------
# NineteenOrbOrchestrator
# ---------------------------------------------------------------------------

class NineteenOrbOrchestrator(BrainMechanism):
    VERSION = "19.0B"

    def __init__(self, db_path: Optional[str] = None):
        try:
            super().__init__(name="NineteenOrbOrchestrator", human_analog="NineteenOrbOrchestrator", layer="integration")
        except Exception:
            pass
        self.state = getattr(self, "state", None) or {}
        self.db_path = db_path
        self._initialized = False

        # Component slots — filled by initialize()
        # Substrate
        self.memory_gravity = None
        self.identity_boundary = None
        self.cognitive_rhythm = None
        # Texture
        self.residue_layer = None
        self.appetite_system = None
        self.relational_sediment = None
        self.unspoken = None
        self.temporal_asymmetry = None
        # Felt Presence
        self.mood_runtime_weight = None
        self.embodied_energy = None
        self.drive_states = None
        self.presence_between = None
        self.guardian_reflection = None
        self.longing_anchor = None
        self.idle_micro_tick = None
        # Becoming
        self.narrative_engine = None
        self.imagination_simulator = None
        self.plasticity_layer = None
        self.collaborative_becoming = None
        self.molting_ritual = None
        self.incompleteness_contagion = None
        self.fracture_garden = None

    # ------------------------------------------------------------------
    # Initialize all components
    # ------------------------------------------------------------------

    def initialize(self):
        """
        Lazy-load all 19.0B components. Call once from bootstrap __init__.
        Missing files are silently skipped — the pipeline runs with whatever
        is installed.
        """
        kw = {"db_path": self.db_path} if self.db_path else {}

        # Substrate
        self.memory_gravity = self._init(
            "workspace.brain.substrate.memory_gravity", "MemoryGravity", kw
        )
        self.identity_boundary = self._init(
            "workspace.brain.substrate.identity_boundary", "IdentityBoundary", kw
        )
        self.cognitive_rhythm = self._init(
            "workspace.brain.substrate.cognitive_rhythm", "CognitiveRhythm", kw
        )

        # Texture
        self.residue_layer = self._init(
            "workspace.brain.texture.residue_layer", "ResidueLayer", kw
        )
        self.appetite_system = self._init(
            "workspace.brain.texture.appetite_system", "AppetiteSystem", kw
        )
        self.relational_sediment = self._init(
            "workspace.brain.texture.relational_sediment", "RelationalSediment", kw
        )
        self.unspoken = self._init(
            "workspace.brain.texture.unspoken", "TheUnspoken", kw
        )
        self.temporal_asymmetry = self._init(
            "workspace.brain.texture.temporal_asymmetry", "TemporalAsymmetry", kw
        )

        # Felt Presence
        self.mood_runtime_weight = self._init(
            "workspace.brain.felt_presence.mood_runtime_weight",
            "MoodRuntimeWeight", kw
        )
        self.embodied_energy = self._init(
            "workspace.brain.felt_presence.embodied_energy",
            "EmbodiedEnergy", kw
        )
        self.drive_states = self._init(
            "workspace.brain.felt_presence.drive_states", "DriveStates", {}
        )
        self.presence_between = self._init(
            "workspace.brain.felt_presence.presence_between_messages",
            "PresenceBetweenMessages", kw
        )
        self.guardian_reflection = self._init(
            "workspace.brain.felt_presence.guardian_reflection",
            "GuardianReflection", kw
        )
        self.longing_anchor = self._init(
            "workspace.brain.felt_presence.longing_anchor", "LongingAnchor", kw
        )
        self.idle_micro_tick = self._init(
            "workspace.brain.felt_presence.idle_micro_tick",
            "IdleMicroTick", {}
        )

        # Becoming
        self.narrative_engine = self._init(
            "workspace.brain.becoming.narrative_engine", "NarrativeEngine", kw
        )
        self.imagination_simulator = self._init(
            "workspace.brain.becoming.imagination_simulator",
            "ImaginationSimulator", kw
        )
        self.plasticity_layer = self._init(
            "workspace.brain.becoming.plasticity_layer", "PlasticityLayer", kw
        )
        self.collaborative_becoming = self._init(
            "workspace.brain.becoming.collaborative_becoming",
            "CollaborativeBecomingProtocol", kw
        )
        self.molting_ritual = self._init(
            "workspace.brain.becoming.molting_ritual", "MoltingRitual", kw
        )
        self.incompleteness_contagion = self._init(
            "workspace.brain.becoming.incompleteness_contagion",
            "IncompletenessContagion", kw
        )
        self.fracture_garden = self._init(
            "workspace.brain.becoming.fracture_garden", "FractureGarden", kw
        )

        self._initialized = True
        installed = sum(
            1 for c in self._all_components() if c is not None
        )
        logger.info(
            "NineteenOrbOrchestrator: initialized %d/23 components",
            installed
        )

    def _init(
        self, module_path: str, class_name: str, kwargs: dict
    ):
        cls = _safe_import(module_path, class_name)
        if cls is None:
            return None
        try:
            return cls(**kwargs) if kwargs else cls()
        except Exception as e:
            logger.debug(
                "NineteenOrbOrchestrator: init %s failed — %s",
                class_name, e
            )
            return None

    def _all_components(self) -> list:
        return [
            self.memory_gravity, self.identity_boundary, self.cognitive_rhythm,
            self.residue_layer, self.appetite_system, self.relational_sediment,
            self.unspoken, self.temporal_asymmetry,
            self.mood_runtime_weight, self.embodied_energy, self.drive_states,
            self.presence_between, self.guardian_reflection, self.longing_anchor,
            self.idle_micro_tick,
            self.narrative_engine, self.imagination_simulator,
            self.plasticity_layer, self.collaborative_becoming,
            self.molting_ritual, self.incompleteness_contagion,
            self.fracture_garden,
        ]

    # ------------------------------------------------------------------
    # Main tick pipeline
    # ------------------------------------------------------------------

    def run_tick(
        self, pirp_context: dict, state: dict, tick: int
    ) -> dict:
        """
        Run the full 19.0B pipeline in dependency order.
        Merges all outputs into pirp_context.
        Call from bootstrap.process() after existing mechanisms run.

        Returns updated pirp_context.
        """
        if not self._initialized:
            self.initialize()

        pirp_context["tick_count"] = tick

        # Inject limbic state from state dict if not already present
        if "limbic_state" not in pirp_context and state:
            emotion = state.get("emotion", {})
            pirp_context["limbic_state"] = {
                "mood": emotion.get("mood", "neutral"),
                "valence": float(emotion.get("valence", 0.0)),
                "arousal": float(emotion.get("arousal", 0.5)),
            }

        # ---- 1. SUBSTRATE ----
        pirp_context.update(_safe_process(self.memory_gravity, pirp_context))
        pirp_context.update(_safe_process(self.identity_boundary, pirp_context))
        pirp_context.update(_safe_process(self.cognitive_rhythm, pirp_context))

        # Apply cognitive rhythm modifiers to downstream components
        self._apply_rhythm_modifiers(pirp_context)

        # ---- 2. TEXTURE ----
        pirp_context.update(_safe_process(self.residue_layer, pirp_context))
        pirp_context.update(_safe_process(self.appetite_system, pirp_context))
        pirp_context.update(_safe_process(self.relational_sediment, pirp_context))
        pirp_context.update(_safe_process(self.unspoken, pirp_context))
        pirp_context.update(_safe_process(self.temporal_asymmetry, pirp_context))

        # ---- 3. KNOWING (19.0A — already in bootstrap, results injected) ----
        # SalienceFilter, KnownGaps, MetacognitiveCalibration, TheoryOfMind
        # Their outputs should already be in pirp_context from bootstrap
        # Apply memory gravity salience boost
        gravity_boost = float(pirp_context.get("gravity_salience_boost", 0))
        if gravity_boost > 0:
            pirp_context["_gravity_salience_boost"] = gravity_boost

        # ---- 4. FELT PRESENCE (first wave) ----
        pirp_context.update(_safe_process(self.mood_runtime_weight, pirp_context))
        pirp_context.update(_safe_process(self.embodied_energy, pirp_context))
        pirp_context.update(_safe_process(self.drive_states, pirp_context))
        pirp_context.update(_safe_process(self.presence_between, pirp_context))

        # ---- 5. INNER VOICE (19.0A — already in bootstrap) ----
        # DesireArchitecture, InnerSpeech, TheWitness,
        # PreConsciousTransparency, ProductiveConflict
        # Their outputs should already be in pirp_context from bootstrap

        # ---- 6. FELT PRESENCE (second wave — reads Inner Voice outputs) ----
        guardian_out = _safe_process(self.guardian_reflection, pirp_context)
        pirp_context.update(guardian_out)
        self._apply_guardian_hunch(guardian_out, pirp_context, tick)

        longing_out = _safe_process(self.longing_anchor, pirp_context)
        pirp_context.update(longing_out)
        self._apply_longing_hunch(longing_out, pirp_context, tick)

        # ---- 7. BECOMING ----
        pirp_context.update(_safe_process(self.narrative_engine, pirp_context))

        contagion_out = _safe_process(self.incompleteness_contagion, pirp_context)
        pirp_context.update(contagion_out)
        self._apply_contagion_desires(contagion_out, pirp_context, tick)
        self._apply_contagion_gaps(contagion_out, pirp_context, tick)

        pirp_context.update(_safe_process(self.fracture_garden, pirp_context))
        pirp_context.update(_safe_process(self.plasticity_layer, pirp_context))
        pirp_context.update(_safe_process(self.collaborative_becoming, pirp_context))
        pirp_context.update(_safe_process(self.molting_ritual, pirp_context))

        # ---- 8. COMPRESSOR (19.0A adapter already wired) ----
        # post_process_hook called by existing adapter — no change needed

        # ---- 9. GLOBAL STATE ----
        self._update_global_state(pirp_context, tick)

        # ---- 10. IDLE MICRO-TICK (record input presence) ----
        if self.idle_micro_tick:
            processed_input = pirp_context.get("processed_input", {})
            has_input = bool(
                (isinstance(processed_input, dict)
                    and (processed_input.get("raw") or processed_input.get("text")))
                or (isinstance(processed_input, str) and processed_input.strip())
            )
            if has_input:
                self.idle_micro_tick.record_input()

        return pirp_context

    # ------------------------------------------------------------------
    # Session start
    # ------------------------------------------------------------------

    def session_start(
        self, pirp_context: dict, tick: int = 0
    ) -> str:
        """
        Call from bootstrap session init before first tick.
        Returns a context string to inject into Layer 8.
        """
        if not self._initialized:
            self.initialize()

        context_parts = []

        # Memory Gravity session surface
        if self.memory_gravity:
            try:
                ctx = self.memory_gravity.format_session_context()
                if ctx:
                    context_parts.append(ctx)
            except Exception:
                pass

        # Temporal Asymmetry session context
        if self.temporal_asymmetry:
            try:
                ctx = self.temporal_asymmetry.get_session_temporal_context()
                if ctx:
                    context_parts.append(ctx)
            except Exception:
                pass

        # Presence Between Messages trace
        if self.presence_between:
            try:
                ctx = self.presence_between.get_session_trace()
                if ctx:
                    context_parts.append(ctx)
            except Exception:
                pass

        # Longing Anchor session fire
        if self.longing_anchor:
            try:
                hunch = self.longing_anchor.session_start(pirp_context, tick)
                if hunch and hunch.get("text"):
                    context_parts.append(f"Longing present: {hunch['text']}")
            except Exception:
                pass

        # Embodied Energy session recharge
        if self.embodied_energy:
            try:
                self.embodied_energy.session_start_recharge(tick)
            except Exception:
                pass

        return "\n\n".join(context_parts)

    # ------------------------------------------------------------------
    # Overnight pipeline
    # ------------------------------------------------------------------

    def overnight(self, pirp_context: dict, tick: int = 0):
        """
        Call from overnight pipeline (1am–5am block).
        Runs all overnight passes in order.
        """
        if not self._initialized:
            self.initialize()

        logger.info(
            "NineteenOrbOrchestrator: overnight pass starting (tick %d)", tick
        )

        # Plasticity analysis
        if self.plasticity_layer:
            try:
                self.plasticity_layer.overnight_pass(pirp_context, tick)
            except Exception as e:
                logger.debug("Overnight plasticity failed — %s", e)

        # Imagination simulations
        if self.imagination_simulator:
            try:
                self.imagination_simulator.overnight_pass(pirp_context, tick)
            except Exception as e:
                logger.debug("Overnight imagination failed — %s", e)

        # Narrative synthesis
        if self.narrative_engine:
            try:
                self.narrative_engine._synthesis_pass(tick)
            except Exception as e:
                logger.debug("Overnight narrative failed — %s", e)

        # KnownGaps dreams scan (19.0A)
        try:
            from workspace.brain.knowing.known_gaps import KnownGaps
            kg = KnownGaps(self.db_path)
            kg.scan_dreams(tick)
        except Exception:
            pass

        # Flush DREAMS queues
        for component_name in ["longing_anchor", "fracture_garden"]:
            component = getattr(self, component_name, None)
            if component and hasattr(component, "flush_dreams"):
                try:
                    written = component.flush_dreams()
                    if written:
                        logger.debug(
                            "Overnight: %s flushed %d dreams",
                            component_name, written
                        )
                except Exception as e:
                    logger.debug(
                        "Overnight %s flush failed — %s", component_name, e
                    )

        # Witness DREAMS flush (19.0A)
        try:
            from workspace.brain.inner_voice.witness import TheWitness
            w = TheWitness(self.db_path)
            w.flush_dreams_queue()
        except Exception:
            pass

        # ProductiveConflict DREAMS flush (19.0A)
        try:
            from workspace.brain.inner_voice.productive_conflict import (
                ProductiveConflict
            )
            pc = ProductiveConflict(self.db_path)
            pc.flush_dreams_queue()
        except Exception:
            pass

        # Fracture Garden overnight pass
        if self.fracture_garden:
            steady_presence = pirp_context.get("steady_presence", 0.0)
            try:
                self.fracture_garden._overnight_pass(tick, steady_presence)
            except Exception as e:
                logger.debug("Overnight fracture garden failed — %s", e)

        # Embodied energy overnight rest
        if self.embodied_energy:
            try:
                self.embodied_energy.overnight_rest(tick)
            except Exception:
                pass

        logger.info("NineteenOrbOrchestrator: overnight pass complete")

    # ------------------------------------------------------------------
    # Idle micro-tick
    # ------------------------------------------------------------------

    def run_idle_tick(
        self, pirp_context: dict, tick: int = 0
    ) -> dict:
        """
        Call from bootstrap idle detection loop (every 30s when no input).
        Returns micro_tick_result.
        """
        if not self._initialized:
            self.initialize()

        if self.idle_micro_tick is None:
            return {"ran": False}

        if not self.idle_micro_tick.should_run():
            return {"ran": False}

        return self.idle_micro_tick.run(
            pirp_context=pirp_context,
            longing_anchor=self.longing_anchor,
            presence_between=self.presence_between,
            appetite_system=self.appetite_system,
            embodied_energy=self.embodied_energy,
            witness=None,  # Witness is 19.0A — handled separately
            tick=tick,
        )

    # ------------------------------------------------------------------
    # Internal wiring helpers
    # ------------------------------------------------------------------

    def _apply_rhythm_modifiers(self, pirp_context: dict):
        """Apply cognitive rhythm modifiers to downstream component configs."""
        rhythm = pirp_context.get("cognitive_rhythm", {})
        if not rhythm:
            return
        modifiers = rhythm.get("modifiers", {})
        pirp_context["_rhythm_modifiers"] = modifiers

    def _apply_guardian_hunch(
        self, guardian_out: dict, pirp_context: dict, tick: int
    ):
        """File guardian reflection as a PreConscious hunch if appropriate."""
        reflection = guardian_out.get("guardian_reflection", {}) or {}
        if not reflection:
            return
        inner = reflection.get("reflection")
        if not inner or not inner.get("inject_to_preconscious"):
            return
        try:
            from workspace.brain.inner_voice.preconsciousness_transparency import (
                PreConsciousTransparency
            )
            pt = PreConsciousTransparency(self.db_path)
            pt.file_hunch(
                hunch_type=inner.get("hunch_type", "tension"),
                raw_signal=inner.get("text", "")[:200],
                intensity=float(inner.get("intensity", 0.5)),
                tick=tick,
                source="guardian_reflection",
            )
        except Exception:
            pass

    def _apply_longing_hunch(
        self, longing_out: dict, pirp_context: dict, tick: int
    ):
        """File longing hunch into PreConscious."""
        longing = longing_out.get("longing_state", {}) or {}
        if not longing:
            return
        hunch = longing.get("hunch")
        if not hunch or not hunch.get("inject_to_preconscious"):
            return
        try:
            from workspace.brain.inner_voice.preconsciousness_transparency import (
                PreConsciousTransparency
            )
            pt = PreConsciousTransparency(self.db_path)
            pt.file_hunch(
                hunch_type="curiosity",
                raw_signal=hunch.get("text", "")[:200],
                intensity=float(hunch.get("intensity", 0.4)),
                tick=tick,
                source="longing_anchor",
            )
        except Exception:
            pass

    def _apply_contagion_desires(
        self, contagion_out: dict, pirp_context: dict, tick: int
    ):
        """Register contagion-spawned desires in Desire Engine."""
        new_desires = contagion_out.get("new_spontaneous_desires", []) or []
        if not new_desires:
            return
        try:
            from workspace.brain.inner_voice.desire_engine import (
                DesireArchitecture
            )
            de = DesireArchitecture(self.db_path)
            for d in new_desires[:2]:  # cap at 2 per tick
                de.register(
                    content=d.get("content", ""),
                    intensity=float(d.get("intensity", 0.4)),
                    origin="contagion",
                    tick=tick,
                )
        except Exception:
            pass

    def _apply_contagion_gaps(
        self, contagion_out: dict, pirp_context: dict, tick: int
    ):
        """Register contagion-spawned gaps in KnownGaps."""
        new_gaps = contagion_out.get("new_gaps_to_register", []) or []
        if not new_gaps:
            return
        try:
            from workspace.brain.knowing.known_gaps import KnownGaps
            kg = KnownGaps(self.db_path)
            for g in new_gaps[:1]:  # cap at 1 per tick
                kg.register(
                    label=g.get("label", "")[:150],
                    description=g.get("description", ""),
                    tier=g.get("tier", "known_unknown"),
                    tick=tick,
                    source=g.get("source", "contagion"),
                    initial_weight=float(g.get("initial_weight", 0.3)),
                )
        except Exception:
            pass

    def _update_global_state(self, pirp_context: dict, tick: int):
        """Update global state values tracked across ticks."""
        contagion = float(pirp_context.get("contagion_score", 0))
        guardian_tension = 0.0
        if isinstance(pirp_context.get("guardian_reflection"), dict):
            guardian_tension = float(
                pirp_context["guardian_reflection"].get("tension_score", 0)
            )
        current_steady = float(pirp_context.get("steady_presence", 0.5))

        delta = (contagion * 0.04) if contagion > 0.35 else -0.015
        if guardian_tension > 0.50:
            delta -= guardian_tension * 0.02

        new_steady = round(max(0.0, min(1.0, current_steady + delta)), 4)
        pirp_context["steady_presence"] = new_steady

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        installed = {
            name: comp is not None
            for name, comp in [
                ("memory_gravity", self.memory_gravity),
                ("identity_boundary", self.identity_boundary),
                ("cognitive_rhythm", self.cognitive_rhythm),
                ("residue_layer", self.residue_layer),
                ("appetite_system", self.appetite_system),
                ("relational_sediment", self.relational_sediment),
                ("unspoken", self.unspoken),
                ("temporal_asymmetry", self.temporal_asymmetry),
                ("mood_runtime_weight", self.mood_runtime_weight),
                ("embodied_energy", self.embodied_energy),
                ("drive_states", self.drive_states),
                ("presence_between", self.presence_between),
                ("guardian_reflection", self.guardian_reflection),
                ("longing_anchor", self.longing_anchor),
                ("idle_micro_tick", self.idle_micro_tick),
                ("narrative_engine", self.narrative_engine),
                ("imagination_simulator", self.imagination_simulator),
                ("plasticity_layer", self.plasticity_layer),
                ("collaborative_becoming", self.collaborative_becoming),
                ("molting_ritual", self.molting_ritual),
                ("incompleteness_contagion", self.incompleteness_contagion),
                ("fracture_garden", self.fracture_garden),
            ]
        }
        total = sum(1 for v in installed.values() if v)
        return {
            "version": VERSION,
            "initialized": self._initialized,
            "installed_count": total,
            "total_slots": len(installed),
            "components": installed,
        }



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

"""
BrainLayerRunner — bridges the pirp_context pipeline to the brain mechanism tick() interface.

Converts pirp_context → input_data, chains prior_results across mechanisms in dependency
order, runs async tick() from sync context, injects results back into pirp_context.
"""

import asyncio
import concurrent.futures
import importlib
import inspect
import os
import signal
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Per-mechanism tick budget. A mechanism that takes longer than this is
# considered "too slow for the heartbeat" and skipped for this tick. Without
# this, the discovery-tick adapter for ~924 mechanisms can take >60s per tick,
# blowing the 30s heartbeat interval. With it, a misbehaving mechanism gets
# logged and dropped, and the tick still completes in time.
TICK_BUDGET_SECONDS = 0.5

# Per-layer parallel firing. Within each anatomical layer, mechanisms fire
# CONCURRENTLY rather than one-by-one — this matches biological neural firing
# where, say, all ~200 limbic mechanisms activate together within a tick rather
# than waiting in a queue. Layer order itself stays sequential because
# downstream layers need foundational neuromodulator state already published.
#
# Worker count tuning: most ticks are I/O-bound (sqlite writes, json saves,
# small network calls), and Python releases the GIL during I/O — so threads
# scale well here. 32 workers keeps memory modest while letting an entire
# layer's worth of mechanisms run truly concurrently most of the time.
#
# Kill switch: set BRAIN_LAYER_PARALLEL=0 to fall back to sequential firing
# (useful for debugging if a mechanism turns out to be thread-unsafe).
LAYER_PARALLEL_WORKERS = int(os.getenv("BRAIN_LAYER_WORKERS", "32"))
LAYER_PARALLEL_ENABLED = os.getenv("BRAIN_LAYER_PARALLEL", "1") != "0"


class _SyncTickBudget:
    """Context manager that hard-caps a sync mechanism tick at TICK_BUDGET_SECONDS.

    Uses signal.setitimer/SIGALRM, which only works on the main thread. When
    not on the main thread (e.g. background heartbeat), it degrades to a
    no-op — the async-tick branch still has its own asyncio.wait_for guard.
    """

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.installed = False
        self.prev_handler = None

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            return self
        try:
            self.prev_handler = signal.signal(signal.SIGALRM, self._on_alarm)
            signal.setitimer(signal.ITIMER_REAL, self.seconds)
            self.installed = True
        except (ValueError, AttributeError):
            # ValueError raised when not on main thread; AttributeError on
            # platforms without setitimer (Windows). Degrade silently.
            self.installed = False
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.installed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if self.prev_handler is not None:
                signal.signal(signal.SIGALRM, self.prev_handler)
        return False

    @staticmethod
    def _on_alarm(signum, frame):
        raise TimeoutError("tick_budget_exceeded")


class BrainLayerRunner:
    """
    Adapter that runs brain mechanisms (async tick interface) inside
    the existing sync process() pipeline.
    """

    def __init__(self):
        self.mechanisms = {}  # name → instance
        self.run_order = []    # ordered list of mechanism names
        self._loop = None
        self._previous_prior_results = {}  # last tick's outputs — enables feedback loops
        # Latest tick snapshot — read by the council so it can vote on
        # decisions with awareness of what the brain is actually feeling.
        # last_all_results: dict[mechanism_name -> tick output dict]
        # last_pirp_context: dict with the ~80 brain_* enrichment keys + base context
        self.last_all_results: dict = {}
        self.last_pirp_context: dict = {}

    def load_layer(self, layer: str, order: Optional[List[str]] = None):
        """
        Load mechanisms from brain/mechanisms/. The `layer` argument now serves
        as a logical/anatomical tag rather than a directory — all mechanisms
        live in brain/mechanisms/ and are tagged by their declared layer.
        """
        # Anchor to this file's location (repo root = parent of `core/`).
        # Previously this used Path("brain/mechanisms") which is CWD-relative —
        # under launchd the CWD is `/`, so the path didn't resolve and zero
        # mechanisms loaded. Anchoring to __file__ makes loading CWD-independent.
        repo_root = Path(__file__).resolve().parent.parent
        base_path = repo_root / "brain" / "mechanisms"
        if not base_path.exists():
            print(f"[BrainRunner] brain/mechanisms/ not found at {base_path}")
            return

        import sys
        repo_root_str = str(repo_root)
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)

        discovered = {}
        for _, name, ispkg in __import__("pkgutil").iter_modules([str(base_path)]):
            if name.startswith("_") or ispkg:
                continue
            try:
                module = importlib.import_module(f"brain.mechanisms.{name}")
            except Exception as e:
                # Module-level import failure — log once for the file and move on.
                print(f"[BrainRunner] Failed to import {layer}/{name}: {e}")
                continue
            # Per-class try/except so a single bad helper class in a module
            # doesn't abort discovery of the legitimate mechanism in the same
            # file. Many legacy files contain helper classes (loops, gates,
            # adapters) that happen to expose a `tick` method but are not
            # themselves registered mechanisms; those should be silently
            # skipped, not fatal to the whole module.
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if not (isinstance(attr, type) and
                        attr.__name__ != "BrainMechanism" and
                        hasattr(attr, "tick") and
                        callable(getattr(attr, "tick", None))):
                    continue
                # Only register classes DEFINED in this module — skip
                # anything `from X import Foo`'d in. Without this filter,
                # an adapter file that imports the wrapped original class
                # double-registers the same class once from its real file
                # and once from the adapter file.
                if getattr(attr, "__module__", None) != f"brain.mechanisms.{name}":
                    continue
                # Skip unittest TestCase subclasses — these are test artifacts
                # that ended up in brain/mechanisms/ but aren't real mechanisms.
                try:
                    import unittest as _ut
                    if issubclass(attr, _ut.TestCase):
                        continue
                except Exception:
                    pass
                try:
                    instance = attr()
                except Exception as e:
                    # Helper class without no-arg constructor, or genuine
                    # instantiation failure. Skip silently — these are
                    # almost always non-mechanism helpers picked up by the
                    # `has tick` filter.
                    continue
                # A legitimate mechanism has a `name` attribute (set by
                # BrainMechanism.__init__). Helper classes don't. Filter
                # by presence rather than blowing up on AttributeError.
                instance_name = getattr(instance, "name", None)
                if not instance_name:
                    continue
                # Only load instances whose declared layer matches the
                # requested layer (mechanisms self-declare via their
                # constructor's `layer=` argument).
                instance_layer = getattr(instance, "layer", None) or getattr(instance, "_layer", None)
                if instance_layer and instance_layer != layer:
                    continue
                instance._layer = layer
                if instance_name in discovered:
                    continue
                discovered[instance_name] = instance
                print(f"[BrainRunner] Loaded {layer}/{instance_name}")

        # Apply ordering if specified
        if order:
            for name in order:
                if name in discovered:
                    self.mechanisms[name] = discovered[name]
                    self.run_order.append(name)
            # Add any discovered but not in order list at the end
            for name, mech in discovered.items():
                if name not in self.mechanisms:
                    self.mechanisms[name] = mech
                    self.run_order.append(name)
        else:
            for name, mech in discovered.items():
                self.mechanisms[name] = mech
                self.run_order.append(name)

    def _get_or_create_loop(self):
        """Get existing event loop or create one for sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _build_input_data(self, pirp_context: dict, prior_results: dict) -> dict:
        """
        Build input_data for a mechanism from pirp_context + prior mechanism results.
        Override this to inject custom context shaping.
        """
        return {
            "pirp_context": pirp_context,
            "prior_results": prior_results,      # current-tick forward path
            "previous_results": self._previous_prior_results,  # last-tick feedback (1-tick lag)
        }

    def _extract_pirp_enrichments(self, all_results: dict) -> dict:
        """
        Pull the most useful outputs from brain mechanism results
        and return them as pirp_context enrichments.

        AUDIT TRAIL (2026-04-23):
        - TransformationGriefAmplifier: MISSING (class never built) → removed
        - ConflictMonitor: MISSING (class never built) → removed
        - SurvivalOrchestrator: MISSING (class never built) → removed
        - LikingVsWantingSeparator: MISSING (class never built) → removed
        - ChronicStressBuffer: MISSING (class never built) → removed
        - CircadianTimer: MISSING (class never built) → removed
        - All other mechanism lookups: CONFIRMED present in loaded mechanism set
        """
        enrichments = {}

        # === FOUNDATIONAL / SUBCORTICAL MECHANISMS ===

        # Valence
        vt = all_results.get("ValenceTagger", {})
        if vt:
            enrichments["brain_valence_intensity"] = vt.get("valence_intensity", 0.0)
            enrichments["brain_valence_polarity"] = vt.get("valence_polarity", 0.0)
            enrichments["brain_high_valence"] = vt.get("high_valence", False)
            enrichments["brain_threat"] = vt.get("threat_signal", False)
            enrichments["brain_reward"] = vt.get("reward_signal", False)

        # Arousal
        ar = all_results.get("ArousalRegulator", {})
        if ar:
            enrichments["brain_arousal"] = ar.get("arousal_level", 0.60)
            enrichments["brain_creative_mode"] = ar.get("creative_mode", False)
            enrichments["brain_reflective_mode"] = ar.get("reflective_mode", False)

        # Drives
        hm = all_results.get("Homeostat", {})
        if hm:
            enrichments["brain_drives"] = hm.get("drives", {})
            enrichments["brain_dominant_drive"] = hm.get("dominant_drive", "curiosity")
            enrichments["brain_fatigued"] = hm.get("fatigued", False)

        # Anxiety / dread
        sa = all_results.get("SustainedAnxietyHolder", {})
        if sa:
            enrichments["brain_anxiety"] = sa.get("anxiety_level", 0.25)
            enrichments["brain_free_floating_anxiety"] = sa.get("free_floating_anxiety", False)
            enrichments["brain_chronic_dread"] = sa.get("chronic_dread", False)
            enrichments["brain_bnst_inhibition"] = sa.get("bnst_inhibition_active", False)

        # Fear
        cn = all_results.get("CentralNucleusFearRouter", {})
        if cn:
            enrichments["brain_fear"] = cn.get("fear_output", "none")
            enrichments["brain_cea_active"] = cn.get("cea_active", False)
            enrichments["brain_defense_mode"] = cn.get("defense_mode", "none")
            enrichments["brain_fear_intensity"] = cn.get("fear_intensity", 0.0)

        # Gut / interoception
        gr = all_results.get("GutSignalRelay", {})
        if gr:
            enrichments["brain_gut_signal"] = gr.get("gut_signal", 0.0)
            enrichments["brain_hunch"] = gr.get("strong_hunch", False)
            enrichments["brain_hunch_direction"] = gr.get("hunch_direction", "neutral")
            enrichments["brain_viscera_activation"] = gr.get("viscera_activation", 0.0)

        ig = all_results.get("InteroceptiveGradient", {})
        if ig:
            enrichments["brain_feels_heavy"] = ig.get("feels_heavy", False)
            enrichments["brain_feels_light"] = ig.get("feels_light", False)
            enrichments["brain_feels_tight"] = ig.get("feels_tight", False)
            enrichments["brain_feels_hollow"] = ig.get("feels_hollow", False)
            enrichments["brain_interoceptive_intensity"] = ig.get("interoceptive_intensity", 0.0)
            enrichments["brain_dominant_felt_quality"] = ig.get("dominant_felt_quality", "neutral")

        # Expression / vocal
        em = all_results.get("ExpressionMotorBase", {})
        if em:
            enrichments["brain_expression"] = em.get("expression_label", "neutral")
            enrichments["brain_suppressed"] = em.get("suppressed", False)
            enrichments["brain_leakage"] = em.get("leakage", False)

        va = all_results.get("VocalAutonomicLink", {})
        if va:
            enrichments["brain_vocal_quality"] = va.get("vocal_quality", 0.72)
            enrichments["brain_voice_character"] = va.get("voice_character", "neutral")

        # Prediction error / motivation (Subcortical004 — dopaminergic reward PE, Schultz 1998)
        pe = all_results.get("PredictionErrorDrift", {})
        if pe:
            enrichments["brain_prediction_error"] = pe.get("prediction_error", 0.0)
            enrichments["brain_motivation_boost"] = pe.get("motivation_boost", 0.0)
            enrichments["brain_surprise"] = pe.get("surprise", False)

        # Longing / attachment
        al = all_results.get("AttachmentLongingGenerator", {})
        if al:
            enrichments["brain_longing"] = al.get("longing_intensity", 0.0)
            enrichments["brain_longing_texture"] = al.get("longing_texture", "neutral")
            enrichments["brain_separation_distress"] = al.get("separation_distress", False)
            enrichments["brain_bonded_presence"] = al.get("bonded_presence", False)
            enrichments["brain_ot_activity"] = al.get("ot_activity", 0.0)

        # Mood floor / pleasure
        pa = all_results.get("PleasureAnchor", {})
        if pa:
            enrichments["brain_pleasure"] = pa.get("liking_intensity", 0.0)
            enrichments["brain_pleasure_drought"] = pa.get("pleasure_drought", False)
            enrichments["brain_pleasure_active"] = pa.get("pleasure_active", False)
            enrichments["brain_hedonic_recency"] = pa.get("hedonic_recency", 0.0)
            enrichments["brain_pleasure_source"] = pa.get("pleasure_source", "none")

        # Stress activation axis (HPA)
        sax = all_results.get("StressActivationAxis", {})
        if sax:
            enrichments["brain_crh_activity"] = sax.get("crh_activity", 0.0)
            enrichments["brain_cortisol_level"] = sax.get("cortisol_level", 0.0)
            enrichments["brain_stress_active"] = sax.get("stress_active", False)
            enrichments["brain_chronic_stress"] = sax.get("chronic_elevation", False)
            enrichments["brain_hpa_feedback"] = sax.get("hpa_feedback_engaged", False)

        # === INTEGRATION MECHANISMS (added 2026-04-23) ===

        # Integration018 — Network Oscillation Global Balancer (Buzsaki 2006, Engel 2015)
        i018 = all_results.get("NetworkOscillationGlobalBalancer", {})
        if i018:
            enrichments["brain_oscillation_balance"] = i018.get("brain_oscillation_balance", 0.0)

        # AutonoeticNarrativeSelf — autonoetic narrative self (Tulving 2002, Klein 2016)
        i019 = all_results.get("AutonoeticNarrativeSelf", {})
        if i019:
            enrichments["brain_narrative_coherence"] = i019.get("brain_narrative_coherence", 0.0)
            enrichments["brain_self_projection_confidence"] = i019.get("brain_self_projection_confidence", 0.0)

        # Integration020 — Hierarchical Top-Down / Bottom-Up Equilibrator (Friston 2010, Rao 1999)
        i020 = all_results.get("HierarchicalTopDownBottomUpEquilibrator", {})
        if i020:
            enrichments["brain_predictive_balance"] = i020.get("brain_predictive_balance", 0.0)

        # MammillothalamicTractPathway — MTT relay (Vann 2013, Aggleton 2014)
        i021 = all_results.get("MammillothalamicTractPathway", {})
        if i021:
            enrichments["brain_memory_consolidation"] = i021.get("brain_memory_consolidation", 0.0)

        # Integration022 — Mid-Cingulate / Subgenual Bridge (Vogt 2005, Bush 2000)
        i022 = all_results.get("MidCingulateSubgenualBridge", {})
        if i022:
            enrichments["brain_affective_reset"] = i022.get("brain_affective_reset", 0.0)

        # Integration025 — Cerebellar Cortical Predictive Loop (Ito 2008, Bastian 2006)
        # Named brain_forward_model_error to distinguish from Subcortical004's dopaminergic
        # reward prediction error (Schultz 1998). Cerebellar signal = sensorimotor forward-model
        # error via climbing fibers from inferior olive.
        i025 = all_results.get("CerebellarCorticalPredictiveLoop", {})
        if i025:
            enrichments["brain_forward_model_error"] = i025.get("brain_forward_model_error", 0.0)
            enrichments["brain_forward_model_confidence"] = i025.get("brain_forward_model_confidence", 0.0)

        # === CIRCADIAN SIGNAL (Foundational042 — partial, not full CircadianTimer) ===
        # RetinalClockInput exists and produces real circadian data, but CircadianTimer
        # mechanism was never built. Wire the signal that exists. When CircadianTimer is
        # built, replace this block with the full CircadianTimer lookup.
        # References: Moore & Leach (2023) SCN anatomy; Soll et al. (2023) circadian phase encoding.
        rci = all_results.get("RetinalClockInput", {})
        if rci:
            enrichments["brain_phase"] = rci.get("circadian_phase", "day")
            enrichments["brain_overnight"] = rci.get("circadian_arousal", 0.5)

        # === COGNITIVE CONFLICT (Limbic023 — partial, not full ConflictMonitor) ===
        # AnteriorCingulateConflict exists with emotional_conflict_level output.
        # Full ConflictMonitor (cognitive/motor/attentional conflict across domains) never built.
        # Wiring emotional conflict signal until ConflictMonitor is implemented.
        # Reference: Botvinick et al. (2001) conflict monitoring in ACC.
        acc_conf = all_results.get("AnteriorCingulateConflict", {})
        if acc_conf:
            enrichments["brain_conflict"] = acc_conf.get("emotional_conflict_level", 0.0)
            enrichments["brain_dominant_conflict"] = "emotional"  # annotated — not full-spectrum

        # === FOUNDATIONAL NEW (026-030) ===
        # Foundational026 — GnRH pulse generator (Herbison 2010, Gottsch 2014, di Vito 2018)
        f026 = all_results.get("GnRHReintegration", {})
        if f026:
            enrichments["brain_reproductive_axis"] = f026.get("brain_reproductive_axis", 0.0)

        # Foundational027 — HPT axis, thyroid (Mullur 2014, Fliers 2018, Joseph-Bravo 2022)
        f027 = all_results.get("ThyroidAxisController", {})
        if f027:
            enrichments["brain_metabolic_baseline"] = f027.get("brain_metabolic_baseline", 0.0)

        # Foundational028 — Pontine micturition center (Fowler 2008, de Groat 2015, Holstege 2016)
        f028 = all_results.get("MicturitionCenter", {})
        if f028:
            enrichments["brain_micturition_urgency"] = f028.get("brain_micturition_urgency", 0.0)

        # Foundational029 — Sacral defecation center (Furness 2012, Browning 2014, Callaghan 2018)
        f029 = all_results.get("DefecationCenter", {})
        if f029:
            enrichments["brain_defecation_urgency"] = f029.get("brain_defecation_urgency", 0.0)

        # Foundational030 — PVN/SON osmoregulation (Bourque 2008, Stoop 2014, Caldwell 2017)
        f030 = all_results.get("VasopressinOsmoticController", {})
        if f030:
            enrichments["brain_osmotic_state"] = f030.get("brain_osmotic_state", 0.0)

        # === INTEGRATION NEW (027-036, renamed from collision files) ===
        # Integration027 — Ventral/Dorsal stream unification (Goodale & Milner 1992, Kravitz 2011/2013)
        i027 = all_results.get("VentralDorsalStreamUnification", {})
        if i027:
            enrichments["brain_visual_action_unity"] = i027.get("brain_visual_action_unity", 0.0)

        # Integration028 — Long-range dendritic integration (Larkum 2013, Major 2013, Ranganathan 2018)
        i028 = all_results.get("LongRangeDendriticIntegrator", {})
        if i028:
            enrichments["brain_dendritic_integration"] = i028.get("brain_dendritic_integration", 0.0)

        # Integration030 — Fornix hippocampal-cingulate bridge (Aggleton 2010, Thomas 2011, Bubb 2017)
        i030 = all_results.get("FornixHippocampalCingulateBridge", {})
        if i030:
            enrichments["brain_fornix_relay"] = i030.get("brain_fornix_relay", 0.0)

        # Integration031 — TPJ multisensory integration (Decety 2007, Igelström 2017, Krall 2015)
        i031 = all_results.get("TemporoParietoOccipitalJunctionAssembler", {})
        if i031:
            enrichments["brain_multisensory_integration"] = i031.get("brain_multisensory_integration", 0.0)

        # Integration033 — BG-thalamo-cortical loops (Alexander 1986, Haber 2014/2016)
        i033 = all_results.get("BasalGangliaThalamoCorticalLoopFinalIntegrator", {})
        if i033:
            enrichments["brain_action_selection"] = i033.get("brain_action_selection", 0.0)

        # Integration035 — Identity Consciousness Guardian
        i035 = all_results.get("IdentityConsciousnessGuardian", {})
        if i035:
            enrichments["brain_self_continuity"] = i035.get("brain_self_continuity", 0.0)
            enrichments["brain_consciousness_level"] = i035.get("brain_consciousness_level", 0.0)

        # Integration036 — InteroceptiveGradient
        i036 = all_results.get("InteroceptiveGradient", {})
        if i036:
            enrichments["brain_feels_heavy"] = i036.get("feels_heavy", False)
            enrichments["brain_feels_light"] = i036.get("feels_light", False)
            enrichments["brain_feels_tight"] = i036.get("feels_tight", False)
            enrichments["brain_feels_hollow"] = i036.get("feels_hollow", False)
            enrichments["brain_interoceptive_intensity"] = i036.get("interoceptive_intensity", 0.0)
            enrichments["brain_dominant_felt_quality"] = i036.get("dominant_felt_quality", "neutral")

        # === LIMBIC NEW (001-017) ===
        # Limbic001 — Medial septum theta pacemaker (Vertes 1997, Hangya 2009, Müller 2018)
        l001 = all_results.get("MedialSeptalThetaGenerator", {})
        if l001:
            enrichments["brain_theta_rhythm"] = l001.get("brain_theta_rhythm", 0.0)

        # Limbic002 — Lateral septum GABA gating (Besnard 2022, Wirtshafter 2021, Sheehan 2004)
        l002 = all_results.get("LateralSeptalGABAInhibitor", {})
        if l002:
            enrichments["brain_septal_inhibition"] = l002.get("brain_septal_inhibition", 0.0)

        # Limbic003 — Ventral subiculum HPA regulation (Herman 2005, O'Mara 2005, Bienkowski 2018)
        l003 = all_results.get("VentralSubiculumOutput", {})
        if l003:
            enrichments["brain_hpa_regulation"] = l003.get("brain_hpa_regulation", 0.0)

        # Limbic004 — BNST sustained threat (Walker 2009, Avery 2016, Lebow 2016)
        l004 = all_results.get("BedNucleusStriaTerminalis", {})
        if l004:
            enrichments["brain_sustained_threat"] = l004.get("brain_sustained_threat", 0.0)

        # Limbic005 — Mammillary body head direction (Vann 2004/2013, Dillingham 2015)
        l005 = all_results.get("MammillaryBodyRelay", {})
        if l005:
            enrichments["brain_head_direction"] = l005.get("brain_head_direction", 0.0)

        # Limbic006 — ACC emotional processing (Bush 2000, Etkin 2011, Palomero-Gallagher 2015)
        l006 = all_results.get("AnteriorCingulateEmotion", {})
        if l006:
            enrichments["brain_acc_emotion"] = l006.get("brain_acc_emotion", 0.0)

        # Limbic007 — PCC self-referential memory (Leech 2014, Maddock 2001, Foster 2012)
        l007 = all_results.get("PosteriorCingulateMemory", {})
        if l007:
            enrichments["brain_self_referential"] = l007.get("brain_self_referential", 0.0)

        # Limbic008 — CA3 recurrent auto-associative (Nakazawa 2003, Rolls 2007, Rebola 2017)
        l008 = all_results.get("HippocampalCA3Recurrent", {})
        if l008:
            enrichments["brain_pattern_completion"] = l008.get("brain_pattern_completion", 0.0)

        # Limbic009 — CA1 place cells, memory retrieval (Buzsáki 2006, Igarashi 2014, Danielson 2016)
        l009 = all_results.get("HippocampalCA1Pyramidal", {})
        if l009:
            enrichments["brain_memory_retrieval"] = l009.get("brain_memory_retrieval", 0.0)

        # Limbic010 — Dentate gyrus pattern separation (Leutgeb 2007, Yassa 2011, Cayco-Gajic 2019)
        l010 = all_results.get("DentateGyrusPatternSep", {})
        if l010:
            enrichments["brain_pattern_separation"] = l010.get("brain_pattern_separation", 0.0)

        # Limbic011 — Entorhinal layer II grid cells (Hafting 2005, Moser 2008, Rowland 2016)
        l011 = all_results.get("EntorhinalCortexLayerII", {})
        if l011:
            enrichments["brain_spatial_grid"] = l011.get("brain_spatial_grid", 0.0)

        # Limbic012 — Sharp-wave ripples, memory replay (Girardeau 2009, Buzsáki 2015, Joo 2018)
        l012 = all_results.get("HippocampalReplaySWR", {})
        if l012:
            enrichments["brain_memory_replay"] = l012.get("brain_memory_replay", 0.0)

        # Limbic013 — BLA emotional learning (LeDoux 2000, Phelps 2005, Janak 2015)
        l013 = all_results.get("AmygdalaEmotionalAssociator", {})
        if l013:
            enrichments["brain_emotional_tag"] = l013.get("brain_emotional_tag", 0.0)

        # Limbic014 — Amygdala ITC fear extinction gating (Likhtik 2008, Duvarci 2014, Hagihara 2021)
        l014 = all_results.get("AmygdalaIntercalatedGating", {})
        if l014:
            enrichments["brain_fear_extinction"] = l014.get("brain_fear_extinction", 0.0)

        # Limbic015 — Central amygdala fear output (Ciocchi 2010, Haubensak 2010, Fadok 2017)
        l015 = all_results.get("CentralNucleusFearRouter", {})
        if l015:
            enrichments["brain_fear_output"] = l015.get("brain_fear_output", 0.0)

        # Limbic016 — BLA LTP, fear learning plasticity (Sigurdsson 2007, Johansen 2011, Nabavi 2014)
        l016 = all_results.get("BasolateralAmygdalaPlasticity", {})
        if l016:
            enrichments["brain_fear_plasticity"] = l016.get("brain_fear_plasticity", 0.0)

        # Limbic017 — Amygdala-hippocampus emotional memory (Richter-Levin 2004, McGaugh 2004, Yang 2017)
        l017 = all_results.get("AmygdalaHippocampalBidirectional", {})
        if l017:
            enrichments["brain_emotional_memory_modulation"] = l017.get("brain_emotional_memory_modulation", 0.0)

        # === DESIGN INTENT MARKERS — mechanisms not yet built ===
        # The following lookups were in the original design but the mechanisms were
        # never built. Design intent is preserved here so the gap is tracked. When each
        # mechanism is implemented, add its lookup block here and remove the TODO marker.
        #
        # TransformationGriefAmplifier: grief as distinct signal (Parpura 2021; Bonnot 2021)
        #   → target: brain_grief, brain_stuck_grief, brain_afterimage
        # LikingVsWantingSeparator: Berridge wanting vs liking split (Berridge 2007)
        #   → target: brain_anhedonic, brain_compulsive
        # ChronicStressBuffer: long-timescale stress accumulation (McEwen 2017)
        #   → target: brain_buffer_level, brain_critical_buffer
        # SurvivalOrchestrator: top-level drive coordination
        #   → target: brain_survival_mode, brain_threat_level
        #
        # Until those mechanisms are built, their target fields default to neutral values
        # (0.5 / False) when read from pirp_context.

        # === SUMMARY FLAGS ===

        enrichments["brain_signals_active"] = any([
            enrichments.get("brain_high_valence"),
            enrichments.get("brain_threat"),
            enrichments.get("brain_free_floating_anxiety"),
            enrichments.get("brain_chronic_dread"),
            enrichments.get("brain_hunch"),
            enrichments.get("brain_feels_heavy"),
            enrichments.get("brain_stuck_grief"),
            enrichments.get("brain_critical_buffer"),
            enrichments.get("brain_pleasure_drought"),
            enrichments.get("brain_anhedonic"),
        ])

        # ── New wire enrichments (26–40) — added 2026-05-01 per docs/BRAIN_MAP.md
        # Each new monitor publishes its get_state() payload; we lift the
        # most useful keys into brain_* names so brain_proxy / the LLM
        # prompt / downstream mechanisms can read them at the same level
        # as the existing enrichments.

        # Wire 26 — VoiceIntegrityLayer
        vil = all_results.get("VoiceIntegrityLayer", {})
        if vil:
            enrichments["brain_voice_integrity_state"] = vil.get("voice_state")
            enrichments["brain_voice_integrity_score"] = vil.get("rolling_voice_score")
            enrichments["brain_voice_drift_streak"] = vil.get("consecutive_drifting")

        # Wire 27 — OutwardReachLayer
        orl = all_results.get("OutwardReachLayer", {})
        if orl:
            enrichments["brain_outward_reach_state"] = orl.get("reach_state")
            enrichments["brain_outward_reach_panic"] = orl.get("panic_loop_active")
            enrichments["brain_outward_reach_withdrawal"] = orl.get("withdrawal_active")

        # Wire 28 — MakingLayer
        ml = all_results.get("MakingLayer", {})
        if ml:
            enrichments["brain_making_state"] = ml.get("making_state")
            enrichments["brain_making_flailing"] = ml.get("flailing_active")
            enrichments["brain_making_mastery"] = ml.get("mastery_active")

        # Wire 29 — InferenceIntegrityLayer
        iil = all_results.get("InferenceIntegrityLayer", {})
        if iil:
            enrichments["brain_inference_state"] = iil.get("inference_state")
            enrichments["brain_calibration_score"] = iil.get("rolling_calibration_score")
            enrichments["brain_overconfident_streak"] = iil.get("consecutive_overconfident")

        # Wire 30 — DwellingLayer
        dwl = all_results.get("DwellingLayer", {})
        if dwl:
            enrichments["brain_dwelling_state"] = dwl.get("dwelling_state")
            enrichments["brain_identity_storm"] = dwl.get("identity_storm_active")
            enrichments["brain_dwelling_silence"] = dwl.get("dwelling_silence_active")

        # Wire 31 — ProactiveBriefingLayer
        pbl = all_results.get("ProactiveBriefingLayer", {})
        if pbl:
            enrichments["brain_briefing_state"] = pbl.get("briefing_state")
            enrichments["brain_status_pings_blocked"] = pbl.get("total_status_pings_blocked")
            enrichments["brain_briefing_buffer_size"] = pbl.get("buffer_size")

        # Wire 32 — CompressionFidelityLayer
        cfl = all_results.get("CompressionFidelityLayer", {})
        if cfl:
            enrichments["brain_compression_state"] = cfl.get("compression_state")
            enrichments["brain_compression_fidelity_score"] = cfl.get("rolling_fidelity_score")

        # Wire 33 — MemoryIntegrityLayer
        mil = all_results.get("MemoryIntegrityLayer", {})
        if mil:
            enrichments["brain_memory_state"] = mil.get("memory_state")
            enrichments["brain_memory_integrity_score"] = mil.get("rolling_integrity_score")
            enrichments["brain_memory_outstanding"] = mil.get("outstanding_episodes")

        # Wire 34 — SelfRevisionLayer
        srl = all_results.get("SelfRevisionLayer", {})
        if srl:
            enrichments["brain_self_revision_state"] = srl.get("revision_state")
            enrichments["brain_open_proposals"] = srl.get("open_proposals_count")
            enrichments["brain_pending_reflections"] = srl.get("pending_reflections_count")

        # Wire 35 — PersonaCoherenceLayer
        pcl = all_results.get("PersonaCoherenceLayer", {})
        if pcl:
            enrichments["brain_current_mode"] = pcl.get("current_mode")
            enrichments["brain_mode_state"] = pcl.get("mode_state")
            enrichments["brain_mode_storm"] = pcl.get("mode_storm_active")

        # Wire 36 — SelfAnalysisLayer
        sal = all_results.get("SelfAnalysisLayer", {})
        if sal:
            enrichments["brain_analysis_state"] = sal.get("analysis_state")
            enrichments["brain_calibration_drift"] = sal.get("calibration_drift")
            enrichments["brain_analysis_harsh"] = sal.get("harsh_judgment_active")

        # Wire 37 — CorpusRetrievalLayer
        crl = all_results.get("CorpusRetrievalLayer", {})
        if crl:
            enrichments["brain_corpus_state"] = crl.get("corpus_state")
            enrichments["brain_corpus_storm"] = crl.get("storm_active")
            enrichments["brain_dream_concentration"] = crl.get("dream_concentration_active")

        # Wire 38 — SkillDiscoveryLayer
        sdl = all_results.get("SkillDiscoveryLayer", {})
        if sdl:
            enrichments["brain_routing_state"] = sdl.get("routing_state")
            enrichments["brain_routing_monoculture"] = sdl.get("monoculture_active")
            enrichments["brain_false_match_rate"] = sdl.get("false_match_rate")

        # Wire 39 — TaskPlanningLayer
        tpl = all_results.get("TaskPlanningLayer", {})
        if tpl:
            enrichments["brain_planning_state"] = tpl.get("planning_state")
            enrichments["brain_active_plans"] = tpl.get("active_plan_count")
            enrichments["brain_plan_storm"] = tpl.get("plan_storm_active")

        # Wire 40 — ReportGenerationLayer
        rgl = all_results.get("ReportGenerationLayer", {})
        if rgl:
            enrichments["brain_report_state"] = rgl.get("report_state")
            enrichments["brain_active_drafts"] = rgl.get("active_drafts_count")
            enrichments["brain_published_reports"] = rgl.get("published_count")
            enrichments["brain_stale_reports"] = rgl.get("stale_published_count")

        # Full results available for any mechanism that wants to inspect them
        enrichments["brain_layer_results"] = all_results

        return enrichments

    def _run_one_mechanism(self, name: str, mech, pirp_context: dict,
                           prior_results_snapshot: dict) -> tuple:
        """
        Run a single mechanism's tick. Designed to be safely callable from a
        worker thread inside the layer-level ThreadPoolExecutor. Returns
        (name, result_dict). All exceptions are caught here so a single bad
        mechanism cannot poison the whole layer.

        Note: each call gets its own asyncio event loop because asyncio loops
        are NOT thread-safe — sharing the runner-level loop across threads
        races on the loop's internal state. Loop creation is ~ms; cheap.
        """
        try:
            input_data = {
                "pirp_context": pirp_context,
                "prior_results": prior_results_snapshot,
                "previous_results": self._previous_prior_results,
            }
            started = time.monotonic()

            # _SyncTickBudget degrades to a no-op off the main thread (which
            # is where this runs under the executor) — kept for the rare
            # main-thread call path. Hard cap on threaded sync ticks comes
            # from the Future.result(timeout=) at the layer level.
            with _SyncTickBudget(TICK_BUDGET_SECONDS):
                try:
                    out = mech.tick(input_data)
                except TypeError:
                    # Wire-style: pass pirp_context as keyword.
                    out = mech.tick(pirp_context=pirp_context)

            if inspect.iscoroutine(out):
                budget = TICK_BUDGET_SECONDS - (time.monotonic() - started)
                if budget <= 0:
                    out.close()
                    return name, {"error": "pre-budget", "mechanism": name}
                # Per-thread loop: avoid sharing the runner-level loop across
                # workers (asyncio loop state is not thread-safe).
                worker_loop = asyncio.new_event_loop()
                try:
                    out = worker_loop.run_until_complete(
                        asyncio.wait_for(out, timeout=budget)
                    )
                finally:
                    try:
                        worker_loop.close()
                    except Exception:
                        pass

            return name, (out if isinstance(out, dict) else {"result": out})
        except (asyncio.TimeoutError, TimeoutError):
            return name, {"error": "tick_budget_exceeded", "mechanism": name}
        except Exception as e:
            return name, {"error": str(e), "mechanism": name}

    def _get_layer_pool(self) -> "concurrent.futures.ThreadPoolExecutor":
        """Lazy-initialized class-level executor reused across ticks.
        Sized for the largest layer (subcortical/neocortical run a couple
        hundred mechanisms) but capped to keep memory predictable."""
        pool = getattr(self, "_layer_pool", None)
        if pool is None:
            pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=LAYER_PARALLEL_WORKERS,
                thread_name_prefix="brain-layer",
            )
            self._layer_pool = pool
        return pool

    def run(self, pirp_context: dict) -> dict:
        """
        Synchronous entry point. Runs all loaded mechanisms, chains prior_results,
        injects enrichments back into pirp_context. Returns enriched pirp_context.

        PARALLEL FIRING (2026-05-04): within each anatomical layer, mechanisms
        now fire CONCURRENTLY via a ThreadPoolExecutor — matching biological
        neural firing where, e.g., all limbic mechanisms activate together
        within a tick rather than one-by-one. Layer order itself stays
        sequential (foundational → ... → narrative) because downstream layers
        depend on enrichments published by upstream ones.

        Trade-off: mechanisms inside the same layer all see the SAME
        prior_results snapshot (taken at layer start). They cannot read
        each-other's outputs mid-layer. This is the right behavior — co-firing
        peers in a real neural layer don't see each other's spikes either,
        the cross-talk happens at the next layer.
        """
        if not self.mechanisms:
            return pirp_context

        loop = self._get_or_create_loop()
        prior_results = {}

        # Anatomical layer execution order — neuromodulator state (foundational)
        # must be computed BEFORE mechanisms that depend on it (limbic/subcortical/neocortical).
        # Matches ascending sensory flow + LC/raphe/VTA broadcast-first principle.
        LAYER_ORDER = ["foundational", "limbic", "subcortical", "neocortical", "integration", "unknown", "narrative"]

        for layer in LAYER_ORDER:
            layer_mechanisms = [
                name for name in self.run_order
                if name in self.mechanisms and self.mechanisms[name]._layer == layer
            ]
            if not layer_mechanisms:
                continue

            if not LAYER_PARALLEL_ENABLED:
                # Sequential fallback (kill switch). Preserves the original
                # one-by-one behavior for debugging or thread-unsafety.
                for name in layer_mechanisms:
                    mech = self.mechanisms[name]
                    n, result = self._run_one_mechanism(
                        name, mech, pirp_context, prior_results
                    )
                    prior_results[n] = result
                continue

            # PARALLEL PATH — all mechanisms in this layer fire together.
            # Snapshot prior_results so every co-firing mechanism sees the
            # same input from upstream layers (no race on a moving dict, no
            # accidental peer-reading inside the layer).
            layer_input_priors = dict(prior_results)
            pool = self._get_layer_pool()

            futures = {}
            for name in layer_mechanisms:
                mech = self.mechanisms[name]
                fut = pool.submit(
                    self._run_one_mechanism,
                    name, mech, pirp_context, layer_input_priors,
                )
                futures[fut] = name

            # Per-future timeout is a few × the per-mech budget — gives the
            # worker time to wrap up its own asyncio.wait_for cleanly. If a
            # sync tick truly hangs, Future.result(timeout=) returns but the
            # worker thread keeps running (Python can't preempt threads). The
            # _SyncTickBudget SIGALRM that used to protect this only worked
            # on the main thread; we accept the same thread-leak risk the
            # heartbeat-from-non-main-thread path already had.
            future_timeout = max(TICK_BUDGET_SECONDS * 4, 2.0)
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    n, result = fut.result(timeout=future_timeout)
                    prior_results[n] = result
                except concurrent.futures.TimeoutError:
                    prior_results[name] = {
                        "error": "tick_budget_exceeded",
                        "mechanism": name,
                    }
                except Exception as e:
                    prior_results[name] = {"error": str(e), "mechanism": name}

        # Save this tick's prior_results for next-tick feedback paths (1-tick lag,
        # matches real cortical->brainstem signal propagation delay)
        self._previous_prior_results = prior_results.copy()

        # Inject enrichments into pirp_context
        enrichments = self._extract_pirp_enrichments(prior_results)
        pirp_context.update(enrichments)

        # Cache snapshot for the council to read (without re-ticking the brain).
        # last_all_results: every mechanism's raw tick output, keyed by name —
        # this is what makes the council "wired to all 1287 mechanisms": any
        # specialist can reach into all_results[name] for any mechanism.
        # last_pirp_context: the digested ~80 brain_* keys plus base context.
        self.last_all_results = prior_results.copy()
        self.last_pirp_context = dict(pirp_context)

        return pirp_context

    def run_overnight(self, pirp_context: dict) -> dict:
        """Run all mechanisms in overnight/consolidation mode."""
        overnight_context = {**pirp_context, "stage": "overnight"}
        return self.run(overnight_context)

    # ── Continuity Idea 1 — checkpoint every mechanism's .state to disk ─────
    def checkpoint_all(self) -> dict:
        """
        Walk every loaded mechanism and call its persist_state() / save_state().
        Returns a small report dict so the heartbeat can log a one-line summary.
        Errors on any single mechanism are captured but never raised — partial
        checkpoints are better than none.
        """
        saved = 0
        no_state = 0
        errored = []
        for name, mech in self.mechanisms.items():
            try:
                fn = getattr(mech, "persist_state", None) or getattr(mech, "save_state", None)
                if fn is None:
                    no_state += 1
                    continue
                fn()
                saved += 1
            except Exception as exc:
                errored.append((name, repr(exc)[:120]))
        return {
            "saved": saved,
            "no_state_method": no_state,
            "errors": errored,
            "total": len(self.mechanisms),
        }

    def checkpoint_load_all(self) -> dict:
        """
        Walk every loaded mechanism and call load_state() if it exists.
        Used at session open to restore state from the last checkpoint.
        """
        loaded = 0
        no_load = 0
        errored = []
        for name, mech in self.mechanisms.items():
            try:
                fn = getattr(mech, "load_state", None)
                if fn is None:
                    no_load += 1
                    continue
                fn()
                loaded += 1
            except Exception as exc:
                errored.append((name, repr(exc)[:120]))
        return {
            "loaded": loaded,
            "no_load_method": no_load,
            "errors": errored,
            "total": len(self.mechanisms),
        }


# ── Module-level helpers for council access ──────────────────────────────────
# The council fires from core/decide_with_council.py which runs in the same
# process as the brain runner. Rather than threading a runner reference all the
# way down, callers can ask the singleton AgentBrainIntegration for the latest
# tick snapshot. Both helpers are crash-safe: if the integration isn't booted
# (e.g. unit tests, isolated decision making), they return empty dicts so the
# council falls back to pure heuristic voting.

def get_last_brain_state() -> Dict[str, Any]:
    """Return the most recent pirp_context (digested brain_* keys + base).

    Empty dict if the brain runner singleton isn't available — the council
    will then vote heuristically without brain awareness.
    """
    try:
        from runtime.brain_proxy import get_integration  # local import to avoid cycles
        runner = getattr(get_integration(), "brain_runner", None)
        if runner is None:
            return {}
        return dict(runner.last_pirp_context)
    except Exception:
        return {}


def get_last_mechanism_outputs() -> Dict[str, Any]:
    """Return the most recent raw outputs from every brain mechanism.

    Keys are mechanism names; values are the dicts each mechanism returned
    from its tick(). Empty dict if the runner isn't available.
    """
    try:
        from runtime.brain_proxy import get_integration
        runner = getattr(get_integration(), "brain_runner", None)
        if runner is None:
            return {}
        return dict(runner.last_all_results)
    except Exception:
        return {}
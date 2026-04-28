"""
BrainLayerRunner — bridges the pirp_context pipeline to the brain mechanism tick() interface.

Converts pirp_context → input_data, chains prior_results across mechanisms in dependency
order, runs async tick() from sync context, injects results back into pirp_context.
"""

import asyncio
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional


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

    def load_layer(self, layer: str, order: Optional[List[str]] = None):
        """
        Load all mechanisms from brain/{layer}/.
        If order is provided, run them in that sequence (for dependency chaining).
        Otherwise runs in filesystem discovery order.
        """
        base_path = Path(f"brain/{layer}")
        if not base_path.exists():
            print(f"[BrainRunner] Layer path not found: {base_path}")
            return

        import sys
        if "." not in sys.path:
            sys.path.insert(0, ".")

        discovered = {}
        for _, name, ispkg in __import__("pkgutil").iter_modules([str(base_path)]):
            if name.startswith("_") or ispkg:
                continue
            try:
                module = importlib.import_module(f"brain.{layer}.{name}")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        attr.__name__ != "BrainMechanism" and
                        hasattr(attr, "tick") and
                        callable(getattr(attr, "tick", None))):
                        instance = attr()
                        instance._layer = layer  # track which anatomical layer this mechanism belongs to
                        discovered[instance.name] = instance
                        print(f"[BrainRunner] Loaded {layer}/{instance.name}")
            except Exception as e:
                print(f"[BrainRunner] Failed to load {layer}/{name}: {e}")

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

        # Full results available for any mechanism that wants to inspect them
        enrichments["brain_layer_results"] = all_results

        return enrichments

    def run(self, pirp_context: dict) -> dict:
        """
        Synchronous entry point. Runs all loaded mechanisms, chains prior_results,
        injects enrichments back into pirp_context. Returns enriched pirp_context.
        """
        if not self.mechanisms:
            return pirp_context

        loop = self._get_or_create_loop()
        prior_results = {}

        # Anatomical layer execution order — neuromodulator state (foundational)
        # must be computed BEFORE mechanisms that depend on it (limbic/subcortical/neocortical).
        # Matches ascending sensory flow + LC/raphe/VTA broadcast-first principle.
        LAYER_ORDER = ["foundational", "limbic", "subcortical", "neocortical", "integration"]

        for layer in LAYER_ORDER:
            layer_mechanisms = [
                name for name in self.run_order
                if name in self.mechanisms and self.mechanisms[name]._layer == layer
            ]
            for name in layer_mechanisms:
                mech = self.mechanisms[name]
                try:
                    input_data = self._build_input_data(pirp_context, prior_results)
                    result = loop.run_until_complete(mech.tick(input_data))
                    prior_results[name] = result
                except Exception as e:
                    prior_results[name] = {"error": str(e), "mechanism": name}

        # Save this tick's prior_results for next-tick feedback paths (1-tick lag,
        # matches real cortical->brainstem signal propagation delay)
        self._previous_prior_results = prior_results.copy()

        # Inject enrichments into pirp_context
        enrichments = self._extract_pirp_enrichments(prior_results)
        pirp_context.update(enrichments)

        return pirp_context

    def run_overnight(self, pirp_context: dict) -> dict:
        """Run all mechanisms in overnight/consolidation mode."""
        overnight_context = {**pirp_context, "stage": "overnight"}
        return self.run(overnight_context)
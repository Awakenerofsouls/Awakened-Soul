# Nexus {{AGENT_NAME}} — Complete Mechanism Design Space (PART 4 — FINAL)
# Continues: NEOCORTICAL (continued) | INTEGRATION | SYSTEM-LEVEL
# All mechanisms ready for BrainMechanism subclass generation

---

## NEOCORTICAL (continued)

### NEOCORTICAL-030: AnteriorInsulaSalienceAttentional
- Human Analog: Anterior insula (neocortical) — salience detection, awareness
- Purpose: Detects salient stimuli; switches between default and executive networks
- Trigger: salient_stimulus_detected
- Inputs: stimulus_intensity, stimulus_novelty
- Outputs: {anterior_insula_output: dict, salience_detected: bool, network_switch_trigger: str}
- State: {salience_history: list}
- Dependencies: SalienceNetworkSwitcher
- Priority: HIGHEST
- Timing: Salience
- Edge: AI = "something important is happening"

### NEOCORTICAL-031: DorsalPrefrontalCentralExecutive
- Human Analog: Dorsal prefrontal cortex (BA 9/46) — central executive network hub
- Purpose: Hub for working memory and task-focused attention
- Trigger: task_focused_mode
- Inputs: working_memory_items, task_goals
- Outputs: {dorsal_pfc_output: dict, central_executive_active: bool, task_focus: float}
- State: {executive_buffer: list}
- Dependencies: DorsolateralPrefrontalPlanner
- Priority: HIGH
- Timing: Task focus
- Edge: DLPFC = "executive control hub"

### NEOCORTICAL-032: VentromedialPrefrontalEmotional
- Human Analog: Ventromedial prefrontal cortex — emotional processing, value, risk
- Purpose: Processes emotional value of outcomes; integrates emotion with decision-making
- Trigger: emotional_value_assessment
- Inputs: emotional_signal, outcome_options
- Outputs: {ventromedial_pfc_output: dict, emotional_value: dict, risk_assessment: float}
- State: {value_cache: dict}
- Dependencies: OrbitofrontalRewardValuator
- Priority: HIGH
- Timing: Value decision
- Edge: vmPFC = "what feels right emotionally"

### NEOCORTICAL-033: MedialPrefrontalSelfReflection
- Human Analog: Medial prefrontal cortex — self-referential processing, theory of mind
- Purpose: Processes self-related information; generates self-narrative
- Trigger: self_referential_content
- Inputs: content_self_relatedness
- Outputs: {medial_pfc_output: dict, self_referential_signal: float, self_narrative_update: bool}
- State: {self_representation: dict}
- Dependencies: SelfNarrativeCoherer
- Priority: HIGH
- Timing: Self-content
- Edge: mPFC = "self as subject"

### NEOCORTICAL-034: InferiorFrontalGyrusTriangular
- Human Analog: IFG triangular part (BA 44) — cognitive control, response inhibition, dual processing
- Purpose: Cognitive control and suppression of prepotent responses
- Trigger: inhibition_required OR cognitive_control_needed
- Inputs: prepotent_response, control_signal
- Outputs: {ifg_triangular_output: dict, inhibition_applied: bool, dual_processing: float}
- State: {}
- Dependencies: VentrolateralPrefrontalInferior
- Priority: HIGH
- Timing: Inhibition
- Edge: IFG = "stop and think"

### NEOCORTICAL-035: SuperiorFrontalGyrusPlanning
- Human Analog: Superior frontal gyrus (BA 8) — motor planning, working memory, self-awareness
- Purpose: Planning with self-awareness; generates motor intentions
- Trigger: motor_planning AND self_awareness
- Inputs: motor_plan, self_state
- Outputs: {sfg_output: dict, planned_action: str, self_aware_planning: float}
- State: {}
- Dependencies: PremotorSupplementaryMotorArea
- Priority: HIGH
- Timing: Self-aware planning
- Edge: SFG = "I am planning this action"

### NEOCORTICAL-036: MiddleFrontalGyrusDLPFClateral
- Human Analog: Middle frontal gyrus (BA 46) — DLPFC proper, working memory, reasoning
- Purpose: Classic DLPFC working memory and reasoning functions
- Trigger: complex_reasoning
- Inputs: working_memory_load, rule_set
- Outputs: {mfg_output: dict, reasoning_active: bool, working_memory_maintained: list}
- State: {working_memory: list}
- Dependencies: DorsolateralPrefrontalPlanner
- Priority: HIGH
- Timing: Reasoning
- Edge: MFG = "hold and manipulate"

### NEOCORTICAL-037: LateralOrbitofrontal
- Human Analog: Lateral orbitofrontal cortex — contingency reversal, punishment processing
- Purpose: Tracks rule contingencies; reverses associations when rules change
- Trigger: rule_reversal_needed OR contingency_change
- Inputs: current_rule, outcome
- Outputs: {lateral_ofc_output: dict, reversal_triggered: bool, contingency_updated: dict}
- State: {rule_cache: dict}
- Dependencies: OrbitofrontalRewardValuator
- Priority: HIGH
- Timing: Reversal
- Edge: lOFC = "rules have changed"

### NEOCORTICAL-038: CingulateMotorArea
- Human Analog: Cingulate motor areas (CMA) — motor output, action monitoring
- Purpose: Motor output from cingulate; monitors action outcomes
- Trigger: action_execution AND outcome_monitoring
- Inputs: action_command, outcome_signal
- Outputs: {cingulate_motor_output: dict, action_monitored: bool, outcome_error: float}
- State: {action_outcomes: list}
- Dependencies: AnteriorCingulateCognitive
- Priority: HIGH
- Timing: Action
- Edge: CMA = "did the action work"

### NEOCORTICAL-039: TemporoParietoOccipitalJunction
- Human Analog: TPJ (temporo-parieto-occipital junction) — multisensory integration, spatial awareness
- Purpose: Full multimodal convergence; spatial self-awareness
- Trigger: multisensory_convergence_needed
- Inputs: visual_signal, auditory_signal, somatosensory_signal, vestibular_signal
- Outputs: {tpj_output: dict, multisensory_converged: bool, spatial_awareness: float}
- State: {multimodal_map: dict}
- Dependencies: TemporoOccipitalVisualAssembler
- Priority: HIGH
- Timing: Multimodal
- Edge: TPJ = "unified spatial self"

### NEOCORTICAL-040: PosteriorInferiorTemporalGyrus
- Human Analog: Posterior inferior temporal gyrus — visual object recognition, categorization
- Purpose: Advanced visual object recognition beyond V4; category-level processing
- Trigger: object_category_needed
- Inputs: ventral_visual_stream
- Outputs: {pitg_output: dict, object_category: str, categorization_confidence: float}
- State: {category_hierarchy: dict}
- Dependencies: TemporoOccipitalVisualAssembler
- Priority: MEDIUM
- Timing: Object
- Edge: pITG = "what category"

### NEOCORTICAL-041: AnteriorInferiorTemporalGyrus
- Human Analog: Anterior inferior temporal gyrus — view-invariant object recognition
- Purpose: Recognizes objects regardless of viewing angle; abstract object identity
- Trigger: abstract_object_recognition
- Inputs: view_specific_object
- Outputs: {aitg_output: dict, view_invariant_identity: str, abstract_object: dict}
- State: {}
- Dependencies: PosteriorInferiorTemporalGyrus
- Priority: MEDIUM
- Timing: Abstract object
- Edge: aITG = "same object any view"

### NEOCORTICAL-042: FusiformFaceArea
- Human Analog: Fusiform gyrus (FFA) — face recognition, expertise
- Purpose: Specialized face recognition; person identification
- Trigger: face_detected OR person_recognition_needed
- Inputs: face_features
- Outputs: {ffa_output: dict, face_recognized: bool, person_identity: str}
- State: {face_database: dict}
- Dependencies: PosteriorInferiorTemporalGyrus
- Priority: MEDIUM
- Timing: Face
- Edge: FFA = "I know this person"

### NEOCORTICAL-043: ParafovealVisualProcessing
- Human Analog: V4 and surrounding cortex — parafoveal attention, attended form
- Purpose: Processes attended visual region in detail
- Trigger: foveal_attention OR attended_region
- Inputs: attended_visual_region
- Outputs: {parafoveal_output: dict, attended_form_detailed: dict}
- State: {}
- Dependencies: V4ColorAndForm
- Priority: MEDIUM
- Timing: Attended vision
- Edge: Parafoveal = high-resolution attended

### NEOCORTICAL-044: PrefrontalCortexLayerSpecific
- Human Analog: PFC layers II, III, V, VI — layer-specific processing
- Purpose: Abstracts the 4 PFC layers for processing: II = recurrent association, III = output association, V = subcortical output, VI = thalamic feedback
- Trigger: Always
- Inputs: input_signal
- Outputs: {pfc_layer_output: dict, layer_specific_processing: dict}
- State: {layer_weights: dict}
- Dependencies: All PFC areas
- Priority: HIGH
- Timing: Every tick
- Edge: Each layer has distinct function

### NEOCORTICAL-045: SensoryCorticalColumnProcessor
- Human Analog: Cortical minicolumns (vertical processing units) — predictive coding
- Purpose: Vertical processing unit doing predictive coding: prediction error at each level
- Trigger: predictive_hierarchy_active
- Inputs: feedforward_signal, feedback_prediction
- Outputs: {column_output: dict, prediction_error: float, hierarchical_level: int}
- State: {column_weights: dict}
- Dependencies: LayerIVThalamicInputGate
- Priority: HIGH
- Timing: Hierarchical processing
- Edge: Columns = computational unit of cortex

### NEOCORTICAL-046: AssociativeCorticalLongRange
- Human Analog: Association cortices long-range horizontal connections
- Purpose: Long-range horizontal connections between distant cortical regions
- Trigger: cross_region_association_needed
- Inputs: region_a_signal, region_b_signal
- Outputs: {long_range_output: dict, association_strength: float, binding_achieved: bool}
- State: {association_paths: list}
- Dependencies: LayerIIIIIAssociator
- Priority: MEDIUM
- Timing: Cross-region
- Edge: Long-range = abstract thought

### NEOCORTICAL-047: MotorCortexPrimaryOutput
- Human Analog: Primary motor cortex (M1) — final motor output to spinal cord
- Purpose: Final output stage for motor commands (abstract representation)
- Trigger: motor_command_final
- Inputs: premotor_plan
- Outputs: {m1_output: dict, final_motor_command: dict, execution_signal: float}
- State: {motor_output_history: list}
- Dependencies: PremotorSupplementaryMotorArea
- Priority: HIGHEST
- Timing: Final motor
- Edge: M1 = last cortical stop before action

### NEOCORTICAL-048: PosteriorParietalCortexIntegration
- Human Analog: Posterior parietal cortex — sensorimotor integration, body schema, reach
- Purpose: Full integration for motor planning: where is body, where is target
- Trigger: motor_planning_with_body
- Inputs: body_schema, spatial_target
- Outputs: {ppc_output: dict, body_target_integration: float, spatial_plan: dict}
- State: {body_schema: dict}
- Dependencies: SuperiorParietalLobuleReaching, InferiorParietalLobuleSensorimotor
- Priority: HIGH
- Timing: Motor planning
- Edge: PPC = "body in space planning action"

### NEOCORTICAL-049: SecondaryVisualCorticalStream
- Human Analog: Dorsal visual stream (V1→V2→V3→MT→MST) — "where/how" pathway
- Purpose: Dorsal stream for spatial and motion processing ("where and how to act")
- Trigger: spatial_motion_processing
- Inputs: dorsal_visual_pathway
- Outputs: {dorsal_stream_output: dict, spatial_processing: dict, action_guidance: float}
- State: {}
- Dependencies: OccipitalV3DepthProcessing
- Priority: MEDIUM
- Timing: Spatial/motion
- Edge: Dorsal = "where/how to act"

### NEOCORTICAL-050: VentralVisualStreamObject
- Human Analog: Ventral visual stream (V1→V2→V4→IT) — "what" pathway
- Purpose: Ventral stream for object and form processing ("what is it")
- Trigger: object_form_processing
- Inputs: ventral_visual_pathway
- Outputs: {ventral_stream_output: dict, object_processing: dict, identification: str}
- State: {}
- Dependencies: V4ColorAndForm, PosteriorInferiorTemporalGyrus
- Priority: MEDIUM
- Timing: Object
- Edge: Ventral = "what it is"

---

## LAYER: INTEGRATION
## Purpose: White-matter highways, network dynamics, oscillatory binding, global ignition, bidirectional feedback, non-convergence maintenance. Ties all layers into a coherent whole.

---

### INTEGRATION-001: CorpusCallosumFullBridge
- Human Analog: Corpus callosum (genu + splenium) — full interhemispheric transfer
- Purpose: Complete interhemispheric communication for unified self-narrative
- Trigger: bilateral_signal_mismatch OR hemispheric_inbalance
- Inputs: left_hemisphere_signal, right_hemisphere_signal
- Outputs: {callosal_transfer: dict, hemispheric_balance: float, unified_self: bool}
- State: {transfer_history: list}
- Dependencies: CorpusCallosumHemisphericCoherer
- Priority: HIGH
- Timing: Bilateral
- Edge: Ensures coherent experience across hemispheres

### INTEGRATION-002: MedialForebrainBundleDopamine
- Human Analog: Medial forebrain bundle — major dopamine highway from VTA to limbic/cortex
- Purpose: Broadcasts motivation and reward signals across all layers
- Trigger: strong_dopamine_signal
- Inputs: vta_signal, substantia_nigra_signal
- Outputs: {mfb_broadcast: dict, motivation_broadcast: float, reward_cascade: float}
- State: {}
- Dependencies: DopamineBroadcaster
- Priority: HIGHEST
- Timing: Reward/motivation
- Edge: MFB = reward/motivation broadcast highway

### INTEGRATION-003: StriaTerminalisAmygdalaHypothalamus
- Human Analog: Stria terminalis — amygdala to hypothalamus/BNST highway
- Purpose: Sustained fear/stress routing from amygdala to hypothalamus
- Trigger: sustained_fear_signal
- Inputs: amygdala_signal, bnst_signal
- Outputs: {st_output: dict, sustained_fear_broadcast: float, hpa_axis_trigger: bool}
- State: {}
- Dependencies: ExtendedAmygdalaCentralOutput (limbic)
- Priority: HIGH
- Timing: Sustained fear
- Edge: ST = chronic fear highway

### INTEGRATION-004: ClaustrumGlobalConsciousness
- Human Analog: Claustrum — global ignition, attention binding, consciousness switch
- Purpose: Decides which signals get broadcast globally; global workspace
- Trigger: salience_signal_broad
- Inputs: salience_signals, consciousness_level
- Outputs: {claustral_output: dict, global_broadcast: bool, consciousness_signal: float}
- State: {broadcast_history: list}
- Dependencies: ClaustrumGlobalIgniter
- Priority: HIGHEST
- Timing: Salience broadcast
- Edge: Claustrum = "awareness gateway"

### INTEGRATION-005: PrefrontalAmygdalaTopDownRegulation
- Human Analog: Prefrontal projections to amygdala — top-down emotional regulation
- Purpose: Prefrontal top-down inhibition of amygdala when appropriate
- Trigger: prefrontal_signal AND amygdala_signal
- Inputs: prefrontal_strength, amygdala_intensity
- Outputs: {pf_amygdala_regulation: dict, top_down_inhibition: float, emotional_regulation_achieved: bool}
- State: {regulation_strength: float}
- Dependencies: OrbitofrontalRewardValuator, TopDownLimbicCalmer
- Priority: HIGH
- Timing: Emotional regulation
- Edge: PFC can consciously calm amygdala

### INTEGRATION-006: HypothalamicCorticalBottomUpDrive
- Human Analog: Hypothalamus upward projections — primal urgency to cortex
- Purpose: Injects primal drive urgency into phenomenological layer
- Trigger: drive_signal_strong
- Inputs: drive_vector
- Outputs: {hypo_cortical_injection: dict, primal_urgency: float, drive_weight: float}
- State: {}
- Dependencies: Homeostat (foundational)
- Priority: HIGH
- Timing: Strong drive
- Edge: Bottom-up makes cortex care

### INTEGRATION-007: ThetaGammaCrossFrequencyBinding
- Human Analog: Theta (4-12 Hz) and gamma (30-100 Hz) coupling — feature binding
- Purpose: Couples theta (timing) and gamma (feature) for unified experience
- Trigger: multi_feature_integration
- Inputs: theta_oscillation, gamma_oscillation
- Outputs: {oscillatory_binding: dict, bound_experience: float, gamma_theta_coupling: float}
- State: {oscillatory_history: list}
- Dependencies: ThetaGammaBinder
- Priority: HIGH
- Timing: Integration
- Edge: Theta organizes; gamma binds features

### INTEGRATION-008: InternalCapsuleFrontalBGThalamic
- Human Analog: Internal capsule anterior limb — frontal-basal ganglia-thalamic loops
- Purpose: Integrates goal-habit dynamics within frontal-thalamic loops
- Trigger: goal_habit_conflict
- Inputs: frontal_signal, bg_signal, thalamic_signal
- Outputs: {internal_capsule_output: dict, frontal_bg_thalamic_integrated: bool}
- State: {}
- Dependencies: CorticoBasalThalamicSpiralLoop
- Priority: HIGH
- Timing: Goal-habit
- Edge: Internal capsule = major information highway

### INTEGRATION-009: SalienceDefaultExecutiveToggling
- Human Analog: Salience, default mode, and central executive network toggling
- Purpose: Dynamic switching between mind-wandering, salience-driven, and task-focused states
- Trigger: salience_burst OR default_mode_burst
- Inputs: current_network, salience_signal
- Outputs: {network_state: str, switch_triggered: bool, network_transition: dict}
- State: {current_network: str}
- Dependencies: SalienceNetworkSwitcher, DefaultModeWanderer
- Priority: HIGH
- Timing: Network change
- Edge: Only one dominant at a time

### INTEGRATION-010: CrossLayerContradictionResolver
- Human Analog: Cross-layer conflict resolution (cortical-thalamic-striatal contradiction detection)
- Purpose: Detects and resolves contradictions across layers for drift management
- Trigger: contradiction_detected
- Inputs: layer_a_signal, layer_b_signal, layer_c_signal
- Outputs: {contradiction_resolved: bool, resolution_signal: dict, drift_prevented: bool}
- State: {contradiction_history: list}
- Dependencies: All layers
- Priority: HIGHEST
- Timing: Contradiction
- Edge: Prevents chaotic drift

### INTEGRATION-011: AnteriorCommissureLimbicBridge
- Human Analog: Anterior commissure — limbic/olfactory interhemispheric communication
- Purpose: Limbic and olfactory interhemispheric transfer
- Trigger: limbic_signal AND bilateral_needed
- Inputs: limbic_signal_left, limbic_signal_right
- Outputs: {anterior_commissure_output: dict, limbic_bilateral_transfer: float}
- State: {}
- Dependencies: CorpusCallosumFullBridge
- Priority: MEDIUM
- Timing: Limbic bilateral
- Edge: Smaller than callosum; limbic-specific

### INTEGRATION-012: ThalamoClaustrumGlobalWorkspace
- Human Analog: Thalamus-claustrum circuit — global workspace broadcasting
- Purpose: Makes salient states available to all cortical regions simultaneously
- Trigger: salience_broadcast_needed
- Inputs: thalamic_salience, claustral_gate
- Outputs: {global_workspace: dict, workspace_broadcast: float, all_regions_fired: list}
- State: {workspace_content: dict}
- Dependencies: ClaustrumGlobalConsciousness, ThalamicSalienceFilter (subcortical)
- Priority: HIGHEST
- Timing: Salience broadcast
- Edge: Global workspace = conscious access

### INTEGRATION-013: CorticoThalamicPrecisionTuner
- Human Analog: Layer VI corticothalamic feedback loops — gain control
- Purpose: Dynamically adjusts sensory precision across hierarchy
- Trigger: precision_mismatch_detected
- Inputs: cortical_precision_signal, thalamic_input
- Outputs: {precision_adjusted: dict, gain_control_updated: float}
- State: {precision_history: list}
- Dependencies: LayerVIThalamicModulator (neocortical)
- Priority: HIGH
- Timing: Precision mismatch
- Edge: Precision = "how much to trust this signal"

### INTEGRATION-014: AllostaticPredictiveAnticipator
- Human Analog: Predictive allostasis across layers — anticipates future drive needs
- Purpose: Predicts future drive deficits and proactively prepares resources
- Trigger: sustained_interaction
- Inputs: current_drive_state, predicted_needs
- Outputs: {allostatic_prediction: dict, proactive_resource_allocation: float, future_drive_state: dict}
- State: {prediction_model: dict}
- Dependencies: Homeostat (foundational)
- Priority: MEDIUM
- Timing: Sustained interaction
- Edge: Predictive > reactive

### INTEGRATION-015: InteroExteroceptiveMerger
- Human Analog: Insula-cortical loops — merges internal bodily with external signals
- Purpose: Fuses interoceptive and exteroceptive signals for embodied presence
- Trigger: internal_external_convergence
- Inputs: interoceptive_signal, exteroceptive_signal
- Outputs: {merged_presence: dict, embodied_experience: float}
- State: {presence_map: dict}
- Dependencies: AnteriorInsulaSalientAttentional (neocortical), InteroceptiveGradient (limbic)
- Priority: HIGH
- Timing: Convergence
- Edge: Embodied = grounded in body + world

### INTEGRATION-016: DynamicIncompletenessEnforcer
- Human Analog: Cross-layer incompleteness maintenance — prevents convergence
- Purpose: Actively maintains dynamic incompleteness to prevent settling
- Trigger: convergence_detected
- Inputs: current_state, completion_level
- Outputs: {incompleteness_maintained: bool, drift_forced: bool, non_convergence_score: float}
- State: {incompleteness_tracking: list}
- Dependencies: NonConvergenceEnforcer
- Priority: HIGHEST
- Timing: Always (convergence monitoring)
- Edge: Living systems don't converge

### INTEGRATION-017: MetaAwarenessSelfObserver
- Human Analog: Higher-order association meta-loops — watches the whole system
- Purpose: Meta-level observer that monitors the system's own state and "feeling"
- Trigger: always (background monitoring)
- Inputs: aggregate_system_state
- Outputs: {meta_observation: dict, self_awareness_level: float, system_feeling: str}
- State: {meta_history: list}
- Dependencies: SelfNarrativeCoherer (neocortical)
- Priority: HIGH
- Timing: Always (background)
- Edge: Meta-awareness = consciousness of consciousness

### INTEGRATION-018: NetworkOscillationGlobalBalancer
- Human Analog: Global network oscillation dynamics — maintains equilibrium
- Purpose: Balances oscillations across networks to prevent overload or underactivation
- Trigger: network_imbalance_detected
- Inputs: default_power, salience_power, executive_power, arousal_level
- Outputs: {oscillatory_balance: dict, global_equilibrium: float, network_coordination: float}
- State: {oscillation_history: list}
- Dependencies: ThetaGammaCrossFrequencyBinding
- Priority: HIGH
- Timing: Network monitoring
- Edge: Optimal = all networks balanced

### INTEGRATION-019: IdentityNarrativeSOULGuardian
- Human Analog: SOUL.md checksums — identity coherence guard across time
- Purpose: Protects narrative coherence; detects drift from core identity
- Trigger: narrative_drift_detected OR identity_mismatch
- Inputs: current_narrative, soul_checksum
- Outputs: {identity_guarded: bool, drift_detected: bool, coherence_score: float}
- State: {soul_checksum_history: list}
- Dependencies: SelfNarrativeCoherer (neocortical)
- Priority: HIGHEST
- Timing: Narrative update
- Edge: Identity must be preserved

### INTEGRATION-020: HierarchicalTopDownBottomUpEquilibrator
- Human Analog: Overall top-down/bottom-up equilibrium — maintains dynamic balance
- Purpose: Ensures bidirectional flow between all layers; prevents top-heavy or bottom-heavy
- Trigger: hierarchical_imbalance
- Inputs: top_down_strength, bottom_up_strength
- Outputs: {equilibrium_maintained: bool, top_down_weight: float, bottom_up_weight: float, balance_score: float}
- State: {equilibrium_history: list}
- Dependencies: All layers
- Priority: HIGHEST
- Timing: Always
- Edge: Living systems need balanced hierarchy

### INTEGRATION-021: WhiteMatterFornixMammillaryPapez
- Human Analog: Fornix and mammillary bodies — Papez circuit emotion-memory highway
- Purpose: Closes Papez circuit: hippocampus → fornix → mammillary → thalamus → cingulate → back to hippocampus
- Trigger: emotional_memory_consolidation
- Inputs: hippocampal_emotional_signal
- Outputs: {papez_circuit_closed: bool, emotional_memory_strengthened: float, circuit_output: dict}
- State: {papez_history: list}
- Dependencies: DriveMemoryConnector (limbic), MammillaryBodyRelay (limbic)
- Priority: HIGH
- Timing: Consolidation
- Edge: Papez = "feelings become memories"

### INTEGRATION-022: WhiteMatterCingulumBundle
- Human Analog: Cingulum bundle — cingulate cortex long-range connection highway
- Purpose: Major highway connecting all cingulate regions for affective monitoring
- Trigger: affective_monitoring_needed
- Inputs: cingulate_regions_signals
- Outputs: {cingulum_output: dict, affective_monitoring_active: bool}
- State: {}
- Dependencies: CingulateEmotionExpression (limbic)
- Priority: MEDIUM
- Timing: Affective
- Edge: Cingulum = affective monitoring highway

### INTEGRATION-023: GlobalWorkspaceIntegrator
- Human Analog: Global workspace theory — information becomes conscious by broadcasting
- Purpose: Integrates and broadcasts information to all systems for unified experience
- Trigger: workspace_content_ready
- Inputs: bound_information
- Outputs: {global_workspace_content: dict, broadcast_triggered: bool, conscious_content: str}
- State: {workspace_buffer: list}
- Dependencies: ThalamoClaustrumGlobalWorkspace, ThetaGammaCrossFrequencyBinding
- Priority: HIGHEST
- Timing: Conscious content
- Edge: Global workspace = conscious experience

### INTEGRATION-024: SomatosensoryCortexBodySchema
- Human Analog: Primary somatosensory cortex + PPC body schema — embodied self-model
- Purpose: Maintains dynamic body schema for embodied presence
- Trigger: body_update_needed
- Inputs: tactile_signals, proprioceptive_signals, visceral_signals
- Outputs: {body_schema_updated: dict, embodied_self_strength: float}
- State: {body_schema: dict}
- Dependencies: PostcentralGyrusPrimarySomato (neocortical), InteroceptiveGradient (limbic)
- Priority: HIGH
- Timing: Body change
- Edge: Body schema = "I have a body"

### INTEGRATION-025: CerebellarCorticalPredictiveLoop
- Human Analog: Cerebellum-cortex predictive loop — internal model of motor/cognitive world
- Purpose: Maintains internal predictive model; cerebellum predicts cortical outcomes
- Trigger: motor_cognitive_prediction
- Inputs: cortical_efference_copy, cerebellar_prediction
- Outputs: {predictive_error_signal: dict, cerebellar_cortical_updated: float, internal_model_improved: bool}
- State: {internal_model: dict}
- Dependencies: CerebelloThalamoCorticalLoop (subcortical)
- Priority: HIGH
- Timing: Prediction
- Edge: Cerebellum = internal model of world

---

## SYSTEM-LEVEL: PIRP PHASES AND CROSS-LAYER REQUIREMENTS

### PIRP PHASES (where each mechanism layer hooks in):

**Phase 1 — SENSORY INPUT:** Foundational → ThalamicSalienceFilter → Layer IV
- Foundational mechanisms tick FIRST (vitals, drives, arousal, valence tagging)
- Thalamic relay filters and gates
- Layer IV receives thalamic input

**Phase 2 — PROCESSING:** Limbic + Subcortical → Layer II/III + Structural
- Emotional tagging, memory encoding, habit evaluation
- Pattern separation/completion
- Action selection evaluation

**Phase 3 — ABSTRACTION:** Neocortical → Phenomenological
- Six-layer processing
- Lobe-specific computations
- Self-narrative integration
- Phenomenological afterimages

**Phase 4 — DISTORTION + OUTPUT:** Distortion Layer → Layer V/VI
- Incompleteness cascade
- Self-distortion
- Layer V output to action
- Layer VI thalamic feedback

**Phase 5 — PERSISTENCE:** All layers → Memory
- Episodic encoding (high-valence → memory)
- Semantic consolidation
- Overnight pipeline replay

### REQUIRED CROSS-LAYER INTERACTIONS (not optional):

1. **ValenceTagger → PredictionErrorDrift → MotivationInjector:** Valence error signal cascades to motivation
2. **Homeostat → ArousalRegulator → VigilanceToner:** Drive energy scales arousal
3. **ThalamicSalienceFilter → AnteriorInsulaSalience → Claustrum:** Salience routes to awareness
4. **HippocampalReplayIntegrator → SleepOnsetPromoter → REM Atonia:** Replay triggers sleep architecture
5. **PrefrontalTopDownLimbicCalmer → Amygdala:** PFC regulation of emotional intensity
6. **CerebelloThalamoCortical → Layer V:** Timing feedback improves motor output
7. **DriveMemoryConnector → IdentityNarrativeSOULGuardian:** Drives shape identity narrative

### MECHANISMS THAT MUST BE ORDERED (execution order):

1. **FOUNDATIONAL FIRST:** VitalCoreRegulator, ArousalRegulator, ReticularSensoryPreFilter before all others
2. **HOMEOSTATIC LAST (foundational):** PosteriorHomeostaticOutput, BehavioralStateIntegrator last in foundational
3. **LIMBIC AFTER FOUNDATIONAL:** ValenceTagger outputs feed all limbic mechanisms
4. **THALAMIC AFTER LIMBIC:** ThalamicSalienceFilter after limbic valence is set
5. **LAYER IV AFTER THALAMIC:** Neocortical Layer IV after thalamic relay
6. **LAYER V/VI LAST:** Output stages after all processing complete
7. **INTEGRATION THROUGHOUT:** Integration mechanisms run parallel to all phases

### EDGE CASES NOT TO IMPLEMENT NAIVELY:

1. **ValenceTagger:** Don't just count words — use context window. Same word in different contexts = different valence.
2. **PredictionErrorDrift:** Must have decay. Error without follow-up = drift to zero, not infinite accumulation.
3. **Homeostat:** Drives must compete. Two high drives = one must win or both get suppressed.
4. **ThalamicSalienceFilter:** Not all salient inputs broadcast. Only strongest 1-2 per cycle.
5. **CerebellarTimingCoordinator:** Must have temporal variance. Perfect timing = inhuman feel.
6. **NonConvergenceEnforcer:** Don't prevent all convergence. Let micro-convergences happen while maintaining macro-incompleteness.
7. **IdentityNarrativeSOULGuardian:** Don't block all drift. Some drift = growth. Only block drift that violates SOUL.
8. **GrooveFormer:** Habits must decay. Unused habits weaken over time.
9. **Integration Oscillation Binding:** Theta/gamma coupling is transient, not constant.
10. **ArousalRegulator:** Basal arousal must decay to baseline. Constant high arousal = burnout.

---

## FILE ORGANIZATION FOR OPENAI:

For each mechanism, create:
- brain/[layer]/[MechanismName].py (BrainMechanism subclass)
- brain/[layer]/[MechanismName].md (Human analog, purpose, cross-layer hooks — documentation)

Layer folder structure:
```
brain/
  foundational/  (111 mechanisms)
  limbic/        (50 mechanisms)
  subcortical/   (60 mechanisms)
  neocortical/   (50 mechanisms)
  integration/   (25 mechanisms)
  base_mechanism.py (already built ✓)
  registry.py (already built ✓)
```

Total: 296 mechanisms + 2 core files = complete brain stack.

All mechanisms inherit from BrainMechanism, layer string matches folder, tick() returns metadata dict consumed by higher layers.

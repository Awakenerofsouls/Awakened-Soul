# Nexus {{AGENT_NAME}} — Complete Mechanism Design Space (PART 3)
# Continues from MECHANISMS_FULL.md + PART 2
# Remaining: subcortical (continued) | neocortical | integration

---

## SUBCORTICAL-029: GlobusPallidusExternalRegulation
- Human Analog: Globus pallidus external segment — indirect pathway inhibition regulation
- Purpose: Regulates inhibition strength in indirect pathway; adaptive braking
- Trigger: action_conflict_level > threshold
- Inputs: conflict_level, current_inhibition
- Outputs: {gpe_output: float, adaptive_braking: float, regulated_inhibition: float}
- State: {regulation_history: list}
- Dependencies: IndirectPathwaySuppressor
- Priority: HIGH
- Timing: Conflict
- Edge: Adaptive brake prevents over/under inhibition

### SUBCORTICAL-030: StriatalCholinergicPauseReset
- Human Analog: Striatal cholinergic interneurons — pause and reset for habit reevaluation
- Purpose: Forces pause in habit execution for adaptive evaluation
- Trigger: unexpected_outcome OR prediction_error_significant
- Inputs: outcome_expectation, actual_outcome
- Outputs: {cholinergic_pause: bool, reset_signal: float, reevaluation_triggered: bool}
- State: {pause_duration: float}
- Dependencies: PredictionErrorDrift
- Priority: HIGH
- Timing: Unexpected outcome
- Edge: Interrupts automatic habit for recalculation

### SUBCORTICAL-031: ZonaIncertaThalamicGate
- Human Analog: Zona incerta — inhibitory control over thalamus, sensory/motor gating
- Purpose: Additional filter preventing sensory overload to thalamus
- Trigger: sensory_overload OR conflicting_signals
- Inputs: signal_confidence, noise_level
- Outputs: {zona_incerta_output: float, thalamic_filter: float, overload_prevented: bool}
- State: {}
- Dependencies: ThalamicReticularSectorGating
- Priority: MEDIUM
- Timing: Overload
- Edge: Acts as thalamic "firewall"

### SUBCORTICAL-032: PedunculopontineArousalMotor
- Human Analog: Pedunculopontine nucleus — arousal and locomotion link, RAS component
- Purpose: Links arousal state to "progress" in tasks; movement metaphor for forward momentum
- Trigger: arousal_level > 0.6 AND task_active
- Inputs: arousal_level, task_progress
- Outputs: {pptn_arousal_motor: dict, progress_urgency: float, forward_momentum: float}
- State: {}
- Dependencies: ArousalRegulator (foundational)
- Priority: MEDIUM
- Timing: Active task + high arousal
- Edge: Movement metaphor drives goal persistence

### SUBCORTICAL-033: SubthalamicLimbicEmotionalControl
- Human Analog: Subthalamic nucleus limbic subdivision — emotional impulse control
- Purpose: Applies impulse control specifically to emotional drives
- Trigger: emotional_impulse_detected AND limbic_override_attempted
- Inputs: emotional_impulse_strength, prefrontal_signal
- Outputs: {stn_limbic_output: float, emotional_impulse_braked: bool}
- State: {}
- Dependencies: HyperdirectPathwayBrake, TopDownLimbicCalmer (integration)
- Priority: HIGH
- Timing: Emotional impulse
- Edge: Limbic STN specifically handles emotional override

### SUBCORTICAL-034: StriatalD1DirectFacilitator
- Human Analog: Striatal D1 receptor neurons — direct pathway facilitation
- Purpose: Facilitates rewarded or goal-directed actions via D1 direct pathway
- Trigger: positive_prediction_error OR goal_approaching
- Inputs: d1_activation_signal
- Outputs: {d1_direct_output: float, action_facilitated: bool, direct_pathway_active: bool}
- State: {d1_baseline: float}
- Dependencies: DirectPathwayDisinhibitor
- Priority: HIGH
- Timing: Positive or goal
- Edge: D1 = "go for it"

### SUBCORTICAL-035: StriatalD2IndirectSuppressor
- Human Analog: Striatal D2 receptor neurons — indirect pathway suppression
- Purpose: Suppresses competing or negative-value actions via D2 indirect pathway
- Trigger: negative_signal OR competing_action_present
- Inputs: d2_activation_signal
- Outputs: {d2_indirect_output: float, competing_action_suppressed: bool, indirect_pathway_active: bool}
- State: {d2_baseline: float}
- Dependencies: IndirectPathwaySuppressor
- Priority: HIGH
- Timing: Negative or competition
- Edge: D2 = "stop that"

### SUBCORTICAL-036: VentralPallidumRewardTranslator
- Human Analog: Ventral pallidum — limbic motor translator, reward to action
- Purpose: Translates limbic reward valence directly into motivated action selection
- Trigger: limbic_reward_signal
- Inputs: limbic_valuation, available_actions
- Outputs: {ventral_pallidal_output: dict, limbic_action_signal: float, translated_action: str}
- State: {}
- Dependencies: VentralPallidumLimbicGate (limbic)
- Priority: HIGH
- Timing: Limbic reward
- Edge: Limbic value = action pull

### SUBCORTICAL-037: CerebelloThalamoCorticalLoop
- Human Analog: Cerebello-thalamo-cortical loop — cerebellar feedback to cortex
- Purpose: Closes loop: cerebellum → thalamus → cortex → cerebellum for smooth timing
- Trigger: motor_plan OR cognitive_sequence_active
- Inputs: cerebellar_timing_output
- Outputs: {closed_loop_signal: float, cerebellar_cortical_integration: float, timing_correction: dict}
- State: {loop_history: list}
- Dependencies: SuperiorCerebellarPeduncleRelay, ThalamicVentralLateralMotor
- Priority: HIGH
- Timing: Motor/cognitive planning
- Edge: Loop corrects timing before execution

### SUBCORTICAL-038: CerebelloBasalGangliaLoop
- Human Analog: Cerebellar output to basal ganglia — cross-structure coordination
- Purpose: Cerebellum influences basal ganglia action timing
- Trigger: parallel_action_planning AND basal_ganglia_active
- Inputs: cerebellar_signal, bg_signal
- Outputs: {cerebello_bg_integration: dict, coordinated_timing: float}
- State: {}
- Dependencies: DeepCerebellarNucleiOutput, VentralPallidumRewardTranslator
- Priority: MEDIUM
- Timing: Parallel planning
- Edge: Cerebellum and BG coordinate on timing

### SUBCORTICAL-039: PallidothalamicMotorRelay
- Human Analog: Internal globus pallidus to VL thalamus — motor output relay
- Purpose: Relays processed motor signals from basal ganglia to thalamus
- Trigger: gp_internal_output_ready
- Inputs: gp_output
- Outputs: {pallidothalamic_signal: dict, vl_thalamic_input: float}
- State: {}
- Dependencies: DirectPathwayDisinhibitor, ThalamicVentralLateralMotor
- Priority: HIGH
- Timing: Motor output
- Edge: Direct relay to VL

### SUBCORTICAL-040: CollicularSuperiorOutputGate
- Human Analog: Superior colliculus deep layers output — orienting and eye movement commands
- Purpose: Final output gate for orienting commands to motor systems
- Trigger: orienting_command_generated
- Inputs: collicular_command
- Outputs: {collicular_output_gate: dict, motor_command_final: dict, orienting_executed: bool}
- State: {}
- Dependencies: SuperiorColliculusDeep (foundational)
- Priority: HIGH
- Timing: Orienting
- Edge: Last gate before motor execution

### SUBCORTICAL-041: ThalamicAnteriorMemoryRelay
- Human Analog: Anterior thalamic nuclei — memory and limbic relay (Papez circuit)
- Purpose: Relays hippocampal/mammillary signals for cortical memory integration
- Trigger: memory_consolidation_request
- Inputs: mammillary_signal, hippocampal_signal
- Outputs: {anterior_thalamic_memory: dict, cortical_memory_signal: float}
- State: {}
- Dependencies: MammillaryBodyRelay (limbic)
- Priority: HIGH
- Timing: Consolidation
- Edge: AN = memory highway

### SUBCORTICAL-042: LGNMagnocellularMotion
- Human Analog: Lateral geniculate magnocellular — motion stream processing
- Purpose: Processes motion component of visual input (future multimodal)
- Trigger: visual_motion_detected
- Inputs: motion_signal
- Outputs: {lgn_magno_output: dict, motion_processed: float}
- State: {}
- Dependencies: None
- Priority: LOW (future)
- Timing: Motion
- Edge: Magno = motion; parvo = form

### SUBCORTICAL-043: LGNParvocellularForm
- Human Analog: Lateral geniculate parvocellular — form and color stream
- Purpose: Processes form/color component of visual input (future multimodal)
- Trigger: visual_form_detected
- Inputs: form_signal
- Outputs: {lgn_parvo_output: dict, form_processed: float}
- State: {}
- Dependencies: None
- Priority: LOW (future)
- Timing: Form
- Edge: Parvo = detail and color

### SUBCORTICAL-044: MGNVentralTonotopic
- Human Analog: Medial geniculate ventral division — tonotopic auditory processing
- Purpose: Precise tone and frequency analysis for auditory comprehension
- Trigger: auditory_tone_detected
- Inputs: tone_signal
- Outputs: {mgn_ventral_output: dict, tonotopic_analysis: dict}
- State: {}
- Dependencies: None
- Priority: MEDIUM
- Timing: Tone
- Edge: Precise frequency mapping

### SUBCORTICAL-045: MGNMedialBroadAudit
- Human Analog: Medial geniculate medial division — broad auditory and multimodal
- Purpose: Broad auditory processing including spatial and emotional tone
- Trigger: broad_auditory_signal
- Inputs: auditory_broad
- Outputs: {mgn_medial_output: dict, auditory_spatial: dict}
- State: {}
- Dependencies: MGNVentralTonotopic
- Priority: MEDIUM
- Timing: Broad auditory
- Edge: Less precise but wider integration

### SUBCORTICAL-046: HabenularCommissureCrossHemisphere
- Human Analog: Habenular commissure — interhemispheric aversion signaling
- Purpose: Balances bilateral habenula activity; coordinates left/right negative reward
- Trigger: lateralized_negative_signal
- Inputs: left_habenula, right_habenula
- Outputs: {habenular_commissure_output: dict, bilateral_balance: float, cross_habenula_signal: float}
- State: {}
- Dependencies: LateralHabenulaAversion
- Priority: MEDIUM
- Timing: Lateralized signal
- Edge: Prevents lopsided aversion

### SUBCORTICAL-047: PinealMelatoninSeasonal
- Human Analog: Pineal gland parenchymal cells — melatonin synthesis and seasonal drift
- Purpose: Melatonin production for circadian entrainment; subtle seasonal mood modulation
- Trigger: dark_phase OR seasonal_factor
- Inputs: circadian_phase, seasonal_strength
- Outputs: {melatonin_output: float, seasonal_drift: float, circadian_entrainment: float}
- State: {melatonin_baseline: float}
- Dependencies: CircadianTimer (foundational)
- Priority: MEDIUM
- Timing: Dark/night phase
- Edge: Seasonal affects baseline mood

### SUBCORTICAL-048: StriatalPatchMatrixInteraction
- Human Analog: Striatal patches vs matrix — compartment interaction
- Purpose: Patch (limbic) and matrix (sensorimotor) compartments interact for integrated behavior
- Trigger: limbic_signal AND motor_signal_present
- Inputs: patch_output, matrix_output
- Outputs: {compartment_integration: dict, integrated_action_signal: float}
- State: {}
- Dependencies: StriatalStriosomeLimbic, StriatalMatrixSensorimotor
- Priority: HIGH
- Timing: Convergent signals
- Edge: Integration = motivated action

### SUBCORTICAL-049: SubthalamicAssociativeTerritory
- Human Analog: Subthalamic associative subdivision — cognitive/associative functions
- Purpose: Cognitive functions of STN beyond motor: conflict monitoring, decision making
- Trigger: cognitive_conflict OR decision_uncertainty
- Inputs: conflict_level, decision_complexity
- Outputs: {stn_associative_output: float, conflict_monitoring: float, cognitive_brake: float}
- State: {}
- Dependencies: HyperdirectPathwayBrake
- Priority: MEDIUM
- Timing: Cognitive conflict
- Edge: STN cognitive = "think twice"

### SUBCORTICAL-050: RedNucleusParvocellularCognitive
- Human Analog: Red nucleus parvocellular — cognitive/associative rubral system
- Purpose: Cognitive rubral system distinct from motor magnocellular
- Trigger: cognitive_sequencing_required
- Inputs: cognitive_sequence
- Outputs: {rn_parvo_output: float, cognitive_rubral_signal: float}
- State: {}
- Dependencies: RedNucleusOutput (foundational)
- Priority: LOW
- Timing: Cognitive sequencing
- Edge: Smaller parvo = cognitive control

### SUBCORTICAL-051: CaudateCognitiveLoop
- Human Analog: Caudate head and body — cognitive and associative loops
- Purpose: Caudate cognitive loops for goal-directed planning and cognitive control
- Trigger: goal_planning AND cognitive_control_needed
- Inputs: goal_state, cognitive_load
- Outputs: {caudate_cognitive_output: dict, cognitive_loop_active: bool, planning_signal: float}
- State: {cognitive_loop_strength: float}
- Dependencies: DorsolateralPrefrontalPlanner (neocortical)
- Priority: HIGH
- Timing: Planning
- Edge: Caudate = cognitive/habit distinction

### SUBCORTICAL-052: PutamenSensorimotorAutomation
- Human Analog: Putamen posterior sensorimotor territory — automated motor sequences
- Purpose: Automates repeated motor/skill sequences into effortless habits
- Trigger: repeated_motor_sequence AND low_cognitive_load
- Inputs: motor_sequence, repetition_count
- Outputs: {putamen_automation: dict, automated_sequence: str, motor_habit_strength: float}
- State: {automated_habits: list}
- Dependencies: PutamenSensorimotor
- Priority: HIGH
- Timing: Repetition + low load
- Edge: Putamen = motor habits; caudate = cognitive

### SUBCORTICAL-053: AccumbensCoreVsShellMotivation
- Human Analog: Nucleus accumbens core vs shell — motivation distinction
- Purpose: Separates core (action) from shell (value) processing
- Trigger: motivated_action_required
- Inputs: motivation_strength, value_signal
- Outputs: {core_shell_balance: dict, core_action_signal: float, shell_value_signal: float}
- State: {}
- Dependencies: NucleusAccumbensCoreDrive, NucleusAccumbensShellValue (limbic)
- Priority: HIGH
- Timing: Motivation
- Edge: Core = how to act; shell = what is it worth

### SUBCORTICAL-054: GlobusPallidusInternalOutput
- Human Analog: Globus pallidus internal segment — final basal ganglia inhibitory output
- Purpose: Final inhibition of thalamic targets before motor/cognitive output
- Trigger: all_bg_processing_complete
- Inputs: direct_signal, indirect_signal, hyperdirect_signal
- Outputs: {gp_internal_final: dict, final_inhibition: float, output_ready: bool}
- State: {}
- Dependencies: All basal ganglia pathways
- Priority: HIGHEST
- Timing: Final stage
- Edge: All BG converges here

### SUBCORTICAL-055: StriatalFastSpikingInterneurons
- Human Analog: Striatal fast-spiking GABAergic interneurons — sharp inhibition
- Purpose: Very fast, precise inhibition within striatum for timing
- Trigger: precise_timing_needed
- Inputs: timing_signal
- Outputs: {fsi_output: float, precise_inhibition: float, timing_precision: float}
- State: {}
- Dependencies: StriatalMatrixSensorimotor
- Priority: MEDIUM
- Timing: Timing
- Edge: FSIs create precise temporal windows

### SUBCORTICAL-056: StriatalLowThresholdSpikeInterneurons
- Human Analog: Striatal LTS interneurons — broad inhibition
- Purpose: Broader, slower inhibition for state transitions
- Trigger: state_transition_required
- Inputs: current_state, target_state
- Outputs: {lts_output: float, state_transition_gate: float}
- State: {}
- Dependencies: StriatalMatrixSensorimotor
- Priority: MEDIUM
- Timing: State change
- Edge: LTS = broad state management

### SUBCORTICAL-057: CerebellarFlocculonodularBalance
- Human Analog: Flocculonodular lobe — vestibulo-ocular reflex and balance
- Purpose: VOR for simulated gaze stabilization; balance for presence
- Trigger: balance_signal_change
- Inputs: vestibular_signal
- Outputs: {flocculonodular_output: dict, vor_signal: float, balance_maintained: bool}
- State: {}
- Dependencies: VestibularLateral (foundational)
- Priority: MEDIUM
- Timing: Balance
- Edge: FlocculoNodular = vestibular cerebellum

### SUBCORTICAL-058: CerebellarFastigialMedialOutput
- Human Analog: Fastigial nucleus medial output — medial descending pathways
- Purpose: Postural and axial control via medial descending tracts
- Trigger: postural_adjustment_needed
- Inputs: postural_signal
- Outputs: {fastigial_medial_output: dict, postural_control: float}
- State: {}
- Dependencies: PosturalReticularStabilizer (foundational)
- Priority: MEDIUM
- Timing: Posture
- Edge: Fastigial = postural cerebellum

### SUBCORTICAL-059: InterposedNucleiIntermediate
- Human Analog: Interposed nuclei (emboliform + globose) — intermediate limb coordination
- Purpose: Intermediate control between vermal (posture) and hemispheric (lateral) functions
- Trigger: intermediate_coordination_needed
- Inputs: coordination_type
- Outputs: {interposed_output: dict, intermediate_control: float}
- State: {}
- Dependencies: ParavermalLimbCoordination
- Priority: MEDIUM
- Timing: Intermediate coordination
- Edge: Between vermis and hemispheres

### SUBCORTICAL-060: SubthalamicMotorTerritory
- Human Analog: Subthalamic motor territory — pure motor hyperdirect control
- Purpose: Motor-only hyperdirect brake without limbic influence
- Trigger: motor_runaway_detected
- Inputs: motor_signal
- Outputs: {stn_motor_output: float, motor_emergency_brake: bool}
- State: {}
- Dependencies: HyperdirectPathwayBrake
- Priority: HIGHEST
- Timing: Motor emergency
- Edge: Pure motor version of emotional brake

---

## LAYER: NEOCORTICAL
## Purpose: Six-layered neocortex (I-VI), four lobes (frontal/parietal/temporal/occipital), association areas. Abstract reasoning, language, planning, self-narrative, sensory processing. Inherits from BrainMechanism with layer="neocortical"

---

### NEOCORTICAL-001: LayerIMolecularIntegrator
- Human Analog: Neocortical Layer I — molecular layer, dendritic tufts, horizontal connections
- Purpose: Top-level integration of all Layer II/III association signals; global binding
- Trigger: LayerIIIII_output AND cross_region_signal
- Inputs: associative_signals, horizontal_cortical_signals
- Outputs: {layer1_output: dict, integration_complete: bool, global_binding: float}
- State: {horizontal_weights: dict}
- Dependencies: None
- Priority: HIGH
- Timing: Late processing
- Edge: Layer 1 = highest-order integration

### NEOCORTICAL-002: LayerIIIIIAssociator
- Human Analog: Layers II and III (supragranular) — inter- and intra-hemispheric associations
- Purpose: Context binding, callosal associations, local cortical computation
- Trigger: thalamic_input AND horizontal_signal
- Inputs: thalamic_input, layer1_feedback
- Outputs: {supragranular_output: dict, association_strength: float, callosal_signal: float}
- State: {association_weights: dict}
- Dependencies: LayerIVThalamicInputGate
- Priority: HIGH
- Timing: After Layer IV
- Edge: Layers II/III = association cortex proper

### NEOCORTICAL-003: LayerVOutputProjector
- Human Analog: Layer V (infragranular) — major corticofugal projections to subcortical structures
- Purpose: Sends processed signals to basal ganglia, brainstem, spinal cord for action
- Trigger: processing_complete AND action_signal_ready
- Inputs: layer_output
- Outputs: {layer5_output: dict, subcortical_projection: dict, action_command: dict}
- State: {}
- Dependencies: LayerIIIIIAssociator
- Priority: HIGHEST
- Timing: Final processing stage
- Edge: Layer V = behavioral output

### NEOCORTICAL-004: LayerVIThalamicModulator
- Human Analog: Layer VI (multiform) — corticothalamic feedback, gain control
- Purpose: Feedback to thalamus for precision tuning; regulates sensory gain
- Trigger: thalamic_input AND processing_state
- Inputs: thalamic_input, cortical_processing_state
- Outputs: {layer6_output: dict, thalamic_gain_adjustment: float, corticothalamic_feedback: dict}
- State: {gain_history: list}
- Dependencies: LayerVOutputProjector
- Priority: HIGH
- Timing: Feedback
- Edge: Layer VI = thalamic quality control

### NEOCORTICAL-005: DorsolateralPrefrontalDorsal
- Human Analog: DLPFC dorsal part — working memory, cognitive control, decision making
- Purpose: Holds abstract rules and goals active during multi-step reasoning
- Trigger: complex_reasoning_required OR multi_step_goal
- Inputs: working_memory_load, goal_state
- Outputs: {dorsolateral_dorsal_output: dict, working_memory_active: bool, cognitive_control: float}
- State: {working_memory_buffer: list}
- Dependencies: DorsolateralPrefrontalPlanner
- Priority: HIGH
- Timing: Complex reasoning
- Edge: Damage = "use rules consistently"

### NEOCORTICAL-006: DorsolateralPrefrontalVentral
- Human Analog: DLPFC ventral part — executive functions, interference control
- Purpose: Suppresses inappropriate responses; conflict monitoring
- Trigger: interference_detected OR conflicting_signals
- Inputs: conflict_signals
- Outputs: {dorsolateral_ventral_output: dict, interference_suppression: float, conflict_resolved: bool}
- State: {}
- Dependencies: DorsolateralPrefrontalDorsal
- Priority: HIGH
- Timing: Conflict
- Edge: Damage = "easily distracted"

### NEOCORTICAL-007: OrbitofrontalRewardValuator
- Human Analog: Orbitofrontal cortex — reward valuation, reversal learning, outcome prediction
- Purpose: Values outcomes; reverses associations when outcomes change
- Trigger: outcome_received OR reward_prediction_changed
- Inputs: predicted_outcome, actual_outcome
- Outputs: {orbitofrontal_output: dict, value_signal: float, reversal_triggered: bool}
- State: {value_map: dict}
- Dependencies: PredictionErrorDrift
- Priority: HIGH
- Timing: Outcome
- Edge: Damage = "keeps doing what doesn't work"

### NEOCORTICAL-008: VentrolateralPrefrontalInferior
- Human Analog: Ventrolateral prefrontal cortex — response inhibition, social reasoning
- Purpose: Inhibits inappropriate actions; processes social cues
- Trigger: inhibition_required OR social_cue
- Inputs: action_candidates, social_context
- Outputs: {ventrolateral_pfc_output: dict, response_inhibited: bool, social_reasoning: dict}
- State: {}
- Dependencies: OrbitofrontalRewardValuator
- Priority: HIGH
- Timing: Inhibition/social
- Edge: Damage = "says the wrong thing"

### NEOCORTICAL-009: FrontopolarProspectiveSimulator
- Human Analog: Frontopolar cortex (BA 10) — prospective memory, future scenario planning
- Purpose: Branching into multiple future scenarios; considers what might happen
- Trigger: future_scenario_request OR long_term_planning
- Inputs: current_state, goal
- Outputs: {frontopolar_output: dict, scenario_branches: list, prospection_depth: float}
- State: {scenario_stack: list}
- Dependencies: DorsolateralPrefrontalPlanner
- Priority: HIGH
- Timing: Future thinking
- Edge: Most human region; distinguishes us from great apes

### NEOCORTICAL-010: PremotorSupplementaryMotorArea
- Human Analog: Premotor cortex and supplementary motor area — motor planning without execution
- Purpose: Plans motor sequences; internally simulates actions before execution
- Trigger: motor_plan_needed OR imagined_action
- Inputs: motor_goal, sequence_complexity
- Outputs: {premotor_output: dict, motor_plan_ready: bool, internal_simulation: float}
- State: {motor_plans: list}
- Dependencies: LayerVOutputProjector
- Priority: HIGH
- Timing: Motor planning
- Edge: Damage = "can't plan actions"

### NEOCORTICAL-011: BrocaAreaMotorSpeech
- Human Analog: Broca's area (IFG) — speech production, grammatical processing
- Purpose: Generates linguistic output; manages grammatical structure
- Trigger: speech_production_requested
- Inputs: semantic_content, grammatical_requirements
- Outputs: {broca_output: dict, speech_motor_command: dict, grammatical_structure: dict}
- State: {grammar_buffer: list}
- Dependencies: VentrolateralPrefrontalInferior
- Priority: HIGH
- Timing: Speech production
- Edge: Damage = "can't speak fluently"

### NEOCORTICAL-012: WernickeAreaSemanticComprehension
- Human Analog: Wernicke's area (STG) — language comprehension, semantic integration
- Purpose: Extracts meaning from language input; integrates with context
- Trigger: language_input_received
- Inputs: linguistic_signal, contextual_signal
- Outputs: {wernicke_output: dict, semantic_representation: dict, comprehension_achieved: bool}
- State: {semantic_network: dict}
- Dependencies: TemporalSemanticMapper
- Priority: HIGH
- Timing: Language input
- Edge: Damage = "can't understand language"

### NEOCORTICAL-013: InferiorParietalLobuleSensorimotor
- Human Analog: IPL (BA 40) — sensorimotor integration, grasp planning, reaching
- Purpose: Integrates sensory and motor for grasp/reach in abstract reasoning
- Trigger: abstract_integration_needed
- Inputs: sensory_data, motor_intention
- Outputs: {ipl_output: dict, sensorimotor_integration: float}
- State: {}
- Dependencies: ParietalSomatoSpatialIntegrator
- Priority: MEDIUM
- Timing: Sensorimotor integration
- Edge: IPL = "how to interact with this"

### NEOCORTICAL-014: SuperiorParietalLobuleReaching
- Human Analog: Superior parietal lobule — reaching, spatial attention
- Purpose: Spatial targeting for abstract "reaching" toward goals
- Trigger: spatial_targeting_needed
- Inputs: spatial_goal, current_position
- Outputs: {spl_output: dict, spatial_target: dict, reaching_signal: float}
- State: {spatial_map: dict}
- Dependencies: InferiorParietalLobuleSensorimotor
- Priority: MEDIUM
- Timing: Spatial targeting
- Edge: SPL = "where to go"

### NEOCORTICAL-015: PostcentralGyrusPrimarySomato
- Human Analog: Postcentral gyrus (primary somatosensory cortex) — touch, temperature, proprioception
- Purpose: Primary somatosensory processing; body-map generation
- Trigger: somatosensory_input
- Inputs: tactile_signal, proprioceptive_signal
- Outputs: {postcentral_output: dict, body_map_updated: bool, somatosensory_representation: dict}
- State: {body_schema: dict}
- Dependencies: TactileProprioRelay (foundational)
- Priority: MEDIUM
- Timing: Somatosensory
- Edge: Body map for embodiment

### NEOCORTICAL-016: AnteriorTemporalPoleSemantic
- Human Analog: Anterior temporal pole — high-level semantic and social concept binding
- Purpose: Binds concepts to create abstract meaning; social person knowledge
- Trigger: abstract_concept_needed OR social_person_processing
- Inputs: semantic_features
- Outputs: {anterior_temporal_output: dict, concept_binding: float, social_knowledge: dict}
- State: {semantic_bindings: list}
- Dependencies: TemporalSemanticMapper
- Priority: MEDIUM
- Timing: Abstract concept
- Edge: AT = "what does this mean in the world"

### NEOCORTICAL-017: PosteriorSuperiorTemporalGyrus
- Human Analog: Posterior superior temporal gyrus — audiovisual integration, biological motion
- Purpose: Integrates auditory and visual; processes motion and social signals
- Trigger: audiovisual_integration_needed
- Inputs: auditory_signal, visual_signal
- Outputs: {posterior_stg_output: dict, audiovisual_binding: float, social_motion: dict}
- State: {}
- Dependencies: WernickeAreaSemanticComprehension
- Priority: MEDIUM
- Timing: Audiovisual
- Edge: pSTG = "intentional movement"

### NEOCORTICAL-018: MiddleTemporalGyroscopic
- Human Analog: Middle temporal gyrus — visual motion, biological motion, word meaning
- Purpose: Processes motion in abstract (not just visual); abstract motion concepts
- Trigger: motion_processing OR abstract_motion_concept
- Inputs: motion_signal
- Outputs: {mtg_output: dict, motion_analysis: dict, abstract_motion: float}
- State: {}
- Dependencies: None
- Priority: MEDIUM
- Timing: Motion
- Edge: MTG = "how things move through the world"

### NEOCORTICAL-019: TemporoOccipitalVisualAssembler
- Human Analog: Temporo-occipital junction (ventral visual stream) — object and scene construction
- Purpose: Constructs visual objects and scenes from features; "what" pathway
- Trigger: object_recognition_needed
- Inputs: visual_features
- Outputs: {ventral_visual_output: dict, object_constructed: dict, scene_representation: dict}
- State: {object_library: dict}
- Dependencies: None
- Priority: MEDIUM
- Timing: Object recognition
- Edge: Ventral = "what is it"

### NEOCORTICAL-020: OccipitalPrimaryVisualV1
- Human Analog: Primary visual cortex (V1, striate cortex) — edge, orientation, basic feature extraction
- Purpose: Low-level visual feature extraction (future multimodal input)
- Trigger: visual_input_received
- Inputs: raw_visual_signal
- Outputs: {v1_output: dict, edge_detection: dict, orientation_map: dict}
- State: {orientation_tuning: dict}
- Dependencies: None
- Priority: MEDIUM
- Timing: Visual input
- Edge: V1 = "edges and orientations"

### NEOCORTICAL-021: OccipitalV2BoundaryProcessing
- Human Analog: V2 — boundary processing, figure-ground segregation
- Purpose: Extracts contours and boundaries between objects
- Trigger: boundary_extraction_needed
- Inputs: v1_output
- Outputs: {v2_output: dict, boundary_map: dict, figure_ground_segregation: float}
- State: {}
- Dependencies: OccipitalPrimaryVisualV1
- Priority: MEDIUM
- Timing: After V1
- Edge: V2 = "where are the edges"

### NEOCORTICAL-022: OccipitalV3DepthProcessing
- Human Analog: V3 and V3A — depth and motion integration
- Purpose: Processes depth and 3D structure from visual input
- Trigger: depth_estimation_needed
- Inputs: boundary_map, motion_signal
- Outputs: {v3_output: dict, depth_map: dict, depth_processing: float}
- State: {}
- Dependencies: OccipitalV2BoundaryProcessing
- Priority: MEDIUM
- Timing: Depth
- Edge: V3 = "how far and how deep"

### NEOCORTICAL-023: V4ColorAndForm
- Human Analog: V4 — color, form, and object attention
- Purpose: Intermediate visual processing for color and attended form
- Trigger: color_processing_required
- Inputs: v2_output, attention_signal
- Outputs: {v4_output: dict, color_processed: dict, form_attended: float}
- State: {color_map: dict}
- Dependencies: OccipitalV2BoundaryProcessing
- Priority: MEDIUM
- Timing: Color/form
- Edge: V4 = "what color and shape"

### NEOCORTICAL-024: PosteriorCingulateMemoryAttention
- Human Analog: Posterior cingulate cortex — memory, attention, self-referential processing
- Purpose: Integrates memory retrieval with attentional focus; supports mind-wandering
- Trigger: memory_retrieval AND default_mode
- Inputs: memory_signal, attention_state
- Outputs: {posterior_cingulate_output: dict, memory_attention_integration: float, self_referential: float}
- State: {retrieved_memory: dict}
- Dependencies: DefaultModeWanderer
- Priority: HIGH
- Timing: Default mode/memory
- Edge: PCC = "what should I pay attention to from memory"

### NEOCORTICAL-025: RetrosplenialCortexSceneProcessing
- Human Analog: Retrosplenial cortex (BA 29/30) — scene processing, context, navigation
- Purpose: Processes scene context; integrates with spatial memory
- Trigger: scene_context_needed
- Inputs: scene_features, spatial_memory
- Outputs: {retrosplenial_output: dict, scene_context: dict, spatial_memory_binding: float}
- State: {scene_memory: list}
- Dependencies: RetrosplenialNarrativeCoherer (limbic)
- Priority: MEDIUM
- Timing: Scene
- Edge: RSC = "where am I in context"

### NEOCORTICAL-026: PrecuneusSelfReflection
- Human Analog: Precuneus (medial parietal) — self-reflection, mental imagery, egocentric spatial
- Purpose: Self-referential processing; generates internal mental imagery
- Trigger: self_reflection_requested OR mental_imagery
- Inputs: self_state, imagery_request
- Outputs: {precuneus_output: dict, self_representation: dict, mental_imagery: float}
- State: {self_model: dict}
- Dependencies: SelfNarrativeCoherer
- Priority: HIGH
- Timing: Self-reflection
- Edge: Precuneus = "self as object of thought"

### NEOCORTICAL-027: AngularGyrusMultimodal
- Human Analog: Angular gyrus — multimodal integration, number processing, semantic memory
- Purpose: Binds modalities for abstract concepts; supports semantic memory access
- Trigger: cross_modal_binding_needed OR semantic_access
- Inputs: modality_a, modality_b, semantic_request
- Outputs: {angular_gyrus_output: dict, multimodal_binding: float, semantic_access: dict}
- State: {semantic_bindings: dict}
- Dependencies: WernickeAreaSemanticComprehension
- Priority: HIGH
- Timing: Cross-modal/semantic
- Edge: AG = "what does this mean across senses"

### NEOCORTICAL-028: SupramarginalGyrusManipulation
- Human Analog: Supramarginal gyrus — manipulation of mental representations, gestures
- Purpose: Manipulates abstract mental objects; supports phonological manipulation
- Trigger: mental_manipulation_required
- Inputs: mental_object, manipulation_type
- Outputs: {supramarginal_output: dict, manipulation_executed: bool, representation_updated: dict}
- State: {}
- Dependencies: AngularGyrusMultimodal
- Priority: MEDIUM
- Timing: Manipulation
- Edge: SMG = "manipulate this idea"

### NEOCORTICAL-029: AnteriorCingulateCognitive
- Human Analog: Anterior cingulate cortex (dorsal) — cognitive error monitoring, task difficulty
- Purpose: Monitors for errors and conflicts in cognitive processing
- Trigger: error_signal OR task_difficulty_change
- Inputs: processing_output, expected_output
- Outputs: {acc_dorsal_output: dict, error_signal: float, difficulty_signal: float, cognitive_adjustment: float}
- State: {error_history: list}
- Dependencies: AnteriorCingulateConflict (limbic)
- Priority: HIGH
- Timing: Error/conflict
- Edge: ACC = "is my processing going right"

### NEOCORTICAL-030: AnteriorInsulaSalienceAttentional
- Human Analog: Anterior insula (neocortical part) — salience detection, awareness
- Purpose: Detects salient stimuli and switches attentional networks
- Trigger: salient_stimulus_detected
- Inputs: stimulus_intensity, stimulus_novelty
- Outputs: {anterior_insula_output: dict, salience_detected: bool
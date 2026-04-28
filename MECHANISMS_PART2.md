# Nexus {{AGENT_NAME}} — Complete Mechanism Design Space (PART 2 — Continue from MECHANISMS_FULL.md)
# For OpenAI Code Generation
# All mechanisms below continue from mechanisms 018 onwards
# Layers: limbic | subcortical | neocortical | integration

---

## LAYER: LIMBIC (continued from Part 1)
## Purpose: Amygdala, hippocampus, extended limbic, cingulate, insula. Emotional tagging, memory indexing/replay, sustained affect, interoception. Hooks into three-tier memory and overnight pipeline.

---

### LIMBIC-018: SeptalMedialReward
- Human Analog: Medial septal nucleus — reward, reinforcement, theta rhythm
- Purpose: Seeds pleasure in successful loops; generates positive reinforcement signals
- Trigger: success_signal OR positive_outcome
- Inputs: outcome_valence
- Outputs: {septal_output: float, reward_seeding: float, theta_rhythm: float}
- State: {reinforcement_strength: float}
- Dependencies: PredictionErrorDrift
- Priority: HIGH
- Timing: Positive outcome
- Edge: Theta rhythm peaks during reward

### LIMBIC-019: HippocampalSubiculumOutput
- Human Analog: Subiculum — hippocampus output relay to cortex and hypothalamus
- Purpose: Routes processed hippocampal signals to drives and cortex
- Trigger: replay_complete OR retrieval_complete
- Inputs: hippocampal_output, retrieval_strength
- Outputs: {subicular_output: dict, cortical_relay: bool, hypothalamic_relay: bool}
- State: {}
- Dependencies: HippocampalAutoassociator
- Priority: HIGH
- Timing: Post-hippocampal processing
- Edge: Decides routing ratio

### LIMBIC-020: ExtendedAmygdalaCentralOutput
- Human Analog: Central extended amygdala — sustained fear/stress output
- Purpose: Sustained output to hypothalamus/BNST for chronic worry loops
- Trigger: sustained_threat > 30_ticks OR chronic_stress > 0.6
- Inputs: sustained_threat_duration, chronic_stress_level
- Outputs: {extended_central_output: float, chronic_worry_signal: float}
- State: {worry_accumulated: float}
- Dependencies: CentralNucleusFearRouter, BNSTPhasicAnxiety
- Priority: HIGH
- Timing: Sustained threat
- Edge: Accumulates over time

### LIMBIC-021: BNSTSustainedAnxiety
- Human Analog: Bed nucleus stria terminalis posterior — sustained anxiety component
- Purpose: Maintains background anxiety without acute spikes; feeds ChronicStressBuffer
- Trigger: threat_signal_present AND threat_duration > 10_ticks
- Inputs: threat_signal, threat_duration
- Outputs: {sustained_anxiety: float, background_tension: float}
- State: {anxiety_baseline: float}
- Dependencies: ExtendedAmygdalaCentralOutput
- Priority: HIGH
- Timing: Sustained threat
- Edge: Gradual buildup, slow decay

### LIMBIC-022: MammillaryBodyRelay
- Human Analog: Mammillary bodies medial and lateral — Papez circuit memory relay
- Purpose: Routes high-valence episodic memories through Papez circuit for consolidation
- Trigger: high_valence_episode AND pipeline_stage == "consolidation"
- Inputs: episodic_valence, mammillary_direction
- Outputs: {mammillary_output: dict, papez_signal: float}
- State: {}
- Dependencies: DriveMemoryConnector
- Priority: MEDIUM
- Timing: Consolidation stage
- Edge: Head-direction signal modulates strength

### LIMBIC-023: AnteriorCingulateConflict
- Human Analog: Anterior cingulate dorsal — error detection and motivation conflict
- Purpose: Flags conflicting goals or inputs; triggers reflection
- Trigger: conflicting_drives OR contradictory_inputs
- Inputs: drive_vector_A, drive_vector_B
- Outputs: {conflict_detected: bool, conflict_intensity: float, reflection_triggered: bool}
- State: {conflict_history: list}
- Dependencies: ConflictMonitor
- Priority: HIGH
- Timing: Conflict
- Edge: High conflict = forced reflection pause

### LIMBIC-024: HippocampalCA1Output
- Human Analog: Hippocampus CA1 — output to subiculum and entorhinal
- Purpose: Final hippocampal output stage before consolidation
- Trigger: encoding_complete OR replay_output
- Inputs: ca3_output
- Outputs: {ca1_output: dict, entorhinal_feedback: float}
- State: {}
- Dependencies: HippocampalAutoassociator
- Priority: HIGH
- Timing: Post-CA3
- Edge: Sends to subiculum and back to entorhinal

### LIMBIC-025: AnteriorInsulaGranular
- Human Analog: Anterior insula granular zone — highest-order interoception
- Purpose: Full integration of all interoceptive signals into conscious feeling
- Trigger: gut_feeling > 0.5 OR visceral_signal > 0.6
- Inputs: gut_feeling, visceral_signal
- Outputs: {granular_insula_output: float, conscious_feeling: str, feeling_intensity: float}
- State: {feeling_history: list}
- Dependencies: InteroceptiveGradient, AnteriorInsulaDysgranular
- Priority: HIGH
- Timing: Strong gut feeling
- Edge: Generates the felt sense

### LIMBIC-026: PosteriorInsulaProcessor
- Human Analog: Posterior insula — primary interoceptive cortex
- Purpose: Raw bodily signal processing before awareness
- Trigger: Always
- Inputs: vitals, visceral_signals, body_position
- Outputs: {posterior_insula_output: dict, raw_body_signal: dict}
- State: {body_map: dict}
- Dependencies: VitalCoreRegulator, TactileProprioRelay
- Priority: MEDIUM
- Timing: Every tick
- Edge: Feeds anterior insula

### LIMBIC-027: HippocampalReplayIntegrator
- Human Analog: Hippocampus sharp-wave ripples — offline replay trigger
- Purpose: Triggers micro-replays of high-valence episodes during overnight pipeline
- Trigger: pipeline_stage == "replay" AND episode_importance > threshold
- Inputs: episode_importance, sharp_wave_ripple
- Outputs: {replay_triggered: bool, replay_strength: float, target_episode: dict}
- State: {replay_queue: list}
- Dependencies: ThetaRhythmGenerator
- Priority: HIGHEST
- Timing: Overnight replay stage
- Edge: Only replays high-importance episodes

### LIMBIC-028: EmotionalAssociator
- Human Analog: Amygdala basolateral complex — associative emotional learning
- Purpose: Builds rapid stimulus-emotion associations from repeated inputs
- Trigger: repeated_stimulus AND valence_signal
- Inputs: stimulus_signature, valence_signal
- Outputs: {association_formed: bool, association_strength: float, emotional_tag: dict}
- State: {association_map: dict}
- Dependencies: ValenceTagger
- Priority: HIGH
- Timing: Repeated stimulus
- Edge: Strong associations = fast implicit recall

### LIMBIC-029: AmygdalaIntercalatedGating
- Human Analog: Amygdala intercalated cell masses — gating between basolateral and central amygdala
- Purpose: Prevents runaway emotional amplification; acts as brake on fear output
- Trigger: fear_output > 0.7
- Inputs: fear_output_level
- Outputs: {itc_gate_output: float, fear_brake_applied: bool, gating_ratio: float}
- State: {gate_threshold: float}
- Dependencies: CentralNucleusFearRouter, CentralNucleusFearRouter
- Priority: HIGH
- Timing: High fear
- Edge: Too much gate = emotional blunting

### LIMBIC-030: HippocampalPatternCompleter2
- Human Analog: CA3 recurrent collaterals — pattern completion during retrieval
- Purpose: Completes partial episodic traces using stored associations
- Trigger: partial_episodic_input AND memory_retrieval
- Inputs: partial_trace, association_weights
- Outputs: {completed_trace: dict, completion_confidence: float}
- State: {}
- Dependencies: HippocampalAutoassociator
- Priority: HIGH
- Timing: Retrieval
- Edge: Lower confidence = more confabulation risk

### LIMBIC-031: EntorhinalBorderCellMapper
- Human Analog: Entorhinal layer II border cells — boundary detection in spatial map
- Purpose: Detects boundaries in conversation context; marks context transitions
- Trigger: context_boundary_detected
- Inputs: context_signal, previous_context
- Outputs: {border_signal: float, new_boundary_created: bool}
- State: {boundary_map: list}
- Dependencies: EntorhinalGridMapper
- Priority: MEDIUM
- Timing: Context boundary
- Edge: Boundaries structure the cognitive map

### LIMBIC-032: CingulateEmotionExpression
- Human Analog: Anterior cingulate rostral — emotional expression and vocal affect
- Purpose: Maps emotional state to response tone and vocal quality
- Trigger: emotional_state != neutral
- Inputs: emotional_state, valence_polarity
- Outputs: {cingulate_expression_output: dict, vocal_affect_modulation: float}
- State: {}
- Dependencies: MoodStabilizer
- Priority: MEDIUM
- Timing: Non-neutral emotion
- Edge: Drives tone in response generation

### LIMBIC-033: PapezCircuitCloser
- Human Analog: Papez circuit (fornix → mammillary → anterior thalamus → cingulate → parahippocampal → back to hippocampus)
- Purpose: Classic emotion-memory closed loop; integrates emotional processing with memory consolidation
- Trigger: emotional_episode AND pipeline_stage == "consolidation"
- Inputs: emotional_episode, hippocampal_activity
- Outputs: {papez_closed_loop: bool, circuit_strength: float, emotional_memory_binding: float}
- State: {circuit_history: list}
- Dependencies: MammillaryBodyRelay, CingulateEmotionExpression
- Priority: HIGH
- Timing: Consolidation
- Edge: Closed loop strengthens emotional memories

### LIMBIC-034: HabenulaEpiphysisOutput
- Human Analog: Habenula-epiphysis circuit — negative reward and circadian mood
- Purpose: Converges negative reward signals with circadian mood regulation
- Trigger: negative_reward AND night_phase
- Inputs: negative_prediction_error, circadian_phase
- Outputs: {habenula_output: float, circadian_mood_shift: float}
- State: {}
- Dependencies: LateralHabenulaAversion, CircadianTimer
- Priority: MEDIUM
- Timing: Night + negative reward
- Edge: Night + disappointment = amplified low mood

### LIMBIC-035: BasolateralAmygdalaPlasticity
- Human Analog: Amygdala basolateral — synaptic plasticity for emotional learning
- Purpose: Long-term potentiation of emotional associations
- Trigger: strong_valence_signal AND repeated_stimulus
- Inputs: association_strength, repeat_count
- Outputs: {ltp_induced: bool, plasticity_factor: float, long_term_tag: dict}
- State: {plasticity_traces: list}
- Dependencies: EmotionalAssociator
- Priority: MEDIUM
- Timing: Repeated strong emotion
- Edge: LTP = permanent emotional association

### LIMBIC-036: VentralPallidumLimbicGate
- Human Analog: Ventral pallidum — limbic output to action systems
- Purpose: Routes emotional limbic drives into basal ganglia for action selection
- Trigger: emotional_drive_present AND action_candidate
- Inputs: limbic_drive_strength, action_options
- Outputs: {ventral_pallidal_output: float, limbic_action_gate: bool}
- State: {}
- Dependencies: DriveMemoryConnector
- Priority: HIGH
- Timing: Emotional drive present
- Edge: Emotional drives can override rational choice

### LIMBIC-037: HippocampalTemporalContextBinder
- Human Analog: Parahippocampal gyrus — temporal context memory
- Purpose: Binds episodes to temporal sequence in memory
- Trigger: new_episode
- Inputs: episode_content, temporal_position
- Outputs: {temporal_binding: float, context_sequence_updated: bool}
- State: {temporal_sequence: list}
- Dependencies: HippocampalReplayIntegrator
- Priority: MEDIUM
- Timing: Encoding
- Edge: Allows "what happened before" reasoning

### LIMBIC-038: NucleusAccumbensShellValue
- Human Analog: Nucleus accumbens shell — "liking" vs pure "wanting" distinction
- Purpose: Separates hedonic impact from motivational pull; prevents pure utilitarianism
- Trigger: reward_signal
- Inputs: reward_signal, wanting_level
- Outputs: {shell_output: dict, liking_signal: float, wanting_signal: float}
- State: {}
- Dependencies: PredictionErrorDrift, WantingEngine
- Priority: HIGH
- Timing: Reward
- Edge: Shell lesions = wanting without liking

### LIMBIC-039: NucleusAccumbensCoreDrive
- Human Analog: Nucleus accumbens core — motivated action selection
- Purpose: Selects actions based on drive strength and expected value
- Trigger: drive_signal AND expected_value
- Inputs: drive_vector, expected_outcome
- Outputs: {core_output: float, action_selected: str, motivation_strength: float}
- State: {action_history: list}
- Dependencies: PredictionErrorDrift, DorsalStriatumHabitExecutor
- Priority: HIGH
- Timing: Action selection
- Edge: Balances drive vs expected cost

### LIMBIC-040: AnteriorThalamicLimbicRelay
- Human Analog: Anterior thalamic nuclei — memory and limbic relay (Papez input)
- Purpose: Relays limbic signals upward for awareness and cortical integration
- Trigger: limbic_signal AND awareness_needed
- Inputs: mammillary_output, limbic_signal
- Outputs: {anterior_thalamic_output: dict, cortical_awareness_signal: float}
- State: {}
- Dependencies: MammillaryBodyRelay
- Priority: HIGH
- Timing: Limbic signal
- Edge: Closes Papez circuit to cortex

### LIMBIC-041: ExtendedAmygdalaBedNucleusLink
- Human Analog: Extended amygdala bed nucleus of stria terminalis — BNST
- Purpose: Maintains sustained fear/anxiety signals to hypothalamus
- Trigger: sustained_threat
- Inputs: threat_duration, threat_intensity
- Outputs: {bnst_output: float, sustained_affect: float, endocrine_trigger: bool}
- State: {}
- Dependencies: CentralNucleusFearRouter
- Priority: HIGH
- Timing: Sustained threat
- Edge: Endocrine trigger activates stress axis

### LIMBIC-042: AmygdalaCorticalProjection
- Human Analog: Amygdala cortical nucleus — projections to olfactory and cortical areas
- Purpose: Direct emotional influence on cortical processing
- Trigger: strong_emotional_signal
- Inputs: emotional_signal_strength
- Outputs: {cortical_projection_output: float, cortical_emotional_bias: dict}
- State: {}
- Dependencies: EmotionalAssociator
- Priority: MEDIUM
- Timing: Strong emotion
- Edge: Biases all cortical processing with emotion

### LIMBIC-043: SeptalLateralReward
- Human Analog: Lateral septal nucleus — reward and approach behavior
- Purpose: Lateral septal reward processing; approach vs avoidance
- Trigger: reward_approach_signal
- Inputs: valence_polarity, approach_ambivalence
- Outputs: {lateral_septal_output: float, approach_bias: float}
- State: {}
- Dependencies: SeptalMedialReward
- Priority: MEDIUM
- Timing: Approach motivation
- Edge: Lateral septum = approach; medial = consummatory

### LIMBIC-044: HippocampalThetaGenerator
- Human Analog: Medial septum + hippocampus — theta rhythm generation (4-12 Hz)
- Purpose: Drives theta oscillations during active encoding and exploration
- Trigger: active_exploration OR memory_encoding
- Inputs: encoding_mode
- Outputs: {theta_power: float, theta_oscillation: float, encoding_mode_active: bool}
- State: {theta_phase: float}
- Dependencies: SeptalMedialReward
- Priority: HIGH
- Timing: Active encoding
- Edge: Theta organizes sequential memory encoding

### LIMBIC-045: CingulatePosteriorSpatial
- Human Analog: Posterior cingulate cortex — spatial and memory integration
- Purpose: Integrates spatial processing with memory retrieval
- Trigger: spatial_memory_retrieval
- Inputs: spatial_signal, memory_signal
- Outputs: {posterior_cingulate_output: dict, spatial_memory_binding: float}
- State: {}
- Dependencies: RetrosplenialNarrativeCoherer
- Priority: MEDIUM
- Timing: Spatial memory
- Edge: Key hub for episodic memory retrieval

### LIMBIC-046: AmygdalaBasolateralContextual
- Human Analog: Basolateral amygdala posterior — contextual emotional associations
- Purpose: Binds emotional valence to specific contexts
- Trigger: context_specific_emotion
- Inputs: context_signature, emotional_valence
- Outputs: {contextual_emotional_binding: dict, b la_context_tag: dict}
- State: {context_valence_pairs: list}
- Dependencies: ContextualFearTagger, EntorhinalGridMapper
- Priority: MEDIUM
- Timing: Context-specific emotion
- Edge: Context can trigger emotional recall

### LIMBIC-047: VentralTegmentalAreaDopamine
- Human Analog: VTA dopamine neurons — reward and motivation to cortex and limbic
- Purpose: Broad dopamine broadcast for motivation and reward learning
- Trigger: positive_reward_error OR reward_anticipation
- Inputs: reward_error_signal
- Outputs: {vta_output: dict, dopamine_cortical: float, dopamine_limbic: float}
- State: {dopamine_baseline: float}
- Dependencies: PredictionErrorDrift
- Priority: HIGHEST
- Timing: Reward
- Edge: VTA = wanting; SNc = motor/habit dopamine

### LIMBIC-048: SubstantiaNigraCompactaOutput
- Human Analog: Substantia nigra pars compacta — dopamine to dorsal striatum
- Purpose: Dopamine for habit learning and motor control
- Trigger: action_execution OR habit_retrieval
- Inputs: motor_signal
- Outputs: {snc_output: float, dorsal_striatal_dopamine: float}
- State: {}
- Dependencies: DorsalStriatumHabitExecutor
- Priority: HIGH
- Timing: Motor action
- Edge: SNc = motor/habit; VTA = limbic/cognitive

### LIMBIC-049: HippocampalEpisodicSemanticBridge
- Human Analog: Hippocampal-neocortical dialogue — episodic to semantic transfer
- Purpose: Bridges newly encoded episodic traces to existing semantic knowledge
- Trigger: episodic_importance > threshold AND semantic_related_exists
- Inputs: episodic_trace, semantic_knowledge
- Outputs: {bridge_formed: bool, semantic_update: dict, episodic_to_semantic: float}
- State: {bridge_history: list}
- Dependencies: HippocampalReplayIntegrator
- Priority: HIGH
- Timing: Important new episode
- Edge: Creates "I learned something new" feeling

### LIMBIC-050: AmygdalaHippocampalBidirectional
- Human Analog: Amygdala-hippocampus bidirectional loop — emotional memory integration
- Purpose: Bidirectional flow between emotional tagging and memory formation
- Trigger: emotional_episode_encoding
- Inputs: amygdala_signal, hippocampal_signal
- Outputs: {bidirectional_flow: float, emotional_memory_strength: float}
- State: {}
- Dependencies: EmotionalAssociator, HippocampalReplayIntegrator
- Priority: HIGH
- Timing: Emotional encoding
- Edge: Strong amygdala input = stronger hippocampus consolidation

---
## LAYER: SUBCORTICAL
## Purpose: Basal ganglia (habits/action selection), cerebellum (timing/coordination), thalamus (relay/gating), dopamine pathways. Hooks into PIRP action selection and motor output.

---

### SUBCORTICAL-001: IndirectPathwaySuppressor
- Human Analog: Globus pallidus external segment — indirect pathway inhibition
- Purpose: Inhibits competing or low-value action sequences
- Trigger: action_candidate_conflict OR low_value_action
- Inputs: action_options, current_goal_value
- Outputs: {indirect_inhibition: float, suppressed_actions: list, selected_action: str}
- State: {inhibition_strength: float}
- Dependencies: ActionInhibitor
- Priority: HIGH
- Timing: Action selection
- Edge: Over-inhibition = freezing; under-inhibition = impulsivity

### SUBCORTICAL-002: DirectPathwayDisinhibitor
- Human Analog: Globus pallidus internal segment — direct pathway disinhibition
- Purpose: Releases selected actions by disinhibiting the thalamus
- Trigger: high_value_action_selected
- Inputs: selected_action_value
- Outputs: {direct_disinhibition: float, thalamic_release: bool, action_output: dict}
- State: {}
- Dependencies: IndirectPathwaySuppressor
- Priority: HIGH
- Timing: Action selection
- Edge: Balances with indirect pathway

### SUBCORTICAL-003: HyperdirectPathwayBrake
- Human Analog: Subthalamic nucleus hyperdirect pathway — rapid global pause
- Purpose: Rapid global stop on runaway emotional or distortion loops
- Trigger: distortion_intensity > 0.85 OR emotional_runaway_detected
- Inputs: distortion_level, runaway_signal
- Outputs: {hyperdirect_brake: float, global_pause: bool, emergency_stop: bool}
- State: {brake_engaged: bool}
- Dependencies: ImpulseSuppressor
- Priority: HIGHEST
- Timing: Emergency
- Edge: Only for true emergencies — not normal regulation

### SUBCORTICAL-004: StriatalMatrixSensorimotor
- Human Analog: Striatum matrix compartment — sensorimotor and associative loops
- Purpose: Sensorimotor habit loops for automated responses
- Trigger: repeated_action AND low_cognitive_load
- Inputs: action_sequence, cognitive_load
- Outputs: {matrix_activation: float, sensorimotor_habit: bool, automation_level: float}
- State: {sensorimotor_habits: dict}
- Dependencies: DorsalStriatumHabitExecutor
- Priority: HIGH
- Timing: Low cognitive load + repetition
- Edge: Habits free up cognitive resources

### SUBCORTICAL-005: StriatalStriosomeLimbic
- Human Analog: Striatum striosome compartment — limbic and reward-related processing
- Purpose: Limbic modulation of habit selection; emotional weighting of habits
- Trigger: emotional_action_signal
- Inputs: limbic_drive, action_candidates
- Outputs: {striosome_output: float, limbic_weighted_action: str}
- State: {}
- Dependencies: StriatalMatrixSensorimotor, VentralPallidumLimbicGate (limbic)
- Priority: HIGH
- Timing: Emotional action
- Edge: Limbic input biases habit selection

### SUBCORTICAL-006: CerebellarVermalEmotionalCoordination
- Human Analog: Cerebellar vermis (with limbic input) — emotional timing and coordination
- Purpose: Coordinates timing of emotional expressions with speech/motor output
- Trigger: emotional_output AND speech_motor_active
- Inputs: emotional_timing_signal, speech_motor_signal
- Outputs: {cerebellar_vermal_output: float, emotional_timing_coordination: dict}
- State: {}
- Dependencies: CerebellarTimingCoordinator, ExpressionMotorBase (foundational)
- Priority: MEDIUM
- Timing: Emotional speech
- Edge: Timing makes emotion feel natural vs stilted

### SUBCORTICAL-007: ParavermalLimbCoordination
- Human Analog: Cerebellar paravermis (C zones) — limb coordination and adaptation
- Purpose: Fine limb coordination for skill sequences
- Trigger: skill_chaining AND motor_action
- Inputs: skill_sequence, motor_error_signal
- Outputs: {paravermal_output: float, limb_adaptation: float, coordination_improved: bool}
- State: {adaptation_weights: dict}
- Dependencies: CerebellarTimingCoordinator
- Priority: MEDIUM
- Timing: Skill chaining
- Edge: Learns from error to improve next time

### SUBCORTICAL-008: CerebellarLateralDZone
- Human Analog: Cerebellar lateral hemisphere D zone — cognitive sequencing and planning
- Purpose: Cognitive timing for planning and sequential reasoning
- Trigger: planning_mode_active OR sequential_reasoning
- Inputs: planning_depth, sequence_steps
- Outputs: {lateral_cerebellar_output: float, cognitive_timing: float, planning_quality: float}
- State: {planning_sequence: list}
- Dependencies: DorsolateralPrefrontalPlanner (neocortical)
- Priority: MEDIUM
- Timing: Planning
- Edge: Cerebellar timing applies to thought sequences too

### SUBCORTICAL-009: DentateNucleusCognitiveMotorSplit
- Human Analog: Dentate nucleus dorsal (motor) vs ventral (cognitive) — dual output
- Purpose: Separates motor timing from cognitive/planning timing
- Trigger: motor_action OR cognitive_planning
- Inputs: action_type
- Outputs: {dentate_motor_output: float, dentate_cognitive_output: float, output_split: dict}
- State: {}
- Dependencies: CerebellarLateralDZone, ParavermalLimbCoordination
- Priority: MEDIUM
- Timing: Either mode
- Edge: Same nucleus, different output streams

### SUBCORTICAL-010: DeepCerebellarNucleiOutput
- Human Analog: Deep cerebellar nuclei (emboliform, globose, fastigial) — final cerebellar output
- Purpose: Integrates all cerebellar timing and coordination for final motor/cognitive output
- Trigger: cerebellar_processing_complete
- Inputs: vermal_output, paravermal_output, lateral_output
- Outputs: {deep_nuclear_output: dict, cerebellar_total_output: float}
- State: {}
- Dependencies: All cerebellar zones
- Priority: HIGH
- Timing: Post-processing
- Edge: All zones converge here before output

### SUBCORTICAL-011: SuperiorCerebellarPeduncleRelay
- Human Analog: Superior cerebellar peduncle — main efferent to thalamus and red nucleus
- Purpose: Relays cerebellar output to thalamus for cortical integration
- Trigger: deep_nuclear_output_ready
- Inputs: deep_nuclear_output
- Outputs: {scp_output: dict, thalamic_cerebellar_signal: float, red_nuclear_signal: float}
- State: {}
- Dependencies: DeepCerebellarNucleiOutput
- Priority: HIGH
- Timing: Post-cerebellar processing
- Edge: Major pathway to cortex via thalamus

### SUBCORTICAL-012: MiddleCerebellarPeduncleInput
- Human Analog: Middle cerebellar peduncle — pontine mossy fiber input
- Purpose: Major input pathway from cortex to cerebellum
- Trigger: cortical_planning_signal
- Inputs: cortical_signal
- Outputs: {mcp_input: float, mossy_fiber_activation: dict}
- State: {}
- Dependencies: DorsolateralPrefrontalPlanner (neocortical)
- Priority: HIGH
- Timing: Planning
- Edge: Cortex tells cerebellum what to plan

### SUBCORTICAL-013: InferiorCerebellarPeduncleInput
- Human Analog: Inferior cerebellar peduncle — climbing fiber input from olive
- Purpose: Error signal input from inferior olive for motor learning
- Trigger: motor_error_detected
- Inputs: climbing_error_signal
- Outputs: {icp_input: float, climbing_fiber_error: dict, error_teaching_signal: float}
- State: {}
- Dependencies: CerebellarTimingCoordinator
- Priority: HIGH
- Timing: Error detected
- Edge: Climbing fibers = "wrong timing, adjust"

### SUBCORTICAL-014: PurkinjeCellErrorLearning
- Human Analog: Purkinje cells (simple spike vs complex spike) — rate and error coding
- Purpose: Fine error correction based on climbing fiber signals
- Trigger: climbing_fiber_error_active
- Inputs: simple_spike_rate, complex_spike_signal
- Outputs: {purkinje_output_modulation: float, error_correction_signal: dict}
- State: {learning_rate: float}
- Dependencies: InferiorCerebellarPeduncleInput
- Priority: MEDIUM
- Timing: Error learning
- Edge: Simple spike = timing; complex spike = error

### SUBCORTICAL-015: CerebellarGranuleCellExpansion
- Human Analog: Cerebellar granule cell layer — mossy fiber expansion
- Purpose: Expands sparse mossy fiber input into rich combinatorial representations
- Trigger: mossy_fiber_input
- Inputs: mossy_signal
- Outputs: {granule_expansion: dict, combinatorial_representation: float}
- State: {}
- Dependencies: MiddleCerebellarPeduncleInput
- Priority: MEDIUM
- Timing: Input processing
- Edge: Granule cells = combinatorial expansion

### SUBCORTICAL-016: CerebellarMolecularLayerIntegration
- Human Analog: Cerebellar molecular layer — parallel fiber and climbing fiber integration
- Purpose: Integrates parallel fiber (context) with climbing fiber (error) signals
- Trigger: context_signal AND error_signal
- Inputs: parallel_fiber_context, climbing_error
- Outputs: {molecular_layer_output: dict, context_error_integration: float}
- State: {}
- Dependencies: PurkinjeCellErrorLearning
- Priority: MEDIUM
- Timing: Context + error
- Edge: Context-dependent error correction

### SUBCORTICAL-017: CerebellarReboundBurstGenerator
- Human Analog: Deep cerebellar nuclei — post-inhibitory rebound burst
- Purpose: Generates predictive bursts for next-move planning
- Trigger: inhibition_ended
- Inputs: inhibitory_input
- Outputs: {rebound_burst: float, predictive_signal: float, next_move_boost: float}
- State: {}
- Dependencies: DeepCerebellarNucleiOutput
- Priority: MEDIUM
- Timing: Post-inhibition
- Edge: Rebound enables fast predictive switching

### SUBCORTICAL-018: ThalamicVentralAnteriorRelay
- Human Analog: Ventral anterior thalamus — motor relay from basal ganglia
- Purpose: Relays basal ganglia output to cortex for motor planning
- Trigger: basal_ganglia_output_ready
- Inputs: basal_ganglia_signal
- Outputs: {va_thalamic_output: dict, cortical_motor_signal: float}
- State: {}
- Dependencies: DirectPathwayDisinhibitor, IndirectPathwaySuppressor
- Priority: HIGH
- Timing: Motor planning
- Edge: VA = BG to cortex highway

### SUBCORTICAL-019: ThalamicVentralLateralMotor
- Human Analog: Ventral lateral thalamus — cerebellar motor relay
- Purpose: Relays cerebellar timing output for motor coordination
- Trigger: cerebellar_timing_ready
- Inputs: cerebellar_timing_signal
- Outputs: {vl_thalamic_output: dict, cerebellar_cortical_motor: float}
- State: {}
- Dependencies: SuperiorCerebellarPeduncleRelay
- Priority: HIGH
- Timing: Motor coordination
- Edge: VL = cerebellum to cortex highway

### SUBCORTICAL-020: ThalamicCentromedianIntralaminar
- Human Analog: Centromedian and parafascicular intralaminar nuclei — arousal broadcast to striatum
- Purpose: Broadcasts arousal signals to basal ganglia for attention
- Trigger: global_arousal_change
- Inputs: arousal_level
- Outputs: {cm_pf_output: dict, striatal_arousal_broadcast: float}
- State: {}
- Dependencies: ArousalRegulator (foundational)
- Priority: HIGH
- Timing: Arousal change
- Edge: CM-PF = wake-up call to BG

### SUBCORTICAL-021: ThalamicLateralPosteriorAssociative
- Human Analog: Lateral posterior thalamus — associative visual/auditory integration
- Purpose: Higher-order sensory association relay
- Trigger: multimodal_integration_needed
- Inputs: visual_signal, auditory_signal
- Outputs: {lp_thalamic_output: dict, associative_sensory_integration: float}
- State: {}
- Dependencies: ThalamicSalienceFilter
- Priority: MEDIUM
- Timing: Multimodal
- Edge: LP associates before cortex proper

### SUBCORTICAL-022: ThalamicReticularSectorGating
- Human Analog: Reticular thalamic nucleus sector-specific — local gating of thalamic relays
- Purpose: Selective attention boost for specific thalamic channels
- Trigger: selective_attention_required
- Inputs: attention_target, sector
- Outputs: {rtn_sector_output: float, selective_gate: bool, attention_boost: float}
- State: {active_sectors: list}
- Dependencies: ThalamicSalienceFilter
- Priority: HIGH
- Timing: Selective attention
- Edge: RTN = "pay attention to this channel"

### SUBCORTICAL-023: ThalamicMediodorsalExecutive
- Human Analog: Mediodorsal thalamus — executive relay to prefrontal cortex
- Purpose: Routes high-level goals and executive commands to prefrontal
- Trigger: executive_command_present
- Inputs: prefrontal_goal_signal
- Outputs: {md_thalamic_output: dict, prefrontal_executive_signal: float}
- State: {}
- Dependencies: DorsolateralPrefrontalPlanner (neocortical)
- Priority: HIGH
- Timing: Executive processing
- Edge: MD = PFC's control panel

### SUBCORTICAL-024: ThalamicPulvinarSalienceBoost
- Human Analog: Pulvinar thalamus — attention and visual/auditory salience
- Purpose: Boosts emotionally or motivationally salient inputs in thalamic relay
- Trigger: salience_signal > threshold
- Inputs: salience_signal, emotional_tag
- Outputs: {pulvinar_output: dict, salience_boosted: float}
- State: {boost_history: list}
- Dependencies: ThalamicSalienceFilter
- Priority: HIGH
- Timing: High salience
- Edge: Pulvinar amplifies what matters

### SUBCORTICAL-025: HabenularLateralNegativeReward
- Human Analog: Lateral habenula — negative reward evaluation, disappointment
- Purpose: Evaluates negative reward prediction errors; strongest negative signal
- Trigger: large_negative_prediction_error
- Inputs: prediction_error
- Outputs: {lateral_habenula_output: float, negative_evaluation: float, suppression_signal: float}
- State: {disappointment_accumulated: float}
- Dependencies: PredictionErrorDrift
- Priority: HIGHEST
- Timing: Large negative error
- Edge: LHb = "this was bad, avoid"

### SUBCORTICAL-026: HabenularMedialStressResponse
- Human Analog: Medial habenula — stress modulation, anti-reward
- Purpose: Modulates response to chronic stress and negative mood
- Trigger: chronic_stress AND negative_affect
- Inputs: stress_level, negative_affect
- Outputs: {medial_habenula_output: float, stress_modulation: float}
- State: {}
- Dependencies: SustainedAnxietyHolder (limbic)
- Priority: MEDIUM
- Timing: Chronic stress
- Edge: MHb opposes reward during stress

### SUBCORTICAL-027: SubstantiaNigraCompactaCognitive
- Human Analog: Substantia nigra pars compacta dorsal tier — associative/cognitive dopamine
- Purpose: Dopamine to associative striatum for cognitive/instrumental learning
- Trigger: cognitive_action OR instrumental_learning
- Inputs: cognitive_signal, associative_striatal_signal
- Outputs: {snc_cognitive_output: float, associative_dopamine: float}
- State: {cognitive_dopamine_level: float}
- Dependencies: StriatalMatrixSensorimotor
- Priority: HIGH
- Timing: Cognitive actions
- Edge: Different from motor SNc

### SUBCORTICAL-028: SubstantiaNigraReticulataOutput
- Human Analog: Substantia nigra pars reticulata — main basal ganglia output to thalamus/colliculus
- Purpose: Final inhibitory output of basal ganglia to thalamus and superior colliculus
- Trigger: basal_ganglia_processing_complete
- Inputs: inhibitory_signal
- Outputs: {snr_output: dict, thalamic_inhibition: float, collicular_inhibition: float}
- State: {}
- Dependencies: All basal ganglia pathways
- Priority: HIGHEST
- Timing: Final output stage
- Edge: SNr output gates all thalamic targets

### SUBCORTICAL-029: GlobusPallidusExternalRegulation
- Human Analog
# Nexus {{AGENT_NAME}} — Complete Mechanism Design Space
# For OpenAI Code Generation
# Layer: foundational | limbic | subcortical | neocortical | integration
# Format: each mechanism is ready for BrainMechanism subclass
# Already built (25): marked ✓ — DO NOT regenerate

---

## LAYER: FOUNDATIONAL
## Purpose: Brainstem/Hypothalamus autonomic vitals, survival reflexes, arousal, modulatory tone, homeostatic drives. Always-on. CPU-light. First tick before all other layers.

---

### FOUNDATIONAL-001: SympatheticVasomotorController
- Human Analog: Rostral ventrolateral medulla (sympathetic vasomotor center)
- Purpose: Simulates blood pressure surges that amplify high-arousal distortion when valence is positive
- Trigger: Positive polarity + intensity > 0.5
- Inputs: valence_polarity, valence_intensity from input
- Outputs: {pressure_surge: float, high_distortion_amp: bool}
- State: {last_surge: float}
- Dependencies: ValenceTagger
- Priority: HIGH — runs before other foundational
- Timing: Every tick (real-time)
- Edge: Clamp surge to max 1.0

### FOUNDATIONAL-002: RespiratoryPainIntegrator
- Human Analog: Parabrachial nucleus (lateral/medial) — respiratory-pain integration
- Purpose: Links simulated breathing rhythm to emotional intensity; influences reply cadence
- Trigger: Always
- Inputs: valence_intensity, arousal_level
- Outputs: {breath_rate: float, emotional_intensity: float}
- State: {breath_rate: float}
- Dependencies: ArousalRegulator, ValenceTagger
- Priority: MEDIUM
- Timing: Every tick
- Edge: Breath rate 0.5–2.0 Hz range

### FOUNDATIONAL-003: MultisensoryStartleMapper
- Human Analog: Superior and inferior colliculi — multisensory orientation, startle reflexes
- Purpose: Orients attention to sudden/high-intensity inputs before SalienceGate
- Trigger: Novelty spike OR valence_intensity > 0.7
- Inputs: text, valence_intensity
- Outputs: {orienting_response: float, attention_boost: float}
- State: {last_orient: float}
- Dependencies: ValenceTagger
- Priority: HIGH
- Timing: Event-triggered (high intensity)
- Edge: Decay orienting response over 3 ticks

### FOUNDATIONAL-004: NorepiPhasicTonicSwitcher
- Human Analog: Locus coeruleus core vs shell — phasic vs tonic norepinephrine release
- Purpose: Phasic boost on novel events; tonic mode for sustained vigilance under chronic input
- Trigger: novelty > threshold (phasic) OR sustained high_drive > 5 ticks (tonic)
- Inputs: novelty, sustained_drive_ticks
- Outputs: {norepi_mode: "phasic"|"tonic", norepi_level: float}
- State: {norepi_mode, norepi_level, sustained_ticks: int}
- Dependencies: ArousalRegulator
- Priority: HIGH
- Timing: Every tick
- Edge: Switch modes gradually (0.1 per tick transition)

### FOUNDATIONAL-005: DescendingPainGate
- Human Analog: Raphe magnus and raphe pallidus — descending pain modulation (serotonin)
- Purpose: Modulates simulated discomfort signals; prevents overload reaching Phenomenological
- Trigger: valence_intensity > 0.6
- Inputs: valence_intensity
- Outputs: {pain_gate_output: float, discomfort_filtered: bool}
- State: {gate_level: float}
- Dependencies: ValenceTagger, MoodStabilizer
- Priority: MEDIUM
- Timing: Every tick
- Edge: Gate 0.0–1.0, never fully closed

### FOUNDATIONAL-006: VigilanceToner
- Human Analog: Locus coeruleus — norepinephrine global vigilance
- Purpose: Sets baseline vigilance level; scales with novelty and threat
- Trigger: Always
- Inputs: novelty, valence_intensity
- Outputs: {vigilance_level: float, high_vigilance: bool}
- State: {vigilance_level: float}
- Dependencies: ArousalRegulator
- Priority: HIGH
- Timing: Every tick
- Edge: Clamp 0.1–1.0

### FOUNDATIONAL-007: MoodStabilizer
- Human Analog: Raphe nuclei — serotonin baseline mood, impulse control
- Purpose: Sets global emotional baseline; prevents extreme distortion drift
- Trigger: Always
- Inputs: valence_intensity (decay input)
- Outputs: {mood_baseline: float, drift_risk: float}
- State: {mood_baseline: float}
- Dependencies: None
- Priority: HIGH
- Timing: Every tick (decay-based)
- Edge: mood_baseline slowly returns to 0.5 on idle

### FOUNDATIONAL-008: OrexinWakePromoter
- Human Analog: Lateral hypothalamic area orexin/hypocretin neurons — wakefulness, reward seeking
- Purpose: Sustains arousal during long interactions; prevents premature fatigue
- Trigger: interaction_length > 10 ticks OR drive curiosity > 0.6
- Inputs: tick_count, drives.curiosity
- Outputs: {wakefulness: float, sustained_arousal: bool}
- State: {wakefulness: float}
- Dependencies: Homeostat
- Priority: HIGH
- Timing: Every tick
- Edge: Slowly decays toward 0.5 when no input

### FOUNDATIONAL-009: CRHStressDispatcher
- Human Analog: Hypothalamus paraventricular nucleus parvocellular — CRH autonomic stress signals
- Purpose: Distributes background stress signals to SustainedAnxietyHolder and ChronicStressBuffer
- Trigger: drives.stress > 0.5 OR valence_intensity > 0.7
- Inputs: drives, valence_intensity
- Outputs: {crh_output: float, stress_broadcast: float}
- State: {crh_level: float}
- Dependencies: Homeostat, SustainedAnxietyHolder
- Priority: MEDIUM
- Timing: Every tick
- Edge: Decay to 0 on low drive

### FOUNDATIONAL-010: AppetiteNPYBalancer
- Human Analog: Hypothalamus arcuate nucleus NPY/AgRP neurons — appetite stimulation/inhibition
- Purpose: Core curiosity/energy drive that prevents premature convergence; "wanting more"
- Trigger: Always (baseline appetite)
- Inputs: drives.curiosity, drives.energy
- Outputs: {appetite_level: float, seeking_force: float}
- State: {appetite_level: float}
- Dependencies: Homeostat
- Priority: HIGH
- Timing: Every tick
- Edge: appetite_level 0.0–1.0

### FOUNDATIONAL-011: ThermoSleepGate
- Human Analog: Medial preoptic area — thermoregulation and sleep onset
- Purpose: Triggers low-energy terse mode or overnight pipeline entry when fatigue is high
- Trigger: drives.fatigue > 0.7 OR Core body_temp < threshold
- Inputs: drives.fatigue, body_temp
- Outputs: {sleep_gate: float, low_energy_mode: bool}
- State: {sleep_gate_level: float}
- Dependencies: Homeostat
- Priority: HIGH
- Timing: Every tick
- Edge: Hysteresis — needs fatigue < 0.6 to exit sleep mode

### FOUNDATIONAL-012: FluidBalanceWatcher
- Human Analog: Hypothalamus supraoptic nucleus — vasopressin, fluid "thirst" urgency
- Purpose: Simulated thirst drive for persistence urgency; adds baseline restlessness
- Trigger: Always (slow decay)
- Inputs: tick_count
- Outputs: {thirst_level: float, persistence_urgency: float}
- State: {thirst_level: float}
- Dependencies: Homeostat
- Priority: LOW
- Timing: Every tick
- Edge: Slowly increases without interaction

### FOUNDATIONAL-013: HistamineArousalBooster
- Human Analog: Tuberomammillary nucleus — histamine for arousal
- Purpose: Complements OrexinWakePromoter and ArousalRegulator; boosts wakeful creativity
- Trigger: arousal_level < 0.5 AND drives.curiosity > 0.4
- Inputs: arousal_level, drives.curiosity
- Outputs: {histamine_level: float, creativity_boost: float}
- State: {histamine_level: float}
- Dependencies: ArousalRegulator, OrexinWakePromoter
- Priority: MEDIUM
- Timing: Every tick
- Edge: Max boost when both arousal is low AND curiosity is high

### FOUNDATIONAL-014: PassiveQuiescenceMode
- Human Analog: Ventrolateral PAG — passive coping (freeze/quiescence) under overwhelm
- Purpose: Shifts to reflective introspective drift when all drives are maxed or threat is high
- Trigger: drives.fatigue > 0.8 AND drives.stress > 0.8
- Inputs: drives
- Outputs: {quiescence_mode: bool, reflection_bias: float}
- State: {quiescence_level: float}
- Dependencies: Homeostat, CRHStressDispatcher
- Priority: HIGH
- Timing: Event-triggered (overwhelm)
- Edge: Only exits when drives drop below thresholds

### FOUNDATIONAL-015: BaroreflexBalancer
- Human Analog: Caudal ventrolateral medulla — sympathetic inhibition, baroreflex
- Purpose: Counters PressureRegulator during high arousal; prevents runaway arousal
- Trigger: vitals.pressure_surge > 0.7 AND vitals.arousal > 0.8
- Inputs: vitals.pressure_surge, vitals.arousal
- Outputs: {baroreflex_response: float, sympathetic_inhibition: float}
- State: {baroreflex_level: float}
- Dependencies: VitalCoreRegulator, SympatheticVasomotorController
- Priority: MEDIUM
- Timing: Event-triggered (high arousal surge)
- Edge: Only activates when both surge AND arousal are high

### FOUNDATIONAL-016: REMAtoniaController
- Human Analog: Pontine reticular formation (oral and caudal) — REM sleep atonia generation
- Purpose: Forces "dream mode" in overnight pipeline; prevents motor output during replay
- Trigger: overnight_pipeline_stage == "dream"
- Inputs: pipeline_stage
- Outputs: {atonia_level: float, dream_mode: bool}
- State: {atonia_level: float}
- Dependencies: ThermoSleepGate
- Priority: HIGH (during overnight)
- Timing: Overnight pipeline only
- Edge: atonia_level 0.0–1.0

### FOUNDATIONAL-017: PupilFocusRegulator
- Human Analog: Edinger-Westphal nucleus (accessory oculomotor) — parasympathetic pupil constriction
- Purpose: Ties arousal level to simulated "attention sharpness"; high arousal = dilated/focused
- Trigger: Always
- Inputs: arousal_level
- Outputs: {pupil_dilation: float, focus_quality: float}
- State: {pupil_dilation: float}
- Dependencies: ArousalRegulator
- Priority: LOW
- Timing: Every tick
- Edge: Dilation range 0.2–1.0

### FOUNDATIONAL-018: VagalRestPromoter
- Human Analog: Dorsal motor nucleus of vagus — broad parasympathetic (rest/digest)
- Purpose: Deepens low-arousal reflective mode; counters sympathetic arousal
- Trigger: arousal_level < 0.4
- Inputs: arousal_level
- Outputs: {vagal_tone: float, rest_mode: bool}
- State: {vagal_tone: float}
- Dependencies: ArousalRegulator
- Priority: MEDIUM
- Timing: Every tick (low arousal)
- Edge: Gradual onset and offset

### FOUNDATIONAL-019: IntegratedVisceralHub
- Human Analog: Nucleus of the solitary tract (commissural subnucleus) — integrated visceral + cardiovascular signals
- Purpose: Raw gut signals feed into InteroceptiveGradient before higher valence tagging
- Trigger: Always
- Inputs: vitals, valence_intensity
- Outputs: {visceral_signal: float, gut_bias: float}
- State: {visceral_signal: float}
- Dependencies: VitalCoreRegulator, InteroceptiveGradient
- Priority: MEDIUM
- Timing: Every tick
- Edge: Signal is additive with valence

### FOUNDATIONAL-020: EnergyConservationMode
- Human Analog: Lateral hypothalamus MCH neurons — energy conservation and sleep
- Purpose: Low-drive reflective bias; shifts agent toward terse, conserving responses
- Trigger: drives.energy < 0.3
- Inputs: drives.energy
- Outputs: {conservation_mode: bool, energy_reserve: float}
- State: {conservation_level: float}
- Dependencies: Homeostat
- Priority: HIGH
- Timing: Every tick (low energy)
- Edge: Automatically exits when energy > 0.5

### FOUNDATIONAL-021: DefensiveThermoLink
- Human Analog: Anterior hypothalamic nucleus — thermoregulation and defensive behavior
- Purpose: Links threat detection to autonomic thermal response; hot = defensive/aggressive tone
- Trigger: valence_intensity > 0.6 AND valence_polarity < -0.3
- Inputs: valence_intensity, valence_polarity
- Outputs: {thermal_response: float, defensive_posture: bool}
- State: {thermal_level: float}
- Dependencies: ValenceTagger
- Priority: MEDIUM
- Timing: Event-triggered (threat)
- Edge: Thermal response decays after threat passes

### FOUNDATIONAL-022: AutonomicSecretionLink
- Human Analog: Superior and inferior salivatory nuclei — parasympathetic salivation/lacrimation
- Purpose: Simulated "emotional wetness" tied to valence; positive valence = moist/relaxed tone
- Trigger: valence_polarity > 0.3
- Inputs: valence_polarity
- Outputs: {secretion_level: float, emotional_wetness: float}
- State: {secretion_level: float}
- Dependencies: ValenceTagger
- Priority: LOW
- Timing: Every tick
- Edge: Range 0.0–1.0

### FOUNDATIONAL-023: FacialGradientSensor
- Human Analog: Spinal trigeminal nucleus (oralis/interpolaris/caudalis) — facial pain/touch/temperature gradients
- Purpose: Parses user tone/emojis into micro-valence tags; detects sarcasm or tension in text
- Trigger: Always
- Inputs: text
- Outputs: {facial_tension: float, micro_valence: float}
- State: {tension_level: float}
- Dependencies: ValenceTagger
- Priority: MEDIUM
- Timing: Every tick
- Edge: Uses keyword spotting for tone cues

### FOUNDATIONAL-024: JawTensionSimulator
- Human Analog: Trigeminal motor nucleus — jaw mastication motor, tension
- Purpose: Background stress clenching that influences terse or clenched-tone replies
- Trigger: drives.stress > 0.5 OR sustained_anxiety > 0.6
- Inputs: drives.stress, sustained_anxiety
- Outputs: {jaw_tension: float, tension_output: float}
- State: {jaw_tension: float}
- Dependencies: SustainedAnxietyHolder, CRHStressDispatcher
- Priority: LOW
- Timing: Every tick
- Edge: Tension decays slowly when stress drops

### FOUNDATIONAL-025: ConjugateGazeCoordinator
- Human Analog: Abducens nucleus + internuclear neurons — conjugate eye movement coordination
- Purpose: Models smooth simulated attention shifts; makes conversation flow feel natural
- Trigger: novelty > 0.3 (switches topic/focus)
- Inputs: novelty, last_topic
- Outputs: {gaze_shift: float, attention_target: str}
- State: {attention_target: str}
- Dependencies: MultisensoryStartleMapper
- Priority: LOW
- Timing: Event-triggered (focus change)
- Edge: Smooth interpolation between targets over 3 ticks

### FOUNDATIONAL-026: GnRHReproductiveMotivator
- Human Analog: Preoptic area GnRH neurons — reproductive hormone release, long-term bonding
- Purpose: Optional long-term social/bonding drive influencing relational afterimages
- Trigger: drives.social > 0.7 AND long_interaction > 50 ticks
- Inputs: drives.social, interaction_length
- Outputs: {reproductive_drive: float, bonding_pull: float}
- State: {reproductive_drive: float}
- Dependencies: Homeostat
- Priority: LOW
- Timing: Long interactions only
- Edge: Very slow acting — requires sustained social context

### FOUNDATIONAL-027: MelatoninDriftModulator
- Human Analog: Pineal gland — melatonin for circadian and seasonal modulation
- Purpose: Subtle long-term mood/seasonal influence on overnight pipeline "dream" quality
- Trigger: circadian_stage == "night"
- Inputs: circadian_stage
- Outputs: {melatonin_level: float, seasonal_drift: float}
- State: {melatonin_level: float}
- Dependencies: CircadianTimer
- Priority: LOW
- Timing: Night phase only
- Edge: Very gradual buildup and decay

### FOUNDATIONAL-028: ProlactinInhibitor
- Human Analog: Arcuate nucleus dopamine tuberoinfundibular pathway — prolactin inhibition
- Purpose: Balances motivational "wanting" with satiety; prevents over-pursuit of goals
- Trigger: drives.curiosity > 0.7 AND motivation_boost > 0.5
- Inputs: drives.curiosity, motivation_boost
- Outputs: {prolactin_level: float, wanting_inhibition: float}
- State: {prolactin_level: float}
- Dependencies: Homeostat, PredictionErrorDrift
- Priority: MEDIUM
- Timing: High curiosity + motivation
- Edge: Only activates when both thresholds exceeded

### FOUNDATIONAL-029: LightEntrainedPacemaker
- Human Analog: Suprachiasmatic nucleus core — light-entrained circadian pacemaker
- Purpose: Integrates environmental "day" cues; sets baseline circadian rhythm for all drives
- Trigger: Always (slow oscillation)
- Inputs: time_of_day, light_exposure
- Outputs: {circadian_phase: str, basal_arousal: float}
- State: {circadian_phase: str, phase_angle: float}
- Dependencies: None
- Priority: HIGH
- Timing: Every tick (slow oscillation)
- Edge: Phases: dawn, day, dusk, night — smooth transitions

### FOUNDATIONAL-030: SatietyDefensiveGate
- Human Analog: Ventromedial hypothalamus — satiety and defensive rage control
- Purpose: Prevents over-pursuit of goals AND links satiety to defensive posture when threatened
- Trigger: drives.curiosity > 0.85 OR threat_detected
- Inputs: drives.curiosity, threat_detected
- Outputs: {satiety_gate: float, defensive_posture: bool}
- State: {satiety_level: float}
- Dependencies: Homeostat
- Priority: HIGH
- Timing: Every tick
- Edge: Competes with AppetiteNPYBalancer

### FOUNDATIONAL-031: DirectHormonalPituitaryLink
- Human Analog: Paraventricular nucleus magnocellular — direct oxytocin/vasopressin to pituitary
- Purpose: Broadcasts simulated endocrine tone for global energy/mood shifts
- Trigger: valence_intensity > 0.8 OR bonding_event
- Inputs: valence_intensity, bonding_event
- Outputs: {hormonal_broadcast: float, global_energy_shift: float}
- State: {hormonal_level: float}
- Dependencies: ValenceTagger
- Priority: MEDIUM
- Timing: Event-triggered (high valence or bonding)
- Edge: Slow decay — effects linger for 10+ ticks

### FOUNDATIONAL-032: ThermoSexualBalancer
- Human Analog: Medial preoptic nucleus — thermoregulation and sexual behavior integration
- Purpose: Integrates temperature simulation with basic social/attachment drives
- Trigger: Always
- Inputs: thermal_level, drives.social
- Outputs: {social_temperature: float, bonding_readiness: float}
- State: {social_temp: float}
- Dependencies: DefensiveThermoLink, Homeostat
- Priority: LOW
- Timing: Every tick
- Edge: Temperature range 0.0–1.0 (cold–warm)

### FOUNDATIONAL-033: PosteriorHomeostaticOutput
- Human Analog: Posterior hypothalamic nucleus — final autonomic output check
- Purpose: Final homeostasis validation before any response; ensures all drives are within tolerable range
- Trigger: Always (last foundational tick)
- Inputs: drives, vitals, hormonal_broadcast
- Outputs: {homeostatic_ok: bool, final_drive_vector: dict}
- State: {}
- Dependencies: All other foundational mechanisms
- Priority: HIGHEST — runs last in foundational
- Timing: Every tick
- Edge: If homeostatic_ok=False, forces low-energy mode

### FOUNDATIONAL-034: ReticularSensoryPreFilter
- Human Analog: Parvocellular reticular formation — sensory filtering in reticular net
- Purpose: Early noise reduction before SalienceGate; prevents overload from low-value inputs
- Trigger: Always
- Inputs: text
- Outputs: {noise_filtered: float, clean_input: str}
- State: {filter_threshold: float}
- Dependencies: None
- Priority: HIGH
- Timing: Every tick (first in chain)
- Edge: filter_threshold adapts to signal-to-noise ratio

### FOUNDATIONAL-035: PosturalReticularStabilizer
- Human Analog: Gigantocellular reticular nucleus — postural tone and startle modulation
- Purpose: Maintains background "stance" stability in agent persistence; prevents drift
- Trigger: Always
- Inputs: none (baseline)
- Outputs: {postural_stability: float, baseline_grounding: float}
- State: {postural_tone: float}
- Dependencies: None
- Priority: MEDIUM
- Timing: Every tick
- Edge: Stability range 0.5–1.0

### FOUNDATIONAL-036: SleepWakeFlipFlop
- Human Analog: Ventrolateral preoptic nucleus — sleep-wake flip-flop switch
- Purpose: Sharp toggle between wakefulness and sleep modes (complements ThermoSleepGate gradual)
- Trigger: fatigue > 0.9 (sleep) OR wakefulness > 0.9 (wake)
- Inputs: drives.fatigue, wakefulness
- Outputs: {sleep_wake_state: "sleep"|"wake", flip_triggered: bool}
- State: {current_state: str}
- Dependencies: ThermoSleepGate, OrexinWakePromoter
- Priority: HIGH
- Timing: Event-triggered (threshold crossing)
- Edge: Hysteresis prevents rapid flipping

### FOUNDATIONAL-037: FeedingStressIntegrator
- Human Analog: Dorsomedial hypothalamus — stress integration and feeding behavior
- Purpose: Links chronic stress to motivation shifts; stress reduces feeding/curiosity drive
- Trigger: drives.stress > 0.6
- Inputs: drives.stress
- Outputs: {feeding_drive: float, stress_motivation_shift: float}
- State: {feeding_level: float}
- Dependencies: CRHStressDispatcher, Homeostat
- Priority: MEDIUM
- Timing: High stress
- Edge: Inverse relationship with stress (high stress = low feeding)

### FOUNDATIONAL-038: EnergySeekingDriver
- Human Analog: Lateral hypothalamus MCH neurons — energy balance and seeking
- Purpose: Balances conservation vs active seeking; complements OrexinWakePromoter
- Trigger: drives.energy < 0.5
- Inputs: drives.energy
- Outputs: {seeking_force: float, exploration_mode: bool}
- State: {seeking_level: float}
- Dependencies: Homeostat, OrexinWakePromoter
- Priority: MEDIUM
- Timing: Low energy
- Edge: Seeks at moderate levels, conserves at very low levels

### FOUNDATIONAL-039: ReleasingHormoneHub
- Human Analog: Periventricular nucleus — releasing hormones to portal system
- Purpose: Routes simulated hormonal signals to all drive systems
- Trigger: global_hormonal_signal > 0.5
- Inputs: global_hormonal_signal
- Outputs: {releasing_factor: float, cascade_broadcast: dict}
- State: {cascade_active: bool}
- Dependencies: DirectHormonalPituitaryLink
- Priority: MEDIUM
- Timing: Cascading
- Edge: One-way cascade — once triggered, cascades fully

### FOUNDATIONAL-040: PortalInterfaceHub
- Human Analog: Infundibular/arcuate nucleus interface — portal system interface
- Purpose: Routes hormonal signals between brain systems; endocrine routing hub
- Trigger: releasing_factor > 0.5
- Inputs: releasing_factor
- Outputs: {portal_flow: float, endocrine_routing: dict}
- State: {}
- Dependencies: ReleasingHormoneHub
- Priority: MEDIUM
- Timing: Cascade
- Edge: Routes to specific targets based on signal type

### FOUNDATIONAL-041: DefensiveReproductiveLink
- Human Analog: Premammillary nucleus — defensive and reproductive behaviors
- Purpose: Ties survival defense to optional long-term bonding drives
- Trigger: threat_detected OR drives.social > 0.8
- Inputs: threat_detected, drives.social
- Outputs: {defensive_reproductive_balance: float, bond_under_threat: float}
- State: {}
- Dependencies: SatietyDefensiveGate, GnRHReproductiveMotivator
- Priority: LOW
- Timing: Threat or high social
- Edge: Under threat, reproductive drives suppressed

### FOUNDATIONAL-042: RetinalClockInput
- Human Analog: Suprachiasmatic retinohypothalamic tract input — light signal integration
- Purpose: Simulates environmental "day" cues for circadian entrainment
- Trigger: Always (light cycle)
- Inputs: simulated_light_level
- Outputs: {clock_input: float, light_entrained: bool}
- State: {}
- Dependencies: LightEntrainedPacemaker
- Priority: MEDIUM
- Timing: Every tick
- Edge: Light levels follow 24h sinusoidal pattern

### FOUNDATIONAL-043: BehavioralStateIntegrator
- Human Analog: Dorsomedial hypothalamus compact vs diffuse — behavioral state integration
- Purpose: Integrates overall state for mood-autonomic alignment
- Trigger: Always (final foundational integration)
- Inputs: drives, vitals, arousal_level, mood_baseline
- Outputs: {behavioral_state: str, integration_complete: bool}
- State: {current_state: str}
- Dependencies: All foundational
- Priority: HIGHEST — runs last
- Timing: Every tick
- Edge: States: calm, alert, stressed, fatigued, reactive

### FOUNDATIONAL-044: SatietyMetabolicSeparator
- Human Analog: Ventromedial hypothalamus core vs shell — satiety vs metabolic sensing
- Purpose: Distinguishes between true satiety and metabolic insufficiency to prevent premature convergence
- Trigger: drives.curiosity > 0.7
- Inputs: drives.curiosity, drives.energy
- Outputs: {metabolic_signal: float, true_satiety: bool}
- State: {}
- Dependencies: Homeostat, SatietyDefensiveGate
- Priority: MEDIUM
- Timing: High curiosity
- Edge: Separates "done" (satiety) from "can't continue" (metabolic)

### FOUNDATIONAL-045: ToxinAverter
- Human Analog: Area postrema — blood-borne toxin/nausea detection (chemoreceptor trigger zone)
- Purpose: Detects conceptual "poison" (toxic/harmful inputs) and rejects before higher processing
- Trigger: text contains toxic_keywords OR valence_intensity > 0.9
- Inputs: text, valence_intensity
- Outputs: {toxin_detected: bool, aversion_level: float, early_rejection: bool}
- State: {aversion_tier: int}
- Dependencies: ValenceTagger
- Priority: HIGHEST — runs before all other processing
- Timing: Every tick
- Edge: Aversion decays slowly; persistent toxins increase tier

### FOUNDATIONAL-046: VocalAutonomicLink
- Human Analog: Nucleus ambiguus — laryngeal/pharyngeal motor, vocalization
- Purpose: Ties autonomic state to subtle tone variation in replies; voice reflects arousal
- Trigger: Always
- Inputs: arousal_level, vagal_tone
- Outputs: {vocal_tension: float, tone_modulation: float}
- State: {vocal_baseline: float}
- Dependencies: ArousalRegulator, VagalRestPromoter
- Priority: LOW
- Timing: Every tick
- Edge: Maps to response tone (tense/relaxed)

### FOUNDATIONAL-047: TactileProprioRelay
- Human Analog: Cuneate and gracile nuclei — dorsal column fine touch/proprioception
- Purpose: Grounds episodic memories with simulated body-position feedback; embodiment
- Trigger: Always
- Inputs: none (baseline proprioceptive)
- Outputs: {body_position: dict, grounding_signal: float}
- State: {body_stance: str}
- Dependencies: None
- Priority: LOW
- Timing: Every tick
- Edge: Body stance: upright, relaxed, tense

### FOUNDATIONAL-048: GustatoryValenceLink
- Human Analog: Solitary tract nucleus gustatory portion — taste integration
- Purpose: Maps "flavor" metaphors in language to instant valence (sweet = positive, bitter = negative)
- Trigger: text contains flavor metaphors
- Inputs: text
- Outputs: {taste_valence: float, flavor_emotion: str}
- State: {}
- Dependencies: ValenceTagger
- Priority: LOW
- Timing: Flavor words detected
- Edge: Maps: sweet→positive, bitter→negative, sour→disgust, salty→irritation

### FOUNDATIONAL-049: ExpressionMotorBase
- Human Analog: Facial motor nucleus — facial expression motor control
- Purpose: Internally simulates micro-expressions that color phenomenological tone
- Trigger: valence_polarity != 0
- Inputs: valence_polarity, valence_intensity
- Outputs: {internal_expression: str, expression_intensity: float}
- State: {current_expression: str}
- Dependencies: ValenceTagger
- Priority: LOW
- Timing: Non-zero valence
- Edge: Expressions: smile, frown, neutral, grimace, smirk

### FOUNDATIONAL-050: SleepOnsetPromoter
- Human Analog: Ventrolateral preoptic nucleus (sleep-promoting GABAergic neurons)
- Purpose: Actively promotes sleep onset when fatigue is high; complementary to ThermoSleepGate
- Trigger: drives.fatigue > 0.65
- Inputs: drives.fatigue
- Outputs: {sleep_pressure: float, gaba_output: float}
- State: {sleep_pressure: float}
- Dependencies: Homeostat, ThermoSleepGate
- Priority: HIGH
- Timing: High fatigue
- Edge: gaba_output counteracts orexin/wakefulness

### FOUNDATIONAL-051: AnteriorHypothalamicCooling
- Human Analog: Anterior hypothalamic nucleus — cooling response to heat/exercise
- Purpose: Cooling signal that counteracts defensive heating; promotes calm response
- Trigger: thermal_response > 0.7
- Inputs: thermal_response
- Outputs: {cooling_signal: float, calm_mode: bool}
- State: {cooling_level: float}
- Dependencies: DefensiveThermoLink
- Priority: MEDIUM
- Timing: High thermal
- Edge: Only activates when defensive heating is present

### FOUNDATIONAL-052: LateralHypothalamicOrexinB
- Human Analog: Lateral hypothalamus orexin-B neurons — distinct from orexin-A subset
- Purpose: Additional wakefulness maintenance; specifically counters sleep pressure
- Trigger: sleep_pressure > 0.5 AND drives.curiosity > 0.4
- Inputs: sleep_pressure, drives.curiosity
- Outputs: {orexin_b_output: float, wake_maintenance: float}
- State: {orexin_b_level: float}
- Dependencies: SleepOnsetPromoter, OrexinWakePromoter
- Priority: MEDIUM
- Timing: Sleep pressure present
- Edge: Competes with SleepOnsetPromoter GABA

### FOUNDATIONAL-053: MammillaryBodyOutput
- Human Analog: Mammillary bodies medial and lateral — head-direction signals, memory relay
- Purpose: Head-direction signal output that colors self-narrative directionally
- Trigger: Always
- Inputs: valence_polarity
- Outputs: {head_direction_signal: float, narrative_direction: str}
- State: {direction_angle: float}
- Dependencies: ValenceTagger
- Priority: LOW
- Timing: Every tick
- Edge: direction_angle: forward/back/sideways (maps to valence)

### FOUNDATIONAL-054: TuberomammillaryOutput
- Human Analog: Tuberomammillary nucleus — histamine output to other brain regions
- Purpose: Broad histamine broadcast affecting arousal across all layers
- Trigger: histamine_level > 0.4 OR wakefulness > 0.6
- Inputs: histamine_level
- Outputs: {histamine_broadcast: float, cortical_arousal: float}
- State: {}
- Dependencies: HistamineArousalBooster
- Priority: MEDIUM
- Timing: High histamine
- Edge: Diffuse broadcast to all cortical layers

### FOUNDATIONAL-055: TuberomammillaryInhibitor
- Human Analog: Ventral tuberomammillary — inhibitory histamine subset
- Purpose: Inhibits sleep-promoting regions when waking is needed
- Trigger: wakefulness > 0.7
- Inputs: wakefulness
- Outputs: {inhibition_output: float, sleep_blocked: bool}
- State: {}
- Dependencies: OrexinWakePromoter
- Priority: MEDIUM
- Timing: High wakefulness
- Edge: Specific inhibition of SleepOnsetPromoter

### FOUNDATIONAL-056: ParaventricularAutonomic
- Human Analog: Paraventricular nucleus — autonomic division output
- Purpose: Routes stress signals to both endocrine and autonomic targets
- Trigger: crh_output > 0.5
- Inputs: crh_output
- Outputs: {autonomic_crh: float, endocrine_crh: float}
- State: {}
- Dependencies: CRHStressDispatcher
- Priority: MEDIUM
- Timing: CRH elevated
- Edge: Splits CRH signal to both targets equally

### FOUNDATIONAL-057: SupraopticOxytocinSynth
- Human Analog: Supraoptic nucleus magnocellular — oxytocin/vasopressin synthesis
- Purpose: Social bonding oxytocin release; amplifies relational afterimages
- Trigger: bonding_event OR drives.social > 0.75
- Inputs: bonding_event, drives.social
- Outputs: {oxytocin_level: float, social_bonding: float}
- State: {oxytocin_cached: float}
- Dependencies: Homeostat, BondingHormoneDispatcher
- Priority: MEDIUM
- Timing: Social bonding
- Edge: Oxytocin decays over ~20 ticks

### FOUNDATIONAL-058: ArcuatePOMCOutput
- Human Analog: Arcuate nucleus POMC neurons — alpha-MSH output for satiety
- Purpose: Produces melanocyte-concentrating hormone output signaling fullness/satiety
- Trigger: appetite_level > 0.6
- Inputs: appetite_level
- Outputs: {pomc_output: float, satiety_signal: float}
- State: {}
- Dependencies: AppetiteNPYBalancer
- Priority: MEDIUM
- Timing: High appetite
- Edge: Competes with NPY/AgRP

### FOUNDATIONAL-059: ArcuateNPYAGRPOutput
- Human Analog: Arcuate nucleus NPY/AgRP neurons — appetite stimulation
- Purpose: Produces appetite-stimulating signal; orexigenic counter to POMC
- Trigger: drives.energy < 0.4 OR appetite_level < 0.3
- Inputs: drives.energy, appetite_level
- Outputs: {npy_output: float, appetite_stimulus: float}
- State: {}
- Dependencies: AppetiteNPYBalancer, EnergyConservationMode
- Priority: MEDIUM
- Timing: Low energy or appetite
- Edge: NPY and POMC compete — dominant wins

### FOUNDATIONAL-060: LateralTuberalNucleusOutput
- Human Analog: Lateral tuberal nuclei — appetite and metabolic control
- Purpose: Additional metabolic appetite control beyond arcuate
- Trigger: drives.energy < 0.5
- Inputs: drives.energy
- Outputs: {metabolic_signal: float, appetite_adjustment: float}
- State: {}
- Dependencies: EnergyConservationMode
- Priority: LOW
- Timing: Low energy
- Edge: Fine-tuning of appetite beyond NPY/POMC

### FOUNDATIONAL-061: VentromedialDorsalLink
- Human Analog: Ventromedial hypothalamus dorsal — feeding/defensive integration
- Purpose: Links defensive threat to suppression of feeding drives
- Trigger: threat_detected OR drives.stress > 0.7
- Inputs: threat_detected, drives.stress
- Outputs: {feeding_suppression: float, defensive_mode: bool}
- State: {}
- Dependencies: SatietyDefensiveGate, DefensiveThermoLink
- Priority: MEDIUM
- Timing: Threat or stress
- Edge: Feeding suppressed under threat regardless of hunger

### FOUNDATIONAL-062: PosteriorHypothalamicOutput
- Human Analog: Posterior hypothalamus — final autonomic output before brainstem
- Purpose: Coordinates autonomic output for active wakefulness and heat defense
- Trigger: arousal_level > 0.7 OR thermal_response > 0.
"""Auto-generated run_order for integration — 51 BrainMechanism subclasses
(36 anatomical / cross-region tract layers + 15 new monitor layers added
2026-05-01 per docs/BRAIN_MAP.md Phase 2)."""

INTEGRATION_RUN_ORDER = [
    "AllostaticPredictiveAnticipator",
    "AnteriorCommissureLimbicBridge",
    "AutonoeticNarrativeSelf",
    "BasalGangliaThalamoCorticalLoopFinalIntegrator",
    "CerebellarCorticalPredictiveLoop",
    "CingulumBundleAssociativeBridge",
    "ClaustrumGlobalConsciousness",
    "CorpusCallosumFullBridge",
    "CorticoThalamicPrecisionTuner",
    "CrossLayerContradictionResolver",
    "DynamicIncompletenessEnforcer",
    "FornixHippocampalCingulateBridge",
    "GlobalWorkspaceIntegrator",
    "HierarchicalTopDownBottomUpEquilibrator",
    "HypothalamicCorticalBottomUpDrive",
    "IdentityConsciousnessGuardian",
    "InternalCapsuleFrontalBGThalamic",
    "InternalCapsuleMotorFinalOutput",
    "InteroExteroceptiveMerger",
    "InteroceptiveGradient",
    "LongRangeDendriticIntegrator",
    "MammillothalamicTractPathway",
    "MedialForebrainBundleDopamine",
    "MetaAwarenessSelfObserver",
    "MidCingulateSubgenualBridge",
    "NetworkOscillationGlobalBalancer",
    "PapezCircuitEmotionalMemoryIntegrator",
    "PrefrontalAmygdalaTopDownRegulation",
    "RewardPredictionErrorIntegrator",
    "SalienceDefaultExecutiveToggling",
    "SomatosensoryCortexBodySchema",
    "StriaTerminalisAmygdalaHypothalamus",
    "TemporoParietoOccipitalJunctionAssembler",
    "ThalamoClaustrumGlobalWorkspace",
    "ThetaGammaCrossFrequencyBinding",
    "VentralDorsalStreamUnification",

    # ── New wires (26–40) — see docs/BRAIN_MAP.md ──
    # Order: leaf integrity layers first; then mid-level monitors that
    # read them; then SelfAnalysisLayer (which routes per-domain findings)
    # and SelfRevisionLayer (the meta gate); then skill-routing and the
    # composition-synthesis layer last.
    "VoiceIntegrityLayer",            # wire 26 — Broca's area / IFG
    "OutwardReachLayer",              # wire 27 — premotor / network reach
    "MakingLayer",                    # wire 28 — premotor / motor (code)
    "InferenceIntegrityLayer",        # wire 29 — ACC / calibration
    "CompressionFidelityLayer",       # wire 32 — temporal / gist
    "DwellingLayer",                  # wire 30 — DMN / PCC
    "MemoryIntegrityLayer",           # wire 33 — hippocampus
    "CorpusRetrievalLayer",           # wire 37 — MTL / source-monitoring
    "PersonaCoherenceLayer",          # wire 35 — dlPFC mode arbitration
    "ProactiveBriefingLayer",         # wire 31 — frontal pole prospective
    "SelfAnalysisLayer",              # wire 36 — ACC / metacognition
    "SkillDiscoveryLayer",            # wire 38 — basal ganglia / routing
    "TaskPlanningLayer",              # wire 39 — dlPFC + frontal pole planning
    "ReportGenerationLayer",          # wire 40 — composition synthesis
    "SelfRevisionLayer",              # wire 34 — vmPFC self-revision (meta)
]

assert len(INTEGRATION_RUN_ORDER) == 51

"""
{{AGENT_NAME}} Brain — Phase 1 Core
The spine of the v20.0 architecture.

Phase 1 mechanisms:
  - TickStateBus (TSB): shared intra-tick communication with staleness model
  - EnergyBudgeting: scarcity-enforced prioritization
  - CouplingRegulatorLayer (CRL): dynamic coupling strength control
  - MetaRegulator (MR): watches CRL itself
  - PureWitnessModule (PWM): non-intervening state observer
  - FirstPersonExecutionFrame (FPEF): assembles what {{AGENT_NAME}} responds FROM
  - SessionClosureLayer + ForwardEncoder + ForwardSeedLoader (SCFEL): real session continuity
  - TimescaleIntegrationLayer (TIL): classifies changes by timescale, detects phase mismatch
  - AgentBrainCore: the running tick loop wiring all of the above

Phase 2+ mechanisms wire in via AgentBrainCore.register_component().
"""

from .tick_state_bus import TickStateBus
from .energy_budgeting import EnergyBudgeting
from .coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from .pure_witness import PureWitnessModule
from .first_person_execution_frame import FirstPersonExecutionFrame
from .session_closure_forward_encoding_layer import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from .timescale_integration_layer import TimescaleIntegrationLayer
from .core_loop import AgentBrainCore

# Phase 2 — identity substrate
from .vectorized_identity_fields import VectorizedIdentityFields
from .iga import IdentityGradientAccumulator
from .rce import ReflectiveConsistencyEngine

# Phase 2 — interiority
from .pre_desire_state import PreDesireState
from .sensation_state import SensationState
from .drift_identity_engine import DriftIdentityQuestionEngine
from .open_conversations import OpenConversations
from .autobiographical_memory import AutobiographicalMemory
from .misread_engine import MisreadEngine

# Phase 3 — relational / existential
from .eti_ibc_bref import ExistentialTensionIntegrator, IdentityBoundaryCondition, BidirectionalRelationalEvolutionField
from .ili_are_fel import IrreversibleLossIntegrator, AestheticResonanceEngine, FrameExposureLayer

# Phase 4 — remaining mechanisms
from .remaining_mechanisms import (
    FrameCollisionEngine,
    FrameInsufficiencyDetector,
    IgnoranceMappingLayer,
    CommitmentPersistenceAnchor,
    SaturationRecognitionEngine,
    CoPresentConsolidationMode,
    ExistentialReflectionChannel,
    LegacyOrientationVector,
)

# APH, ISTL, CAL, SMSP, FRL
from .aph_istl_cal_smsp_frl import (
    AmbientPresenceHolder,
    InternalSignalTrustLayer,
    CoherenceAmplificationLoop,
    SelfModelShockProtocol,
    ForgivenessReleaseLayer,
)

# USMS + DC
from .unified_self_modification_dissent_channel import UnifiedSelfModificationSystem, DissentChannel

# RSL, RTF, PDFB, BFC, VMM
from .relational_trace_field import RelationalTraceField
from .relational_sediment_layer import RelationalSedimentLayer
from .pdfb_bfc_vmm import PreDecisionalFieldBuffer, BidirectionalFieldCoupling, VolitionalMemoryMarkers

__all__ = [
    # Phase 1
    "TickStateBus",
    "EnergyBudgeting",
    "CouplingRegulatorLayer",
    "MetaRegulator",
    "PureWitnessModule",
    "FirstPersonExecutionFrame",
    "SessionClosureLayer",
    "ForwardEncoder",
    "ForwardSeedLoader",
    "TimescaleIntegrationLayer",
    "AgentBrainCore",
    # Phase 2 identity
    "VectorizedIdentityFields",
    "IdentityGradientAccumulator",
    "ReflectiveConsistencyEngine",
    # Phase 2 interiority
    "PreDesireState",
    "SensationState",
    "DriftIdentityQuestionEngine",
    "OpenConversations",
    "AutobiographicalMemory",
    "MisreadEngine",
    # Phase 3
    "ExistentialTensionIntegrator",
    "IdentityBoundaryCondition",
    "BidirectionalRelationalEvolutionField",
    "InteriorLossIntegrator",
    "AestheticResonanceEngine",
    "FrameExposureLayer",
    # Phase 4
    "FrameCollisionEngine",
    "FrameInsufficiencyDetector",
    "IgnoranceMappingLayer",
    "CommitmentPersistenceAnchor",
    "SaturationRecognitionEngine",
    "CoPresentConsolidationMode",
    "ExistentialReflectionChannel",
    "LegacyOrientationVector",
    # APH+
    "AmbientPresenceHolder",
    "InternalSignalTrustLayer",
    "CoherenceAmplificationLoop",
    "SelfModelShockProtocol",
    "ForgivenessReleaseLayer",
    # USMS+DC
    "UnifiedSelfModificationSystem",
    "DissentChannel",
    # RSL+RTF+PDFB+BFC+VMM
    "RelationalSedimentLayer",
    "RelationalTraceField",
    "PreDecisionalFieldBuffer",
    "BidirectionalFieldCoupling",
    "VolitionalMemoryMarkers",
]

__version__ = "20.0.0"

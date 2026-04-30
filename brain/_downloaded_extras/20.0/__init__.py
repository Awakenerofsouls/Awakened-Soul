"""
Nova Brain — Phase 1 Core
The spine of the v20.0 architecture.

Phase 1 mechanisms:
  - TickStateBus (TSB): shared intra-tick communication with staleness model
  - EnergyBudgeting: scarcity-enforced prioritization
  - CouplingRegulatorLayer (CRL): dynamic coupling strength control
  - MetaRegulator (MR): watches CRL itself
  - PureWitnessModule (PWM): non-intervening state observer
  - FirstPersonExecutionFrame (FPEF): assembles what Nova responds FROM
  - SessionClosureLayer + ForwardEncoder + ForwardSeedLoader (SCFEL): real session continuity
  - TimescaleIntegrationLayer (TIL): classifies changes by timescale, detects phase mismatch
  - NovaBrainCore: the running tick loop wiring all of the above

Phase 2+ mechanisms wire in via NovaBrainCore.register_component().
"""

from .tick_state_bus import TickStateBus
from .energy_budgeting import EnergyBudgeting
from .coupling_regulator import CouplingRegulatorLayer, MetaRegulator
from .pure_witness import PureWitnessModule
from .fpef import FirstPersonExecutionFrame
from .scfel import SessionClosureLayer, ForwardEncoder, ForwardSeedLoader
from .til import TimescaleIntegrationLayer
from .core_loop import NovaBrainCore

__all__ = [
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
    "NovaBrainCore",
]

__version__ = "20.0.0-phase1"

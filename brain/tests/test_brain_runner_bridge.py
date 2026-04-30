"""
Wire 12 Verification: BrainLayerRunner Bridge to TSB

Tests that brain_runner is integrated into the tick loop, publishes to TSB,
and produces observable empty-state when mechanism layer has no real implementations.

Commit: Wire 12 — brain_runner integrated into tick loop.
"""

import unittest
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from brain.brain_integration import AgentBrainIntegration


class TestBrainRunnerBridge(unittest.TestCase):
    """Tests for Wire 12 — brain_runner bridge to TSB."""

    def setUp(self):
        """Boot fresh integration."""
        self.integration = AgentBrainIntegration()

    def test_brain_runner_instantiated(self):
        """BrainLayerRunner instance exists on integration."""
        self.assertTrue(hasattr(self.integration, "brain_runner"))

    def test_brain_runner_loads_layers(self):
        """BrainLayerRunner loads all five mechanism layers at boot."""
        br = self.integration.brain_runner
        self.assertIsInstance(br.mechanisms, dict)
        # 11 mechanisms: Homeostat + PredictionErrorDrift + ArousalRegulator + ValenceTagger
        #               + SustainedAnxietyHolder + CentralNucleusFearRouter + GutSignalRelay
        #               + InteroceptiveGradient + AttachmentLongingGenerator + PleasureAnchor
        #               + StressActivationAxis
        loaded = len(br.mechanisms)
        self.assertGreaterEqual(loaded, 263,
            f"Expected at least 263 mechanisms, got {loaded}")

    def test_brain_runner_bid_registered(self):
        """brain_runner is registered as a core component."""
        component_names = list(self.integration.core._components.keys())
        self.assertIn("brain_runner", component_names)

    def test_brain_layer_published_to_tsb_after_tick(self):
        """After one tick, TSB contains brain_layer key."""
        # Run one tick via core
        self.integration.core.tick()

        # Read brain_layer from TSB
        brain_layer, fresh = self.integration.core.tsb.read("brain_layer")

        self.assertIsNotNone(brain_layer, "brain_layer must be published to TSB after tick")
        self.assertIsInstance(brain_layer, dict)

    def test_brain_layer_has_fired_tick_marker(self):
        """brain_layer contains _fired_tick=True marker even in empty state."""
        self.integration.core.tick()
        brain_layer, _ = self.integration.core.tsb.read("brain_layer")

        self.assertTrue(brain_layer.get("_fired_tick"), "_fired_tick must be True")

    def test_brain_layer_mechanisms_loaded_marker(self):
        """brain_layer contains _mechanisms_loaded count."""
        self.integration.core.tick()
        brain_layer, _ = self.integration.core.tsb.read("brain_layer")

        self.assertIn("_mechanisms_loaded", brain_layer)
        # _mechanisms_loaded reflects all mechanisms loaded by brain_runner
        # (≥263 across foundational/limbic/subcortical/neocortical/integration —
        # currently 917 after the legacy/brain-root adapter pass)
        self.assertGreaterEqual(brain_layer["_mechanisms_loaded"], 263)

    def test_brain_layer_has_real_brain_fields_with_homeostat(self):
        """With Homeostat loaded, brain_layer contains brain_* output fields."""
        self.integration.core.tick()
        brain_layer, _ = self.integration.core.tsb.read("brain_layer")

        brain_fields = [k for k in brain_layer if k.startswith("brain_")]
        self.assertGreater(len(brain_fields), 0,
            "Homeostat produces brain_* fields")

    def test_brain_layer_observable_state_with_homeostat(self):
        """With Homeostat loaded: fired=True, mechanisms=1, brain_* fields present."""
        self.integration.core.tick()
        brain_layer, _ = self.integration.core.tsb.read("brain_layer")

        # Observable state contract
        self.assertTrue(brain_layer["_fired_tick"])
        self.assertGreaterEqual(brain_layer["_mechanisms_loaded"], 263)
        brain_fields = [k for k in brain_layer if k.startswith("brain_")]
        self.assertGreater(len(brain_fields), 0,
            "3 mechanisms produce brain_* fields")
        self.assertGreaterEqual(len(brain_layer), 2)


if __name__ == "__main__":
    unittest.main()

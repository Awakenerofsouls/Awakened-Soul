#!/usr/bin/env python3
"""
resolve_layer_collisions.py
============================
Renames the `name="X"` registration value in the 23 unnumbered files that
collide with their numbered scaffold counterparts. The numbered scaffold
keeps its canonical name; the unnumbered file gets a distinct name so
brain_runner registers BOTH.

The rename appends "Driver" (foundational/subcortical) or "Variant"
(integration) — both unnumbered files in each pair are the
batch_10/11/12/13/14 builds that model a more specific functional
aspect (typically the ascending/projecting cascade) of the same region.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (file_relative_to_repo, original_name, new_name)
RENAMES = [
    # Foundational — 6 (Baroreflex was missed in earlier count, total = 6)
    ("brain/foundational/OrexinWakePromoter.py",
     "OrexinWakePromoter",   "OrexinAscendingArousalDriver"),
    ("brain/foundational/HistamineArousalBooster.py",
     "HistamineArousalBooster", "HistamineTMNCorticalDriver"),
    ("brain/foundational/FluidBalanceWatcher.py",
     "FluidBalanceWatcher",  "FluidOsmoreceptiveDriver"),
    ("brain/foundational/BaroreflexBalancer.py",
     "BaroreflexBalancer",   "BaroreflexCardiovascularDriver"),
    ("brain/foundational/PupilFocusRegulator.py",
     "PupilFocusRegulator",  "PupilEdingerWestphalDriver"),
    ("brain/foundational/VagalRestPromoter.py",
     "VagalRestPromoter",    "VagalParasympatheticDriver"),

    # Subcortical — 1
    ("brain/subcortical/ZonaIncerta.py",
     "ZonaIncerta",          "ZonaIncertaBroadOutput"),

    # Integration — 16
    ("brain/integration/CorpusCallosumFullBridge.py",
     "CorpusCallosumFullBridge",
     "CorpusCallosumFullBridgeVariant"),
    ("brain/integration/ClaustrumGlobalConsciousness.py",
     "ClaustrumGlobalConsciousness",
     "ClaustrumGlobalConsciousnessVariant"),
    ("brain/integration/AnteriorCommissureLimbicBridge.py",
     "AnteriorCommissureLimbicBridge",
     "AnteriorCommissureLimbicBridgeVariant"),
    ("brain/integration/AllostaticPredictiveAnticipator.py",
     "AllostaticPredictiveAnticipator",
     "AllostaticPredictiveAnticipatorVariant"),
    ("brain/integration/RewardPredictionErrorIntegrator.py",
     "RewardPredictionErrorIntegrator",
     "RewardPredictionErrorIntegratorVariant"),
    ("brain/integration/CingulumBundleAssociativeBridge.py",
     "CingulumBundleAssociativeBridge",
     "CingulumBundleAssociativeBridgeVariant"),
    ("brain/integration/InteroExteroceptiveMerger.py",
     "InteroExteroceptiveMerger",
     "InteroExteroceptiveMergerVariant"),
    ("brain/integration/GlobalWorkspaceIntegrator.py",
     "GlobalWorkspaceIntegrator",
     "GlobalWorkspaceIntegratorVariant"),
    ("brain/integration/PrefrontalAmygdalaTopDownRegulation.py",
     "PrefrontalAmygdalaTopDownRegulation",
     "PrefrontalAmygdalaTopDownRegulationVariant"),
    ("brain/integration/HierarchicalTopDownBottomUpEquilibrator.py",
     "HierarchicalTopDownBottomUpEquilibrator",
     "HierarchicalTopDownBottomUpEquilibratorVariant"),
    ("brain/integration/MedialForebrainBundleDopamine.py",
     "MedialForebrainBundleDopamine",
     "MedialForebrainBundleDopamineVariant"),
    ("brain/integration/PapezCircuitEmotionalMemoryIntegrator.py",
     "PapezCircuitEmotionalMemoryIntegrator",
     "PapezCircuitEmotionalMemoryIntegratorVariant"),
    ("brain/integration/MetaAwarenessSelfObserver.py",
     "MetaAwarenessSelfObserver",
     "MetaAwarenessSelfObserverVariant"),
    ("brain/integration/ThetaGammaCrossFrequencyBinding.py",
     "ThetaGammaCrossFrequencyBinding",
     "ThetaGammaCrossFrequencyBindingVariant"),
    ("brain/integration/SalienceDefaultExecutiveToggling.py",
     "SalienceDefaultExecutiveToggling",
     "SalienceDefaultExecutiveTogglingVariant"),
    ("brain/integration/NetworkOscillationGlobalBalancer.py",
     "NetworkOscillationGlobalBalancer",
     "NetworkOscillationGlobalBalancerVariant"),
]


def patch(rel_path: str, old: str, new: str) -> bool:
    p = REPO / rel_path
    if not p.exists():
        print(f"[MISS] {rel_path} not found")
        return False
    text = p.read_text(encoding="utf-8")
    pattern = re.compile(r'name\s*=\s*[\"\']' + re.escape(old) + r'[\"\']')
    if not pattern.search(text):
        print(f"[NO-MATCH] {rel_path}: name=\"{old}\" not found")
        return False
    new_text = pattern.sub(f'name="{new}"', text, count=1)
    p.write_text(new_text, encoding="utf-8")
    print(f"[RENAMED] {rel_path}: {old} -> {new}")
    return True


def main() -> int:
    n_renamed = 0
    n_missed = 0
    for rel, old, new in RENAMES:
        if patch(rel, old, new):
            n_renamed += 1
        else:
            n_missed += 1
    print()
    print(f"Renamed: {n_renamed}")
    print(f"Missed:  {n_missed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

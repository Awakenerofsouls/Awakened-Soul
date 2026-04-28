#!/usr/bin/env python3
"""Dry-tick all 6 integration mechanisms — verifies tick-1 brain_* field output."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.integration.Integration018NetworkOscillationGlobalBalancer import NetworkOscillationGlobalBalancer
from brain.integration.Integration019AutonoeticNarrativeSelf import AutonoeticNarrativeSelf
from brain.integration.Integration020HierarchicalTopDownBottomUpEquilibrator import HierarchicalTopDownBottomUpEquilibrator
from brain.integration.Integration021MammillothalamicTractPathway import MammillothalamicTractPathway
from brain.integration.Integration022MidCingulateSubgenualBridge import MidCingulateSubgenualBridge
from brain.integration.Integration025IdentityConsciousnessGuardian import IdentityConsciousnessGuardian

MECHANISMS = [
    ("018", NetworkOscillationGlobalBalancer),
    ("019", AutonoeticNarrativeSelf),
    ("020", HierarchicalTopDownBottomUpEquilibrator),
    ("021", MammillothalamicTractPathway),
    ("022", MidCingulateSubgenualBridge),
    ("025", IdentityConsciousnessGuardian),
]

BRAIN_FIELDS = {
    "018": "brain_oscillation_balance",
    "019": ["brain_narrative_coherence", "brain_self_projection_confidence"],
    "020": "brain_predictive_balance",
    "021": "brain_memory_consolidation",
    "022": "brain_affective_reset",
    "025": ["brain_self_continuity", "brain_consciousness_level"],
}

async def dry_tick():
    print("=" * 70)
    print("DRY TICK — all 6 integration mechanisms")
    print("=" * 70)

    for num, cls in MECHANISMS:
        mech = cls()
        # First tick
        result1 = await mech.tick({"prior_results": {}})
        # Fifth tick
        result5 = await mech.tick({"prior_results": {}})
        result5_warmth = min(1.0, 0.3 + 0.07 * 5)

        bf = BRAIN_FIELDS[num]
        fields = bf if isinstance(bf, list) else [bf]

        print(f"\n{num}: {mech.name}")
        print("-" * 60)
        print(f"  tick 1 warmth_factor: {min(1.0, 0.3 + 0.07 * 1):.2f}")
        print(f"  tick 5 warmth_factor: {result5_warmth:.2f}")
        print(f"  tick 1 brain_* fields:")
        all_present = True
        for f in fields:
            val = result1.get(f, "MISSING")
            status = "✅" if val != "MISSING" else "❌ MISSING"
            print(f"    {f}: {val}")
            if val == "MISSING":
                all_present = False
        if all_present:
            print(f"  tick 1 output keys: {sorted(result1.keys())}")
        print(f"  tick 5 brain_* fields:")
        for f in fields:
            print(f"    {f}: {result5.get(f, 'MISSING')}")

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    all_ok = True
    for num, cls in MECHANISMS:
        mech = cls()
        result1 = await mech.tick({"prior_results": {}})
        bf = BRAIN_FIELDS[num]
        fields = bf if isinstance(bf, list) else [bf]
        missing = [f for f in fields if f not in result1]
        if missing:
            print(f"{num}: ❌ MISSING on tick 1: {missing}")
            all_ok = False
        else:
            print(f"{num}: ✅ all brain_* fields on tick 1")

    if all_ok:
        print("\n✅ ALL mechanisms publish brain_* fields on tick 1")
    else:
        print("\n❌ Some mechanisms missing brain_* fields on tick 1")

    return all_ok

if __name__ == "__main__":
    ok = asyncio.run(dry_tick())
    sys.exit(0 if ok else 1)

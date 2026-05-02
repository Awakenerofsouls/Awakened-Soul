#!/usr/bin/env python3
"""
memory_rehearsal.py — Memory rehearsal system.
Periodically strengthens important memories.
"""

import random
from datetime import datetime
from typing import List, Dict, Optional


class MemoryRehearsal:
    """Memory rehearsal - strengthens important memories."""

    def __init__(self, memory_store=None):
        """
        memory_store: optional object with an `update_importance(memory_id, new_importance)`
                      method. If provided, rehearse() persists strengthening back to the
                      store. If None, rehearsal records are tracked in-memory only.
        """
        self.rehearsal_count = 0
        self.memory_store = memory_store
    
    def should_rehearse(self, memory: Dict) -> bool:
        """Determine if memory should be rehearsed."""
        from temporal import get_temporal
        
        t = get_temporal()
        
        # Check temporal eligibility
        created = memory.get('created', '')
        if not created:
            return False
        
        importance = memory.get('importance', 5) / 10.0
        
        return t.should_rehearse(created, importance)
    
    def rehearse(self, memory: Dict) -> Dict:
        """Rehearse a memory - strengthen its importance.

        If a memory_store was provided to __init__, the new importance is
        persisted via memory_store.update_importance(memory_id, new_importance).
        Storage failures are caught so a single bad memory can't break the cycle.
        """
        self.rehearsal_count += 1

        # Increase importance slightly
        current_importance = memory.get('importance', 5)
        new_importance = min(10, current_importance + 1)

        # Persist back to the store if one was wired in
        persisted = False
        store_error = None
        if self.memory_store is not None and 'id' in memory:
            try:
                self.memory_store.update_importance(memory['id'], new_importance)
                persisted = True
            except Exception as e:
                store_error = str(e)

        # Build rehearsal record
        rehearsal = {
            'original': memory,
            'rehearsed_at': datetime.now().isoformat(),
            'rehearsal_count': self.rehearsal_count,
            'new_importance': new_importance,
            'persisted': persisted,
        }
        if store_error:
            rehearsal['store_error'] = store_error

        return rehearsal
    
    def rehearsal_cycle(self, memories: List[Dict]) -> List[Dict]:
        """Run a rehearsal cycle on memories."""
        rehearsed = []
        
        for memory in memories:
            if self.should_rehearse(memory):
                result = self.rehearse(memory)
                rehearsed.append(result)
        
        return rehearsed
    
    def get_rehearsal_stats(self) -> Dict:
        """Get rehearsal statistics."""
        return {
            'total_rehearsals': self.rehearsal_count
        }


# Singleton
_rehearsal: Optional[MemoryRehearsal] = None


def get_memory_rehearsal() -> MemoryRehearsal:
    """Get memory rehearsal singleton."""
    global _rehearsal
    if _rehearsal is None:
        _rehearsal = MemoryRehearsal()
    return _rehearsal


if __name__ == "__main__":
    # Test
    mr = get_memory_rehearsal()
    print(mr.get_rehearsal_stats())

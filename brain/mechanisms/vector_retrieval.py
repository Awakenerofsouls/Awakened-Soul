"""
brain/mechanisms/vector_retrieval.py — re-export shim.

The real semantic memory write/retrieve API lives at brain/vector_retrieval.py.
This module re-exports the public functions so any historical code that
imported them from this path keeps working, plus a BrainMechanism wrapper
that exposes collection size on tick.
"""

from brain.base_mechanism import BrainMechanism
from brain.vector_retrieval import (
    DEFAULT_COLLECTION,
    collection_size,
    retrieve,
    retrieve_by_tag,
    write_memory,
)


class VectorRetrieval(BrainMechanism):
    """BrainMechanism wrapper — reports semantic memory collection size on tick."""

    def __init__(self):
        super().__init__(
            name="VectorRetrieval",
            human_analog="VectorRetrieval",
            layer="integration",
        )

    async def tick(self, input_data: dict) -> dict:
        size = collection_size(DEFAULT_COLLECTION)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["last_size"] = size
        try:
            self.persist_state()
        except Exception:
            pass
        return {
            "mechanism_name": "VectorRetrieval",
            "collection": DEFAULT_COLLECTION,
            "size": size,
            "exposes": ["write_memory", "retrieve", "retrieve_by_tag"],
        }


__all__ = [
    "write_memory",
    "retrieve",
    "retrieve_by_tag",
    "collection_size",
    "DEFAULT_COLLECTION",
    "VectorRetrieval",
]

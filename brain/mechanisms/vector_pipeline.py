"""
brain/mechanisms/vector_pipeline.py — re-export shim.

The real bulk-indexing pipeline lives at brain/vector_pipeline.py. This
module re-exports the public functions and provides a BrainMechanism
wrapper that exposes pipeline status on tick.
"""

from brain.base_mechanism import BrainMechanism
from brain.vector_pipeline import (
    DEFAULT_COLLECTION,
    index_batch,
    index_session_log,
    index_text,
    rebuild_collection,
)
from brain.vector_retrieval import collection_size


class VectorPipeline(BrainMechanism):
    """BrainMechanism wrapper — reports pipeline status on tick."""

    def __init__(self):
        super().__init__(
            name="VectorPipeline",
            human_analog="VectorPipeline",
            layer="integration",
        )

    async def tick(self, input_data: dict) -> dict:
        size = collection_size(DEFAULT_COLLECTION)
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["collection_size"] = size
        try:
            self.persist_state()
        except Exception:
            pass
        return {
            "mechanism_name": "VectorPipeline",
            "collection": DEFAULT_COLLECTION,
            "size": size,
            "exposes": ["index_text", "index_batch", "index_session_log", "rebuild_collection"],
        }


__all__ = [
    "index_text",
    "index_batch",
    "index_session_log",
    "rebuild_collection",
    "DEFAULT_COLLECTION",
    "VectorPipeline",
]

"""
brain/mechanisms/llm.py — thin re-export shim.

The real LLM wrapper lives at brain/llm.py. This module re-exports the
public API so any historical code that imported it from this path keeps
working.
"""

from brain.base_mechanism import BrainMechanism
from brain.llm import generate_structured, llm_synthesis
from brain.llm_router import call_llm


class Llm(BrainMechanism):
    """
    BrainMechanism wrapper exposing llm-wrapper status. Does NOT perform
    LLM calls on tick — those are demand-driven by other mechanisms.
    """

    def __init__(self):
        super().__init__(name="Llm", human_analog="Llm", layer="integration")

    async def tick(self, input_data: dict) -> dict:
        try:
            from plugins.provider import call as _  # noqa: F401
            provider_registered = True
        except ImportError:
            provider_registered = False

        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["provider_registered"] = provider_registered
        try:
            self.persist_state()
        except Exception:
            pass

        return {
            "mechanism_name": "Llm",
            "provider_registered": provider_registered,
            "exposes": ["llm_synthesis", "generate_structured"],
        }


__all__ = [
    "llm_synthesis",
    "generate_structured",
    "call_llm",
    "Llm",
]

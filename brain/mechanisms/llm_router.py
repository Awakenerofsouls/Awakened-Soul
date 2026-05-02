"""
brain/mechanisms/llm_router.py — thin re-export shim.

The real router lives at brain/llm_router.py. This module re-exports the
public API so any historical code that imported it from this path keeps
working.
"""

from brain.base_mechanism import BrainMechanism
from brain.llm_router import (
    LLMProviderNotRegistered,
    call_llm,
    llm_extract,
    route_llm,
)


class LlmRouter(BrainMechanism):
    """
    BrainMechanism wrapper exposing router status. Does NOT perform LLM calls
    on tick — those are demand-driven by other mechanisms.
    """

    def __init__(self):
        super().__init__(
            name="LlmRouter",
            human_analog="LlmRouter",
            layer="integration",
        )

    async def tick(self, input_data: dict) -> dict:
        # Probe whether a provider is registered without making a real call.
        try:
            from plugins.provider import call as _  # noqa: F401
            provider_registered = True
            error = None
        except ImportError as e:
            provider_registered = False
            error = str(e)

        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.state["provider_registered"] = provider_registered
        try:
            self.persist_state()
        except Exception:
            pass

        return {
            "mechanism_name": "LlmRouter",
            "provider_registered": provider_registered,
            "error": error,
            "exposes": ["call_llm", "llm_extract", "route_llm"],
        }


__all__ = [
    "LLMProviderNotRegistered",
    "call_llm",
    "llm_extract",
    "route_llm",
    "LlmRouter",
]

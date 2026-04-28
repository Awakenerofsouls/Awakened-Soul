#!/usr/bin/env python3
"""
brain/llm_router.py — LLM routing contract

The framework calls `call_llm(...)` and `llm_extract(...)` whenever a mechanism
needs an LLM response. Both functions delegate to an operator-provided
implementation.

To register an LLM provider, the operator creates a Python module that exposes
a `call` function matching this signature:

 def call(prompt: str, system: str | None, max_tokens: int, temperature: float) -> str

The module must be importable as `plugins.provider`. Operators may structure
their implementation any way they want beneath that entry point — fallback
chains, task-based routing, retry logic, multiple backends — none of which
the framework needs to know about.

If no provider is registered, both functions raise LLMProviderNotRegistered
with instructions for the operator.
"""

import logging

logger = logging.getLogger(__name__)


class LLMProviderNotRegistered(RuntimeError):
    """Raised when no LLM provider implementation is available."""

    def __init__(self):
        super().__init__(
            "No LLM provider registered. "
            "Create plugins/provider.py with a `call(prompt, system, max_tokens, temperature) -> str` "
            "function. See the install documentation for details."
        )


def _invoke_provider(prompt: str, system, max_tokens: int, temperature: float) -> str:
    try:
        from plugins.provider import call as _call
    except ImportError:
        raise LLMProviderNotRegistered()
    return _call(prompt, system, max_tokens, temperature)


def call_llm(prompt, system=None, max_tokens=2048, temperature=0.7) -> str:
    """
    General-purpose LLM call. Delegates to the operator-provided provider.

    Returns plain text. Raises LLMProviderNotRegistered if no provider is
    registered. All other exceptions are raised as-is from the provider.
    """
    return _invoke_provider(prompt, system, max_tokens, temperature)


def llm_extract(prompt, system=None, max_tokens=1024, temperature=0.3) -> str:
    """
    Extraction/inference call — lower temperature default for deterministic output.
    Delegates to the operator-provided provider.
    """
    return _invoke_provider(prompt, system, max_tokens, temperature)

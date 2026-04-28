"""
brain/llm.py — legacy entry point preserved for backward compatibility.

Older brain mechanisms import `llm_synthesis` from this module. That interface
is preserved here as a thin wrapper over the provider-agnostic LLM router.

All LLM execution goes through brain.llm_router, which delegates to the
operator-provided provider at plugins.provider.

New code should call brain.llm_router.call_llm() directly.
"""

from brain.llm_router import call_llm


def llm_synthesis(prompt, system=None, max_tokens=2048, temperature=0.7, model=None):
    """
    Synthesis call. Delegates to the operator-provided provider via
    brain.llm_router.

    The `model` argument is preserved for signature compatibility with older
    callers. Providers that support per-call model selection can read it from
    kwargs; providers that don't can ignore it. The framework does not act on
    it.

    Returns plain text. Raises brain.llm_router.LLMProviderNotRegistered if no
    provider is registered.
    """
    return call_llm(
        prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )

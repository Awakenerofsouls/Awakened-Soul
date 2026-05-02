#!/usr/bin/env python3
"""
skills/llm_router.py — skill-side LLM calls + retry utility

Delegates all LLM execution to the operator-provided provider registered at
plugins.provider. This router adds two things on top of that entry point:

 1. A small set of convenience signatures (complete, prompt, llm_extract)
 shaped for skill scripts
 2. Framework-level retry (complete_with_retry) for unattended calls —
 overnight skills, long-running pipelines — where a transient failure
 shouldn't kill the whole operation

All routing/fallback/provider-selection decisions belong inside the operator's
registered provider. This router does not know about models, endpoints, or
providers by name.

The `task_type` argument is passed through as a hint to the provider. The
framework does not act on it. Operators may use it inside their provider to
route different task types to different backends if they choose.
"""

import time
import types
from typing import Optional

from brain.llm_router import LLMProviderNotRegistered, call_llm, llm_extract as _llm_extract


# ─── Core skill-facing calls ──────────────────────────────────────────────────

def complete(
    prompt: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 200,
    temperature: float = 0.8,
    task_type: str = "general",
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Optional[str]:
    """
    Call the registered provider with a prompt. Returns text, or None on failure.

    `task_type` is a skill-side hint — the framework doesn't act on it.

    `model` and `timeout` are accepted in this signature for source compatibility
    with skill callers, but the current provider contract is
    `call(prompt, system, max_tokens, temperature) -> str` (see brain/llm_router.py),
    so these two parameters are NOT forwarded to the provider. They're held here
    until the provider contract is extended; passing them today is a no-op.

    Returns None on provider failure. Raises LLMProviderNotRegistered if no
    provider is configured (configuration errors should surface loudly, not
    be hidden behind None).
    """
    # `model` and `timeout` intentionally unused — see docstring.
    _ = model, timeout
    try:
        return call_llm(
            prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except LLMProviderNotRegistered:
        # Configuration problem — surface loudly, don't hide with None
        raise
    except Exception as e:
        _log(f"[{task_type}] provider call failed: {e}")
        return None


def complete_with_retry(
    prompt: str,
    *,
    retries: int = 2,
    retry_delay: float = 5.0,
    **kwargs,
) -> Optional[str]:
    """
    Call complete() with retry on transient failure.

    Use for unattended calls (overnight skills, long pipelines) where a
    momentary provider hiccup shouldn't fail the whole operation.

    Returns the first successful response, or None if all attempts fail.
    """
    for attempt in range(retries + 1):
        result = complete(prompt, **kwargs)
        if result is not None:
            return result
        if attempt < retries:
            _log(f"attempt {attempt + 1}/{retries + 1} failed, retrying in {retry_delay}s")
            time.sleep(retry_delay)
    return None


def prompt(
    prompt_text: str,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 200,
    temperature: float = 0.8,
    timeout: float = 60.0,
    task_type: str = "general",
) -> Optional[str]:
    """
    String-in, string-out interface for skill scripts.
    Thin wrapper over complete().
    """
    return complete(
        prompt_text,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
        task_type=task_type,
        model=model,
        timeout=timeout,
    )


def llm_extract(
    prompt_text: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.4,
    timeout: float = 60.0,
    task_type: str = "general",
) -> Optional[str]:
    """
    Structured-extraction interface. Lower default temperature reduces
    hallucination in tasks that expect parseable output (JSON, classifications).

    Returns text or None. Does not raise on provider failure.
    """
    try:
        return _llm_extract(
            prompt_text,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except LLMProviderNotRegistered:
        raise
    except Exception as e:
        _log(f"[{task_type}] extract call failed: {e}")
        return None


# ─── Utilities ────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    print(f"[llm_router] {msg}", flush=True)


# Back-compat namespace: external callers do `from skills.llm_router import llm_router`
# then call `llm_router.complete(...)`. Provide a namespace with a complete attr.
llm_router = types.SimpleNamespace()
llm_router.complete = complete

"""
brain/llm.py — legacy entry point preserved for backward compatibility.

Older brain mechanisms import `llm_synthesis` and `generate_structured` from
this module. Those interfaces are preserved here as thin wrappers over the
provider-agnostic LLM router.

All LLM execution goes through brain.llm_router, which delegates to the
operator-provided provider at plugins.provider.

New code should call brain.llm_router.call_llm() directly.
"""

import json
import re
from typing import Any, Dict, Optional

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


def generate_structured(
    prompt: str,
    schema: Dict[str, str],
    system: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.4,
) -> Dict[str, Any]:
    """
    Schema-guided structured generation. Asks the provider to return JSON
    matching the given schema (a dict of field_name → description), then
    parses the response into a dict.

    Falls back to {"_raw": <text>, "_parse_error": <reason>} if the
    response is not valid JSON. The caller decides how strict to be.

    Args:
        prompt: the user-facing prompt
        schema: dict of {field_name: description-string}
        system: optional system prompt
        max_tokens, temperature: forwarded to the provider

    Returns:
        dict — keys present depend on what the model returned. On parse
        failure, returns {"_raw": <text>, "_parse_error": <reason>}.
    """
    schema_lines = "\n".join(f'  "{k}": {v}' for k, v in schema.items())
    augmented_system = (
        (system or "")
        + "\n\nRespond with a single JSON object matching this schema. "
        "Output ONLY the JSON — no prose, no code fences."
    ).strip()
    augmented_prompt = (
        f"{prompt}\n\n"
        f"Schema:\n{{\n{schema_lines}\n}}\n\n"
        "Return JSON only."
    )

    text = call_llm(
        augmented_prompt,
        system=augmented_system,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return _parse_json_loose(text)


def _parse_json_loose(text: str) -> Dict[str, Any]:
    """
    Best-effort JSON parse. Strips code fences, finds the first {...} block,
    and tries json.loads. Returns {"_raw":..., "_parse_error":...} on failure.
    """
    if not text:
        return {"_raw": "", "_parse_error": "empty response"}

    s = text.strip()
    # Strip ```json fences
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)

    # First {...} block
    m = re.search(r"\{[\s\S]*\}", s)
    candidate = m.group(0) if m else s

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
        return {"_raw": text, "_parse_error": f"expected object, got {type(parsed).__name__}"}
    except json.JSONDecodeError as e:
        return {"_raw": text, "_parse_error": str(e)}

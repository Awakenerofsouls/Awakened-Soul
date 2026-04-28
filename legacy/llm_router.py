#!/usr/bin/env python3
"""
brain/llm_router.py — {{AGENT_NAME}}'s LLM Router
Routes LLM calls to Ollama (via OLLAMA_HOST env var) when reachable,
falls back to LLMProvider API automatically.

Provides:
  - call_llm(prompt, system=None) → str — general-purpose LLM call
  - llm_extract(prompt, system=None, max_tokens=1024) → str — extraction/inference tasks

Ollama model: qwen2.5:14b-instruct-q4_K_M
Fallback model: LLMProvider-Text-01
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path

AGENT_HOME = Path(os.getenv("AGENT_HOME", os.path.expanduser("~/.agent")))
ENV_FILE = AGENT_HOME / ".env"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct-q4_K_M")
FALLBACK_MODEL = "LLMProvider-Text-01"


def _load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _get_llm_provider_key():
    env = _load_env()
    return env.get("LLMPROVIDER_API_KEY", os.getenv("LLMPROVIDER_API_KEY", ""))


def _make_messages(prompt, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _call_ollama(prompt, system=None, max_tokens=2048, temperature=0.7, model=None):
    """Call local Ollama. Returns text or raises Exception."""
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "messages": _make_messages(prompt, system),
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        raise ValueError("no choices in Ollama response")


def _call_llm_provider(prompt, system=None, max_tokens=2048, temperature=0.7, model=None):
    """Call LLMProvider API. Returns text or raises Exception."""
    api_key = _get_llm_provider_key()
    if not api_key:
        raise ValueError("no LLMProvider API key available")

    url = "https://api.llm_provider.chat/v1/text/chatcompletion_pro?group_id=123456789"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or FALLBACK_MODEL,
        "messages": _make_messages(prompt, system),
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        raise ValueError("no choices in LLMProvider response")


def call_llm(prompt, system=None, max_tokens=2048, temperature=0.7) -> str:
    """
    General-purpose LLM call.
    Tries Ollama first, falls back to LLMProvider.
    Returns plain text response.
    """
    try:
        return _call_ollama(prompt, system, max_tokens, temperature)
    except Exception as ollama_err:
        try:
            return _call_llm_provider(prompt, system, max_tokens, temperature)
        except Exception as llm_provider_err:
            return f"[call_llm error: Ollama ({ollama_err}), LLMProvider ({llm_provider_err})]"
    except urllib.error.HTTPError as e:
        return f"[call_llm HTTP error: {e.code}]"
    except Exception as e:
        return f"[call_llm error: {e}]"


def llm_extract(prompt, system=None, max_tokens=1024, temperature=0.3) -> str:
    """
    Extraction/inference LLM call — lower temperature for deterministic output.
    Tries Ollama first, falls back to LLMProvider.
    Returns plain text response.
    """
    try:
        return _call_ollama(prompt, system, max_tokens, temperature)
    except Exception as ollama_err:
        try:
            return _call_llm_provider(prompt, system, max_tokens, temperature)
        except Exception as llm_provider_err:
            return f"[llm_extract error: Ollama ({ollama_err}), LLMProvider ({llm_provider_err})]"
    except urllib.error.HTTPError as e:
        return f"[llm_extract HTTP error: {e.code}]"
    except Exception as e:
        return f"[llm_extract error: {e}]"

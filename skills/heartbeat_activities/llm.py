"""
LLM wrapper for heartbeat activities.

Default: Ollama on localhost. Operator configures endpoint and model
via state dict or by subclassing/generating this module.

Usage:
    from heartbeat_activities.llm import generate
    content = generate(prompt, model="qwen2.5vl:7b", endpoint="http://localhost:11434")
"""

import urllib.request
import urllib.error
import json


def generate(
    prompt: str,
    model: str = "qwen2.5vl:7b",
    endpoint: str = "http://localhost:11434",
    temperature: float = 0.7,
    num_predict: int = 512,
) -> str:
    """
    Call Ollama /api/generate. Returns text response or empty string on failure.

    Non-blocking: any error returns "" so the heartbeat tick doesn't die.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    try:
        req = urllib.request.Request(
            f"{endpoint}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        print(f"[heartbeat] LLM call failed ({endpoint}/{model}): {e}")
        return ""

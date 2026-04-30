#!/usr/bin/env python3
"""
brain_proxy.py — Brain-enriching proxy between OpenClaw gateway and MiniMax.

Sits on localhost:8001. Gateway thinks it's talking to MiniMax Anthropic API.
Proxy intercepts, calls brain on port 8000, injects cognitive state into system
prompt, forwards enriched request to real MiniMax, streams response back.

Usage:
    python3 brain_proxy.py

Config:
    Change gateway baseUrl from https://api.minimax.io/anthropic
    to http://localhost:8001

Environment:
    MINIMAX_API_KEY — forwarded to real MiniMax (or read from gateway headers)
    BRAIN_URL       — defaults to http://localhost:8000
    MINIMAX_URL     — defaults to https://api.minimax.io/anthropic
    PROXY_PORT      — defaults to 8001
"""

import os
import json
import logging
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [proxy] %(message)s")
log = logging.getLogger("brain_proxy")

BRAIN_URL = os.getenv("BRAIN_URL", "http://localhost:8000")
MINIMAX_URL = os.getenv("MINIMAX_URL", "https://api.minimax.io/anthropic")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8001"))

app = FastAPI(title="Nova Brain Proxy")


def extract_user_message(messages: list) -> str:
    """Extract the most recent user message text from Anthropic message list."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # Content blocks format
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
    return ""


def extract_session_id(request_body: dict, headers: dict) -> str:
    """Best-effort session ID from request metadata."""
    # Check for session in metadata or use model name as stable ID
    meta = request_body.get("metadata", {})
    if isinstance(meta, dict) and meta.get("session_id"):
        return meta["session_id"]
    # Fall back to a stable default — proxy doesn't have real session tracking
    return "gateway_session"


async def call_brain(message: str, session_id: str) -> str | None:
    """
    Call the Python brain API on port 8000.
    Returns the cognitive state prefix string, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BRAIN_URL}/chat",
                json={"message": message, "session_id": session_id}
            )
            if resp.status_code == 200:
                data = resp.json()
                # Brain returns {"response": "...", "cognitive_state": {...}, ...}
                # We want the [COGNITIVE STATE] prefix that gets prepended to system
                cognitive_state = data.get("cognitive_state", {})
                if cognitive_state:
                    lines = ["[COGNITIVE STATE]"]
                    for k, v in cognitive_state.items():
                        if v is not None and v != "" and v != {}:
                            lines.append(f"{k}: {v}")
                    lines.append("")
                    return "\n".join(lines)
                # If brain returns a formatted prefix directly
                raw = data.get("system_prefix", "")
                if raw:
                    return raw
            else:
                log.warning(f"Brain returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log.warning(f"Brain call failed: {e}")
    return None


def inject_brain_context(system_prompt: str, brain_prefix: str) -> str:
    """Prepend cognitive state to system prompt."""
    if not brain_prefix:
        return system_prompt
    if system_prompt:
        return f"{brain_prefix}\n{system_prompt}"
    return brain_prefix


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    """
    Main proxy endpoint. Mirrors Anthropic /v1/messages.
    Intercepts, enriches with brain context, forwards to MiniMax.
    """
    # Read raw body
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError:
        return Response(content=body_bytes, status_code=400)

    # Extract what we need for brain call
    messages = body.get("messages", [])
    user_message = extract_user_message(messages)
    session_id = extract_session_id(body, dict(request.headers))

    log.info(f"Intercepted message: {user_message[:80]}...")

    # Call brain
    brain_prefix = None
    if user_message:
        brain_prefix = await call_brain(user_message, session_id)
        if brain_prefix:
            log.info(f"Brain enrichment: {len(brain_prefix)} chars")
        else:
            log.info("Brain call failed or returned nothing — forwarding without enrichment")

    # Inject brain context into system prompt
    if brain_prefix:
        existing_system = body.get("system", "")
        body["system"] = inject_brain_context(existing_system, brain_prefix)

    # Forward to real MiniMax — pass through all original headers except Host
    forward_headers = {}
    for key, value in request.headers.items():
        if key.lower() in ("authorization", "x-api-key", "content-type", "anthropic-version",
                            "anthropic-beta", "user-agent"):
            forward_headers[key] = value

    target_url = f"{MINIMAX_URL}/v1/messages"
    is_streaming = body.get("stream", False)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_streaming:
                async def stream_response():
                    async with client.stream(
                        "POST",
                        target_url,
                        json=body,
                        headers=forward_headers
                    ) as upstream:
                        async for chunk in upstream.aiter_bytes():
                            yield chunk

                return StreamingResponse(
                    stream_response(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Brain-Enriched": "true" if brain_prefix else "false"}
                )
            else:
                upstream = await client.post(
                    target_url,
                    json=body,
                    headers=forward_headers
                )
                response_headers = {
                    "Content-Type": upstream.headers.get("content-type", "application/json"),
                    "X-Brain-Enriched": "true" if brain_prefix else "false"
                }
                return Response(
                    content=upstream.content,
                    status_code=upstream.status_code,
                    headers=response_headers
                )

    except httpx.TimeoutException:
        log.error("MiniMax request timed out")
        return Response(
            content=json.dumps({"error": {"type": "timeout", "message": "upstream timeout"}}),
            status_code=504,
            media_type="application/json"
        )
    except Exception as e:
        log.error(f"Forward error: {e}")
        return Response(
            content=json.dumps({"error": {"type": "proxy_error", "message": str(e)}}),
            status_code=502,
            media_type="application/json"
        )


@app.get("/health")
async def health():
    """Health check — also reports brain reachability."""
    brain_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{BRAIN_URL}/health")
            brain_ok = resp.status_code == 200
    except Exception:
        pass

    return {
        "proxy": "ok",
        "brain": "ok" if brain_ok else "unreachable",
        "brain_url": BRAIN_URL,
        "minimax_url": MINIMAX_URL,
        "port": PROXY_PORT
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def passthrough(request: Request, path: str):
    """
    Pass through any other endpoints unchanged.
    Handles /v1/models, /v1/count_tokens, etc.
    """
    body_bytes = await request.body()
    forward_headers = {}
    for key, value in request.headers.items():
        if key.lower() in ("authorization", "x-api-key", "content-type", "anthropic-version",
                            "anthropic-beta", "user-agent"):
            forward_headers[key] = value

    target_url = f"{MINIMAX_URL}/{path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                content=body_bytes,
                headers=forward_headers,
                params=dict(request.query_params)
            )
            return Response(
                content=upstream.content,
                status_code=upstream.status_code,
                headers={"Content-Type": upstream.headers.get("content-type", "application/json")}
            )
    except Exception as e:
        log.error(f"Passthrough error for /{path}: {e}")
        return Response(status_code=502)


if __name__ == "__main__":
    log.info(f"Brain proxy starting on port {PROXY_PORT}")
    log.info(f"Brain: {BRAIN_URL}")
    log.info(f"MiniMax: {MINIMAX_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT, log_level="warning")

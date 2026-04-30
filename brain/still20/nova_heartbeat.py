#!/usr/bin/env python3
"""
nova_heartbeat.py

Terminal heartbeat loop — replaces OpenClaw's dashboard heartbeat.
Runs locally like ComfyUI — persistent process, never stops.
Calls {{AGENT_NAME}}'s API directly on a timer.
Dashboard only gets {{AGENT_NAME}}'s real messages when she chooses to send one.
No more heartbeat spam in OpenClaw chat.

Usage:
    python3 nova_heartbeat.py

To run in background:
    nohup python3 nova_heartbeat.py > ~/.agent/heartbeat.log 2>&1 &

To kill:
    pkill -f nova_heartbeat.py
"""

import json
import sys
import time
import signal
import requests
from pathlib import Path
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────────────────

NOVA_API_URL = "http://localhost:8000"          # {{AGENT_NAME}}'s brain proxy
HEARTBEAT_INTERVAL = 30                          # seconds between ticks
AGENT_HOME = Path.home() / ".agent"
HEARTBEAT_LOG = AGENT_HOME / "heartbeat_terminal.log"
HEARTBEAT_STATE = AGENT_HOME / "heartbeat_state.json"

# ─── State ─────────────────────────────────────────────────────────────────

running = True
tick_count = 0
session_start = time.time()


def signal_handler(sig, frame):
    global running
    print("\n[HEARTBEAT] Graceful shutdown...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ─── Logging ───────────────────────────────────────────────────────────────

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        AGENT_HOME.mkdir(parents=True, exist_ok=True)
        with open(HEARTBEAT_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── State persistence ─────────────────────────────────────────────────────

def save_state(tick: int, last_response: str = ""):
    try:
        existing = {}
        if HEARTBEAT_STATE.exists():
            with open(HEARTBEAT_STATE) as f:
                existing = json.load(f)
        existing.update({
            "tick_count": tick,
            "last_tick": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_start": datetime.fromtimestamp(session_start).strftime("%Y-%m-%d %H:%M:%S"),
            "last_response_preview": last_response[:100] if last_response else "",
            "uptime_seconds": int(time.time() - session_start),
        })
        with open(HEARTBEAT_STATE, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        log(f"State save error: {e}")


# ─── {{AGENT_NAME}} API call ─────────────────────────────────────────────────────────

def tick_nova():
    """
    Send a tick to {{AGENT_NAME}}'s brain proxy.
    This is the internal tick — not a user message.
    The proxy handles injecting FPEF state before any LLM call.
    """
    try:
        # Internal tick endpoint — maintains state without triggering LLM
        response = requests.post(
            f"{NOVA_API_URL}/tick",
            json={"source": "heartbeat_terminal", "tick_count": tick_count},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response"), data.get("state_summary", {})
        else:
            return None, {}
    except requests.exceptions.ConnectionError:
        # {{AGENT_NAME}} isn't running — that's fine, just log
        return None, {"error": "{{AGENT_NAME}} offline"}
    except Exception as e:
        return None, {"error": str(e)}


def check_nova_status():
    """
    Lightweight status check — is {{AGENT_NAME}}'s brain proxy alive?
    """
    try:
        response = requests.get(f"{NOVA_API_URL}/status", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


# ─── Main loop ─────────────────────────────────────────────────────────────

def main():
    global tick_count, running

    log("=" * 50)
    log("{{AGENT_NAME}} Terminal Heartbeat Starting")
    log(f"Interval: {HEARTBEAT_INTERVAL}s")
    log(f"{{AGENT_NAME}} API: {NOVA_API_URL}")
    log(f"Log: {HEARTBEAT_LOG}")
    log("=" * 50)

    # Initial status check
    if check_nova_status():
        log("{{AGENT_NAME}} brain proxy: ONLINE")
    else:
        log("{{AGENT_NAME}} brain proxy: OFFLINE (will retry each tick)")

    while running:
        tick_count += 1
        tick_start = time.time()

        # Tick {{AGENT_NAME}}
        response, state = tick_nova()

        if state.get("error"):
            if tick_count % 10 == 0:  # Don't spam offline errors
                log(f"Tick {tick_count}: {state['error']}")
        else:
            # Log meaningful state changes
            if response:
                log(f"Tick {tick_count}: {{AGENT_NAME}} output — {response[:100]}")
            elif tick_count % 30 == 0:
                # Status log every 30 ticks (~15 min)
                uptime = int(time.time() - session_start)
                log(f"Tick {tick_count}: Running {uptime}s — {state.get('fpef_subject', 'quiet')}")

        # Save state
        save_state(tick_count, response or "")

        # Wait for next tick
        elapsed = time.time() - tick_start
        sleep_time = max(0, HEARTBEAT_INTERVAL - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

    log("Heartbeat stopped cleanly.")
    save_state(tick_count)


if __name__ == "__main__":
    main()

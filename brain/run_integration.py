#!/usr/bin/env python3
"""
Launch wrapper for AgentBrainIntegration.
Must be run from workspace root so the agent_brain symlink resolves correctly.
"""
import os, sys, signal, threading
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from brain.brain_integration import AgentBrainIntegration

running = True

def signal_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, signal_handler)

nbi = AgentBrainIntegration()
nbi.on_session_open()

def loop():
    nbi.core.run()

t = threading.Thread(target=loop, daemon=True)
t.start()

print("[run_integration] AgentBrainIntegration running.")
while running:
    t.join(timeout=2)
print("[run_integration] Shutdown complete.")

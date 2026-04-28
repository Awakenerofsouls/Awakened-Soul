#!/usr/bin/env python3
"""Start {{AGENT_NAME}}'s autonomous daemon."""
import sys, os
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.bootstrap import get_agent

agent = get_agent()
agent.start_autonomous_tick()
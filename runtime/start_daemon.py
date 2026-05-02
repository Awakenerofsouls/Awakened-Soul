#!/usr/bin/env python3
"""Start the agent's autonomous daemon."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from brain.bootstrap import get_agent
    agent = get_agent()
    agent.start_autonomous_tick()


if __name__ == "__main__":
    main()
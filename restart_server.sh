#!/bin/bash
cd "${AGENT_WORKSPACE:-$HOME/.agent/workspace}"
python3 api/server.py &

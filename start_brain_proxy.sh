#!/bin/bash
# start_brain_proxy.sh — Start the agent's brain proxy
# Run this after starting the Python brain server (port 8000)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROXY_LOG="${SCRIPT_DIR}/brain_proxy.log"

# Check brain is up
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "WARNING: Brain server on port 8000 not responding — proxy will start but brain enrichment will fail"
fi

# Check port 8001 is free
if lsof -i :8001 > /dev/null 2>&1; then
    echo "ERROR: Port 8001 already in use"
    lsof -i :8001
    exit 1
fi

echo "Starting brain proxy on port 8001..."
echo "Logs: $PROXY_LOG"

cd "$SCRIPT_DIR"
nohup python3 brain_proxy.py >> "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > brain_proxy.pid

sleep 1
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "Brain proxy started (pid $PROXY_PID)"
    # Quick health check
    sleep 1
    curl -sf http://localhost:8001/health && echo "" || echo "Health check failed — check $PROXY_LOG"
else
    echo "ERROR: Proxy failed to start — check $PROXY_LOG"
    exit 1
fi

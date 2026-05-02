"""
core/settings.py
Awakened Soul agent configuration — loaded from environment variables.
"""

import os

# Council decision mode
# off     → bare loop, ~1 LLM call/cycle (DecisionEngine only)
# threshold → council fires if best option risk > COUNCIL_RISK_THRESHOLD
# always  → council every cycle, ~3 LLM calls minimum
COUNCIL_MODE = os.getenv("COUNCIL_MODE", "threshold").lower()
COUNCIL_RISK_THRESHOLD = float(os.getenv("COUNCIL_RISK_THRESHOLD", "0.55"))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Vercel
AGENT_API_URL = os.getenv("AGENT_API_URL", "")
AGENT_API_SECRET = os.getenv("AGENT_API_SECRET", "")

# Loop
CYCLE_INTERVAL_SECONDS = int(os.getenv("CYCLE_INTERVAL_SECONDS", "30"))
MAX_CYCLES = int(os.getenv("MAX_CYCLES", "1000"))

# Context Guardian — monitors memory tier sizes and context load
# Fires a council vote to archive/compress when total memory usage exceeds this threshold (KB)
CONTEXT_GUARDIAN_THRESHOLD_KB = int(os.getenv("CONTEXT_GUARDIAN_THRESHOLD_KB", "512"))

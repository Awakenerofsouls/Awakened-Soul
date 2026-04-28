"""
Stub activity — placeholder for activities not yet ported.

Each stub: run(state) → {ok, status, content, category, detail}
Replace stub with full implementation when porting that activity.
"""

def run(state: dict) -> dict:
    return {
        "ok": True,
        "status": "complete",
        "content": "",
        "category": __name__.rsplit(".", 1)[-1],
        "detail": "stub — not yet ported",
    }

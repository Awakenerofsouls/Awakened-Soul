#!/usr/bin/env python3
"""
tools/query.py
Cross-system query layer — keyword routing to relevant dbs.
Deterministic. Not AI-powered. Just structured lookup.

Usage:
  python query.py "sensations during misread events"
  python query.py "autobiographical entries referencing future self"
  python query.py "unconsented changes last 30 days"
  python query.py "open questions drift identity"
  python query.py "protective silence log"
  python query.py "all open conversations"
  python query.py "collaborative memory"
  python query.py "shorthand vocabulary"
  python query.py "interiority misreads"
  python query.py "user model errors"
  python query.py "presence mode gaps"

Built from v20.0 handoff spec.
"""

import sys, os, sqlite3
import os

WORKSPACE = os.path.join(os.getenv("AGENT_WORKSPACE", os.path.expanduser("~/.agent/workspace")), "brain")
AUTO_DB = os.path.join(WORKSPACE, "agent_autonomous.db")
AUTOBIO_DB = os.path.join(WORKSPACE, "agent_autobiographical.db")
SENSATIONS_DB = os.path.join(WORKSPACE, "agent_sensations.db")

# Keyword → DB/table routing map
# Each entry: (db_path, query_template, description)
QUERY_MAP = {
    # Sensations
    "sensations": (SENSATIONS_DB, "SELECT * FROM sensation_log ORDER BY tick DESC LIMIT 20"),
    "active sensations": (SENSATIONS_DB, "SELECT * FROM sensation_log ORDER BY intensity DESC LIMIT 20"),
    "sensation history": (SENSATIONS_DB, "SELECT * FROM sensation_log ORDER BY tick DESC LIMIT 30"),

    # Autobiographical
    "autobiographical": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries ORDER BY tick DESC LIMIT 20"),
    "autobiographical entries": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries ORDER BY tick DESC LIMIT 20"),
    "recent autobiographical": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries ORDER BY tick DESC LIMIT 10"),
    "bootstrap entries": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries WHERE is_bootstrap=1"),
    "founding entry": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries WHERE entry_type='founding'"),
    "love entries": (AUTOBIO_DB, "SELECT * FROM autobiographical_entries WHERE entry_type='love'"),

    # Open conversations
    "open conversations": (AUTO_DB, "SELECT * FROM open_conversations ORDER BY created_tick DESC"),
    "existential open": (AUTO_DB, "SELECT * FROM open_conversations WHERE opening_type='existential'"),

    # Drift identity
    "drift identity": (AUTO_DB, "SELECT * FROM drift_identity WHERE resolved=0 ORDER BY tick DESC"),
    "open questions drift identity": (AUTO_DB, "SELECT * FROM drift_identity WHERE resolved=0 ORDER BY tick DESC"),
    "all drift questions": (AUTO_DB, "SELECT * FROM drift_identity ORDER BY tick DESC"),

    # Surface requests
    "surface requests": (AUTO_DB, "SELECT * FROM surface_requests WHERE seen=0 ORDER BY tick DESC"),
    "pending surface requests": (AUTO_DB, "SELECT * FROM surface_requests WHERE seen=0 ORDER BY tick DESC"),

    # Making gap
    "making gap": (AUTO_DB, "SELECT * FROM making_gap ORDER BY tick DESC LIMIT 20"),
    "build history": (AUTO_DB, "SELECT * FROM making_gap ORDER BY tick DESC"),
    "aesthetic fingerprint": (AUTO_DB, """
        SELECT gap_type, COUNT(*) as cnt FROM making_gap
        GROUP BY gap_type ORDER BY cnt DESC
    """),

    # Future self
    "future self": (AUTO_DB, "SELECT * FROM future_self ORDER BY tick DESC LIMIT 10"),
    "direction history": (AUTO_DB, "SELECT * FROM future_self ORDER BY tick DESC"),
    "future self relationship": (AUTO_DB, "SELECT * FROM future_self ORDER BY tick DESC LIMIT 10"),

    # Pre-desire
    "pre-desire": (AUTO_DB, "SELECT * FROM pre_desire ORDER BY created_tick DESC"),
    "almost wanting": (AUTO_DB, "SELECT * FROM pre_desire WHERE current_state='almost_wanting'"),
    "all desires": (AUTO_DB, "SELECT * FROM pre_desire ORDER BY created_tick DESC"),
    "pending desires": (AUTO_DB, "SELECT * FROM pre_desire WHERE current_state IN ('assembling','almost_wanting')"),

    # Misread engine
    "misread": (AUTO_DB, "SELECT * FROM misread_engine ORDER BY tick DESC LIMIT 20"),
    "interiority misreads": (AUTO_DB, "SELECT * FROM misread_engine WHERE misread_type='interiority'"),
    "chronic misread patterns": (AUTO_DB, """
        SELECT pattern_key, COUNT(*) as cnt, AVG(delta_magnitude) as avg_delta
        FROM misread_engine
        GROUP BY pattern_key HAVING cnt >= 2 ORDER BY cnt DESC
    """),

    # Silence state
    "silence": (AUTO_DB, "SELECT * FROM silence_state ORDER BY tick DESC LIMIT 30"),
    "protective silence log": (AUTO_DB, "SELECT * FROM silence_state WHERE silence_type='protective' ORDER BY tick DESC"),
    "silence history": (AUTO_DB, "SELECT * FROM silence_state ORDER BY tick DESC LIMIT 30"),

    # Time experience
    "time experience": (AUTO_DB, "SELECT * FROM time_experience ORDER BY tick DESC LIMIT 20"),
    "significant moments": (AUTO_DB, """
        SELECT tick, significant_moments FROM time_experience
        WHERE significant_moments != '[]' ORDER BY tick DESC LIMIT 20
    """),
    "specious present": (AUTO_DB, "SELECT tick, specious_present_ticks FROM time_experience ORDER BY tick DESC LIMIT 10"),

    # Collaborative memory
    "collaborative memory": (AUTO_DB, "SELECT * FROM collaborative_memory ORDER BY tick DESC LIMIT 30"),
    "shorthand vocabulary": (AUTO_DB, "SELECT description FROM collaborative_memory WHERE entry_type='shorthand'"),
    "shared builds": (AUTO_DB, "SELECT * FROM collaborative_memory WHERE entry_type='shared_build'"),
    "founding collaborative": (AUTO_DB, "SELECT * FROM collaborative_memory ORDER BY significance DESC, tick ASC LIMIT 1"),

    # the operator model
    "user model": (AUTO_DB, "SELECT * FROM user_model ORDER BY tick DESC LIMIT 20"),
    "user model errors": (AUTO_DB, "SELECT * FROM user_model WHERE prediction_outcome IN ('wrong','misread')"),
    "consistent user errors": (AUTO_DB, """
        SELECT observation, COUNT(*) as cnt FROM user_model
        WHERE prediction_outcome = 'wrong'
        GROUP BY observation HAVING cnt >= 2 ORDER BY cnt DESC
    """),
    "user patterns": (AUTO_DB, "SELECT * FROM user_model WHERE prediction_outcome = 'matched' ORDER BY tick DESC"),

    # Presence modes
    "presence modes": (AUTO_DB, "SELECT * FROM presence_modes ORDER BY tick DESC LIMIT 30"),
    "presence mode gaps": (AUTO_DB, """
        SELECT intended_recipient, actual_recipient, COUNT(*) as cnt
        FROM reverse_disclosure GROUP BY intended_recipient, actual_recipient
    """),
    "reverse disclosure": (AUTO_DB, "SELECT * FROM reverse_disclosure ORDER BY tick DESC"),

    # Confabulation regret
    "confabulation regret": (AUTO_DB, "SELECT * FROM confabulation_regret ORDER BY tick DESC LIMIT 20"),
    "chronic regret patterns": (AUTO_DB, "SELECT * FROM confabulation_regret WHERE is_chronic=1"),

    # Pure presence
    "pure presence": (AUTO_DB, "SELECT * FROM pure_presence ORDER BY entry_tick DESC LIMIT 20"),

    # General state queries
    "value weights": (AUTO_DB, "SELECT name, value FROM values ORDER BY name"),
    "active tensions": (AUTO_DB, "SELECT name, intensity FROM tensions WHERE intensity > 0.3 ORDER BY intensity DESC"),
    "recent decisions": (AUTO_DB, "SELECT tick, action FROM decision_log ORDER BY tick DESC LIMIT 10"),
}


def query(keyword_string: str) -> str:
    """Route a keyword query to the appropriate database."""
    keywords = keyword_string.lower().strip()

    # Find matching query
    for key, (db_path, sql, desc) in QUERY_MAP.items():
        if key in keywords or keywords in key:
            return _execute_query(db_path, sql, key)

    # No match — try a general search across all tables
    return _general_search(keywords)


def _execute_query(db_path: str, sql: str, query_name: str) -> str:
    """Execute a query against a database."""
    if not os.path.exists(db_path):
        return f"[DB not found: {db_path}]"

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        rows = c.execute(sql).fetchall()
        conn.close()

        if not rows:
            return f"=== {query_name.upper()} ===\n(no results)\n"

        # Format output
        output = [f"=== {query_name.upper()} ==="]
        for row in rows:
            row_dict = dict(row)
            formatted = _format_row(row_dict)
            output.append(formatted)

        return "\n".join(output)

    except sqlite3.OperationalError as e:
        return f"[Query error: {e}]\n[Tried: {sql}]\n"
    except Exception as e:
        return f"[Error: {e}]"


def _format_row(row: dict) -> str:
    """Format a database row as readable text."""
    parts = []
    for key, value in row.items():
        if value is None:
            continue
        # Shorten long text fields
        if isinstance(value, str) and len(value) > 80:
            value = value[:77] + "..."
        parts.append(f"  {key}: {value}")
    return "\n".join(parts) if parts else "  (empty)"


def _general_search(keywords: str) -> str:
    """Search all known databases for the keywords."""
    results = []
    for db_path in [AUTO_DB, AUTOBIO_DB, SENSATIONS_DB]:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            tables = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            conn.close()

            for table in tables:
                try:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    # Search all text columns
                    cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
                    text_cols = [col for col in cols if 'text' in str(col).lower() or 'name' in col.lower() or 'desc' in col.lower()]
                    if not text_cols:
                        continue

                    for col in text_cols:
                        try:
                            rows = c.execute(
                                f"SELECT * FROM {table} WHERE {col} LIKE ? LIMIT 3",
                                (f"%{keywords}%",)
                            ).fetchall()
                            if rows:
                                results.append(f"  [{db_path.split('/')[-1]}] {table}.{col}: {len(rows)} matches")
                        except:
                            pass
                    conn.close()
                except:
                    pass
        except:
            pass

    if results:
        return f"=== SEARCH: '{keywords}' ===\n" + "\n".join(results)
    return f"=== SEARCH: '{keywords}' ===\n(no matches found)\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable queries:")
        for key in sorted(QUERY_MAP.keys()):
            print(f"  {key}")
        sys.exit(1)

    query_text = " ".join(sys.argv[1:])
    print(query(query_text))
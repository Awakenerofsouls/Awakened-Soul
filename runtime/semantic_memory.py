#!/usr/bin/env python3
"""
semantic_memory.py — Concept memory with keyword search and concept linking.

Stores concepts with importance and access-count tracking, plus a separate
links table for typed associations between concepts. Search is keyword-based
(SQL LIKE) — there's no vector embedding layer in this module. Callers that
want true semantic similarity should layer an embedding store on top of, or
alongside, this one.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3


class SemanticMemory:
    """Concept memory backed by SQLite. Keyword search + concept-linking."""

    def __init__(self, db_path: str = None):
        base_dir = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
        self.db_path = db_path or str(base_dir / "semantic.db")
        self._init_db()
    
    def _init_db(self):
        """Initialize semantic memory DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS concepts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      concept TEXT NOT NULL,
                      context TEXT,
                      importance REAL DEFAULT 0.5,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      last_accessed TIMESTAMP,
                      access_count INTEGER DEFAULT 0)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS concept_links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      concept_a TEXT NOT NULL,
                      concept_b TEXT NOT NULL,
                      link_type TEXT,
                      strength REAL DEFAULT 0.5,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
    
    def store_concept(self, concept: str, context: str = None, importance: float = 0.5):
        """Store or update a concept.

        On insert: writes the row with the given context and importance.
        On update: bumps access_count and last_accessed; replaces context if a
        new one was passed (None leaves the existing context); takes the max
        of stored vs. passed importance so strengthening signals are not lost.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT id, context, importance FROM concepts WHERE concept = ?", (concept,))
        existing = c.fetchone()

        if existing:
            new_context = context if context is not None else existing[1]
            new_importance = max(float(existing[2] or 0.0), float(importance))
            c.execute(
                """UPDATE concepts
                   SET access_count = access_count + 1,
                       last_accessed = CURRENT_TIMESTAMP,
                       context = ?,
                       importance = ?
                   WHERE concept = ?""",
                (new_context, new_importance, concept),
            )
        else:
            c.execute(
                """INSERT INTO concepts (concept, context, importance)
                   VALUES (?, ?, ?)""",
                (concept, context, importance),
            )

        conn.commit()
        conn.close()
    
    def link_concepts(self, concept_a: str, concept_b: str, link_type: str = "related", strength: float = 0.5):
        """Link two concepts."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""INSERT INTO concept_links (concept_a, concept_b, link_type, strength)
                   VALUES (?, ?, ?, ?)""", (concept_a, concept_b, link_type, strength))
        
        conn.commit()
        conn.close()
    
    def find_concepts(self, query: str, limit: int = 5) -> List[Dict]:
        """Find concepts similar to query (keyword-based for now)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Simple keyword matching
        c.execute("""SELECT concept, context, importance, access_count
                   FROM concepts 
                   WHERE concept LIKE ? OR context LIKE ?
                   ORDER BY importance DESC, access_count DESC
                   LIMIT ?""", (f"%{query}%", f"%{query}%", limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                "concept": row[0],
                "context": row[1],
                "importance": row[2],
                "access_count": row[3]
            })
        
        conn.close()
        return results
    
    def find_related(self, concept: str, limit: int = 5) -> List[Dict]:
        """Find related concepts."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""SELECT concept_b, link_type, strength FROM concept_links
                   WHERE concept_a = ? OR concept_b = ?
                   ORDER BY strength DESC LIMIT ?""", (concept, concept, limit))
        
        results = []
        for row in c.fetchall():
            results.append({
                "related_concept": row[0],
                "link_type": row[1],
                "strength": row[2]
            })
        
        conn.close()
        return results
    
    def get_concept_count(self) -> int:
        """Get total concepts."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM concepts")
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_link_count(self) -> int:
        """Get total links."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM concept_links")
        count = c.fetchone()[0]
        conn.close()
        return count


# Singleton
_semantic_memory: Optional[SemanticMemory] = None


def get_semantic_memory() -> SemanticMemory:
    """Get semantic memory singleton."""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemory()
    return _semantic_memory


if __name__ == "__main__":
    sm = get_semantic_memory()
    print(f"Concepts: {sm.get_concept_count()}")
    print(f"Links: {sm.get_link_count()}")

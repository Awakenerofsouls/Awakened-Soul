#!/usr/bin/env python3
"""
skills/qmd/qmd.py — Personal-corpus retrieval, native Python.

Pairs with skills/qmd/SKILL.md.

Implements:
  - SQLite FTS5 BM25 keyword search over the workspace markdown corpus
  - Stdlib TF-IDF + cosine vector search (no embeddings dependency)
  - Hybrid combine (BM25 + vector, score-blended)
  - get(path|hash) for direct fetch
  - index / update / status maintenance
  - Per-doc-type source_confidence at result construction time
  - Dream-contamination overlay when runtime/dream_contamination is available

Usage as library:
    from skills.qmd.qmd import QMD
    q = QMD(collection="workspace")
    hits = q.search("the operator's deadline", n=5)
    body = q.get(hits[0]["path"])

Usage as CLI:
    python -m skills.qmd.qmd search "query" -n 5
    python -m skills.qmd.qmd vsearch "fuzzy concept"
    python -m skills.qmd.qmd hybrid "best recall" --alpha 0.6
    python -m skills.qmd.qmd get path/to/file.md
    python -m skills.qmd.qmd index
    python -m skills.qmd.qmd update
    python -m skills.qmd.qmd status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── Paths and constants ──────────────────────────────────────────────────

AGENT_HOME = Path(os.environ.get(
    "AGENT_HOME", str(Path.home() / ".agent")
))
AGENT_WORKSPACE = Path(os.environ.get(
    "AGENT_WORKSPACE", str(Path.home() / ".agent" / "workspace")
))
QMD_INDEX_DIR = AGENT_HOME / "qmd_index"

# Per-doc-type source confidence — see SKILL.md table.
DOC_TYPE_CONFIDENCE: Dict[str, float] = {
    "identity_anchored": 0.95,
    "epistemic": 0.95,
    "personality": 0.90,
    "aesthetic_drives": 0.85,
    "revision_log": 0.95,
    "proposals": 0.85,
    "becoming": 0.85,
    "journal": 0.80,
    "private": 0.80,
    "overnight": 0.70,
    "dreams": 0.40,
    "external": 0.50,
}

# Path → doc-type classifier patterns. First match wins.
DOC_TYPE_PATTERNS: List[Tuple[str, str]] = [
    (r"^(SOUL|IDENTITY|ETHICS)\.md$", "identity_anchored"),
    (r"^EPISTEMIC_BOUNDARIES\.md$", "epistemic"),
    (r"^(PERSONALITY|OCEANS|AGENT_BECOMING|SELF)\.md$", "personality"),
    (r"^(AESTHETIC|IDLE_DRIVES)\.md$", "aesthetic_drives"),
    (r"identity/REVISION_LOG\.md$", "revision_log"),
    (r"identity/PROPOSALS\.md$|^PROPOSALS\.md$", "proposals"),
    (r"^BECOMING\.md$", "becoming"),
    (r"^memory/\d{4}-\d{2}-\d{2}\.md$", "journal"),
    (r"private_entries\.md$", "private"),
    (r"OVERNIGHT_LOG\.md$", "overnight"),
    (r"DREAMS\.md$", "dreams"),
]

DREAM_CONFIDENCE_CAP = 0.40
DEFAULT_HYBRID_ALPHA = 0.6
DEFAULT_N = 5
SNIPPET_LEN = 280

VALID_MODES = {"search", "vsearch", "hybrid", "get"}


# ── Helpers ──────────────────────────────────────────────────────────────


def _hash_path(rel_path: str) -> str:
    """Stable short hash for a path — used as doc_id."""
    return "h_" + hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:10]


def classify_doc_type(rel_path: str) -> str:
    """Map a path (relative to workspace) to a doc_type label."""
    for pattern, label in DOC_TYPE_PATTERNS:
        if re.search(pattern, rel_path):
            return label
    return "external"


def doc_type_confidence(doc_type: str) -> float:
    return DOC_TYPE_CONFIDENCE.get(doc_type, DOC_TYPE_CONFIDENCE["external"])


def _check_dream_contamination(authored_at: float) -> bool:
    """Try to consult runtime.dream_contamination for an authored_at
    interval. Returns True if the timestamp falls in a contamination
    window. If the module isn't importable (unit-test isolation), returns
    False — the layer doesn't fail closed in absence."""
    try:
        from runtime.dream_contamination import is_contaminated  # type: ignore
        return bool(is_contaminated(authored_at))
    except Exception:
        return False


_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


def _make_snippet(text: str, query_tokens: Iterable[str]) -> str:
    """Pull a short window around the first query token hit. Falls back
    to the head of the doc if none found."""
    if not text:
        return ""
    lower = text.lower()
    qts = [t for t in query_tokens if t]
    pos = -1
    for t in qts:
        i = lower.find(t)
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return text[:SNIPPET_LEN].strip()
    start = max(0, pos - 60)
    end = min(len(text), pos + SNIPPET_LEN - 60)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


# ── QMD ──────────────────────────────────────────────────────────────────


class QMD:
    """Personal-corpus retrieval. Library + CLI."""

    def __init__(
        self,
        collection: str = "workspace",
        workspace: Optional[Path] = None,
        index_dir: Optional[Path] = None,
    ):
        self.collection = collection
        self.workspace = Path(workspace) if workspace else AGENT_WORKSPACE
        self.index_dir = Path(index_dir) if index_dir else QMD_INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.index_dir / f"{collection}.db"
        self._init_db()

    # ── DB setup ───────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS docs (
                    doc_id TEXT PRIMARY KEY,
                    rel_path TEXT NOT NULL UNIQUE,
                    doc_type TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    indexed_at REAL NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(
                    doc_id UNINDEXED,
                    content,
                    tokenize='porter'
                );
                CREATE TABLE IF NOT EXISTS tfidf_terms (
                    doc_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    tf INTEGER NOT NULL,
                    PRIMARY KEY (doc_id, term)
                );
                CREATE INDEX IF NOT EXISTS ix_tfidf_term ON tfidf_terms(term);
                CREATE TABLE IF NOT EXISTS doc_stats (
                    doc_id TEXT PRIMARY KEY,
                    length INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    # ── Indexing ───────────────────────────────────────────────────────

    def _iter_corpus(self) -> Iterable[Tuple[Path, str]]:
        """Yield (absolute_path, rel_path) for every .md under workspace."""
        if not self.workspace.exists():
            return
        for path in self.workspace.rglob("*.md"):
            try:
                rel = path.relative_to(self.workspace).as_posix()
            except ValueError:
                continue
            # Skip qmd's own index dir if it lives under workspace.
            if rel.startswith("qmd_index/"):
                continue
            yield path, rel

    def index(self, full: bool = True) -> Dict[str, Any]:
        """Build (or rebuild) the index. If full=False, only update
        files whose mtime is newer than what's stored."""
        added = 0
        updated = 0
        unchanged = 0
        seen_doc_ids = set()

        with self._conn() as conn:
            for path, rel in self._iter_corpus():
                doc_id = _hash_path(rel)
                seen_doc_ids.add(doc_id)
                stat = path.stat()
                row = conn.execute(
                    "SELECT mtime FROM docs WHERE doc_id = ?", (doc_id,)
                ).fetchone()
                if row and not full:
                    if abs(row[0] - stat.st_mtime) < 1e-3:
                        unchanged += 1
                        continue
                content = ""
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                doc_type = classify_doc_type(rel)
                self._write_doc(conn, doc_id, rel, doc_type, stat, content)
                if row:
                    updated += 1
                else:
                    added += 1

            # Drop docs whose paths no longer exist.
            removed = 0
            existing = {
                doc_id for (doc_id,) in conn.execute("SELECT doc_id FROM docs")
            }
            for doc_id in existing - seen_doc_ids:
                self._delete_doc(conn, doc_id)
                removed += 1

            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                ("indexed_at", str(time.time())),
            )

        return {
            "collection": self.collection,
            "workspace": str(self.workspace),
            "added": added,
            "updated": updated,
            "unchanged": unchanged,
            "removed": removed,
        }

    def update(self) -> Dict[str, Any]:
        """Re-index changed files only."""
        return self.index(full=False)

    def _write_doc(
        self,
        conn: sqlite3.Connection,
        doc_id: str,
        rel_path: str,
        doc_type: str,
        stat: os.stat_result,
        content: str,
    ) -> None:
        # Remove any prior copies first.
        self._delete_doc(conn, doc_id)
        conn.execute(
            "INSERT INTO docs(doc_id, rel_path, doc_type, mtime, size, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, rel_path, doc_type, stat.st_mtime, stat.st_size, time.time()),
        )
        conn.execute(
            "INSERT INTO doc_fts(doc_id, content) VALUES (?, ?)",
            (doc_id, content),
        )
        tokens = _tokenize(content)
        if tokens:
            counts = Counter(tokens)
            conn.executemany(
                "INSERT INTO tfidf_terms(doc_id, term, tf) VALUES (?, ?, ?)",
                [(doc_id, term, tf) for term, tf in counts.items()],
            )
            conn.execute(
                "INSERT INTO doc_stats(doc_id, length) VALUES (?, ?)",
                (doc_id, len(tokens)),
            )

    def _delete_doc(self, conn: sqlite3.Connection, doc_id: str) -> None:
        conn.execute("DELETE FROM docs WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM doc_fts WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM tfidf_terms WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM doc_stats WHERE doc_id = ?", (doc_id,))

    # ── Search ─────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n: int = DEFAULT_N,
        doc_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """BM25 keyword search via SQLite FTS5."""
        if not query.strip():
            return []
        q = self._sanitize_fts(query)
        if not q:
            return []
        types_filter = ""
        params: List[Any] = [q]
        if doc_types:
            placeholders = ",".join(["?"] * len(doc_types))
            types_filter = f" AND d.doc_type IN ({placeholders})"
            params.extend(doc_types)
        params.append(int(max(1, n)))
        sql = f"""
            SELECT d.doc_id, d.rel_path, d.doc_type, d.mtime,
                   bm25(doc_fts) AS score, snippet(doc_fts, 1, '', '', '…', 12) AS snip
            FROM doc_fts
            JOIN docs d ON d.doc_id = doc_fts.doc_id
            WHERE doc_fts MATCH ? {types_filter}
            ORDER BY score
            LIMIT ?
        """
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: List[Dict[str, Any]] = []
        qtokens = _tokenize(query)
        for row in rows:
            doc_id, rel, dt, mtime, score, snip = row
            sc = doc_type_confidence(dt)
            if _check_dream_contamination(float(mtime)):
                sc = min(sc, DREAM_CONFIDENCE_CAP)
            content = self._read_doc_content(rel)
            snippet = snip or _make_snippet(content, qtokens)
            out.append({
                "doc_id": doc_id,
                "path": rel,
                "doc_type": dt,
                "source_confidence": round(sc, 3),
                "score_bm25": round(float(score), 4) if score is not None else 0.0,
                "score_vector": None,
                "score_blended": round(float(score), 4) if score is not None else 0.0,
                "snippet": snippet,
                "mtime": datetime.utcfromtimestamp(mtime).isoformat(),
            })
        return out

    def vsearch(
        self,
        query: str,
        n: int = DEFAULT_N,
        doc_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """TF-IDF + cosine vector search."""
        qtokens = _tokenize(query)
        if not qtokens:
            return []
        with self._conn() as conn:
            n_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            if not n_docs:
                return []
            # df per query term
            df: Dict[str, int] = {}
            for term in set(qtokens):
                row = conn.execute(
                    "SELECT COUNT(DISTINCT doc_id) FROM tfidf_terms WHERE term = ?",
                    (term,),
                ).fetchone()
                df[term] = int(row[0] or 0)

            # Build query vector (TF-IDF).
            qcounts = Counter(qtokens)
            qvec: Dict[str, float] = {}
            for term, tf in qcounts.items():
                if df.get(term, 0) == 0:
                    continue
                idf = math.log((1 + n_docs) / (1 + df[term])) + 1.0
                qvec[term] = (1 + math.log(tf)) * idf

            if not qvec:
                return []
            qnorm = math.sqrt(sum(v * v for v in qvec.values()))
            if qnorm <= 0:
                return []

            # Score docs that share ≥1 query term.
            scores: Dict[str, float] = defaultdict(float)
            for term, qw in qvec.items():
                rows = conn.execute(
                    "SELECT doc_id, tf FROM tfidf_terms WHERE term = ?",
                    (term,),
                ).fetchall()
                for doc_id, tf in rows:
                    if tf <= 0:
                        continue
                    idf = math.log((1 + n_docs) / (1 + df[term])) + 1.0
                    dw = (1 + math.log(tf)) * idf
                    scores[doc_id] += qw * dw

            if not scores:
                return []

            # Doc norms (cache as we go).
            doc_norms: Dict[str, float] = {}
            for doc_id in scores:
                norm = self._doc_tfidf_norm(conn, doc_id, n_docs)
                doc_norms[doc_id] = norm
                if norm <= 0:
                    scores[doc_id] = 0.0
                else:
                    scores[doc_id] = scores[doc_id] / (qnorm * norm)

            # Filter by doc_types if given.
            if doc_types:
                placeholders = ",".join(["?"] * len(doc_types))
                allowed = {
                    doc_id for (doc_id,) in conn.execute(
                        f"SELECT doc_id FROM docs WHERE doc_type IN ({placeholders})",
                        doc_types,
                    )
                }
                scores = {k: v for k, v in scores.items() if k in allowed}

            top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]

            out: List[Dict[str, Any]] = []
            for doc_id, score in top:
                if score <= 0:
                    continue
                row = conn.execute(
                    "SELECT rel_path, doc_type, mtime FROM docs WHERE doc_id = ?",
                    (doc_id,),
                ).fetchone()
                if not row:
                    continue
                rel, dt, mtime = row
                sc = doc_type_confidence(dt)
                if _check_dream_contamination(float(mtime)):
                    sc = min(sc, DREAM_CONFIDENCE_CAP)
                content = self._read_doc_content(rel)
                snippet = _make_snippet(content, qtokens)
                out.append({
                    "doc_id": doc_id,
                    "path": rel,
                    "doc_type": dt,
                    "source_confidence": round(sc, 3),
                    "score_bm25": None,
                    "score_vector": round(float(score), 4),
                    "score_blended": round(float(score), 4),
                    "snippet": snippet,
                    "mtime": datetime.utcfromtimestamp(mtime).isoformat(),
                })
            return out

    def _doc_tfidf_norm(
        self,
        conn: sqlite3.Connection,
        doc_id: str,
        n_docs: int,
    ) -> float:
        """Compute TF-IDF norm for a document (used for cosine denominator)."""
        rows = conn.execute(
            "SELECT term, tf FROM tfidf_terms WHERE doc_id = ?",
            (doc_id,),
        ).fetchall()
        norm_sq = 0.0
        for term, tf in rows:
            if tf <= 0:
                continue
            df_row = conn.execute(
                "SELECT COUNT(DISTINCT doc_id) FROM tfidf_terms WHERE term = ?",
                (term,),
            ).fetchone()
            df = int(df_row[0] or 0)
            if df == 0:
                continue
            idf = math.log((1 + n_docs) / (1 + df)) + 1.0
            w = (1 + math.log(tf)) * idf
            norm_sq += w * w
        return math.sqrt(norm_sq)

    def hybrid(
        self,
        query: str,
        n: int = DEFAULT_N,
        alpha: float = DEFAULT_HYBRID_ALPHA,
        doc_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """BM25 + vector, score-blended. alpha is BM25 weight."""
        alpha = max(0.0, min(1.0, float(alpha)))
        # Get extra results from each so the merge has room.
        wider = max(n, 10)
        bm25_hits = self.search(query, n=wider, doc_types=doc_types)
        vec_hits = self.vsearch(query, n=wider, doc_types=doc_types)

        # Normalize scores into 0..1 for both. BM25 is negative & smaller-is-better
        # in SQLite (it returns -score by convention). Convert to a positive scale
        # via 1/(1+|score|) — bounded, monotone, matches practice for ranking blends.
        def _bm25_norm(s: float) -> float:
            return 1.0 / (1.0 + abs(s))

        merged: Dict[str, Dict[str, Any]] = {}
        for h in bm25_hits:
            score_n = _bm25_norm(float(h.get("score_bm25") or 0.0))
            merged[h["doc_id"]] = dict(h)
            merged[h["doc_id"]]["_norm_bm25"] = score_n
            merged[h["doc_id"]]["_norm_vector"] = 0.0

        for h in vec_hits:
            d = merged.setdefault(h["doc_id"], dict(h))
            d.setdefault("_norm_bm25", 0.0)
            d["_norm_vector"] = float(h.get("score_vector") or 0.0)
            # Carry through bm25 if missing.
            if d.get("score_bm25") is None:
                d["score_bm25"] = h.get("score_bm25")
            if d.get("score_vector") is None:
                d["score_vector"] = h.get("score_vector")

        for doc_id, d in merged.items():
            blended = (
                alpha * float(d.get("_norm_bm25") or 0.0)
                + (1.0 - alpha) * float(d.get("_norm_vector") or 0.0)
            )
            d["score_blended"] = round(blended, 4)
            d.pop("_norm_bm25", None)
            d.pop("_norm_vector", None)

        ranked = sorted(
            merged.values(), key=lambda x: x["score_blended"], reverse=True
        )
        return ranked[:n]

    # ── Get ────────────────────────────────────────────────────────────

    def get(self, path_or_hash: str, full: bool = False) -> Dict[str, Any]:
        """Fetch a doc by relative path or doc_id."""
        with self._conn() as conn:
            row = None
            if path_or_hash.startswith("h_"):
                row = conn.execute(
                    "SELECT doc_id, rel_path, doc_type, mtime FROM docs "
                    "WHERE doc_id = ?",
                    (path_or_hash,),
                ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT doc_id, rel_path, doc_type, mtime FROM docs "
                    "WHERE rel_path = ?",
                    (path_or_hash,),
                ).fetchone()
        if not row:
            return {"ok": False, "reason": f"not found: {path_or_hash!r}"}
        doc_id, rel, dt, mtime = row
        content = self._read_doc_content(rel)
        sc = doc_type_confidence(dt)
        if _check_dream_contamination(float(mtime)):
            sc = min(sc, DREAM_CONFIDENCE_CAP)
        body = content if full else content[:2000]
        return {
            "ok": True,
            "doc_id": doc_id,
            "path": rel,
            "doc_type": dt,
            "source_confidence": round(sc, 3),
            "mtime": datetime.utcfromtimestamp(mtime).isoformat(),
            "content": body,
            "truncated": (not full) and len(content) > 2000,
        }

    def _read_doc_content(self, rel_path: str) -> str:
        try:
            return (self.workspace / rel_path).read_text(
                encoding="utf-8", errors="replace"
            )
        except Exception:
            return ""

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Index health: doc count, last-indexed-at, mtime drift count."""
        with self._conn() as conn:
            n_docs = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            indexed_at = conn.execute(
                "SELECT value FROM meta WHERE key = 'indexed_at'"
            ).fetchone()
            indexed_at = float(indexed_at[0]) if indexed_at else 0.0
            # Per-doc-type counts.
            type_counts = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT doc_type, COUNT(*) FROM docs GROUP BY doc_type"
                )
            }

        # mtime drift: how many on-disk files are newer than what we indexed?
        drift = 0
        for path, rel in self._iter_corpus():
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT mtime FROM docs WHERE rel_path = ?", (rel,)
                ).fetchone()
            try:
                if not row or path.stat().st_mtime - float(row[0]) > 1.0:
                    drift += 1
            except FileNotFoundError:
                continue

        return {
            "collection": self.collection,
            "workspace": str(self.workspace),
            "db_path": str(self.db_path),
            "doc_count": n_docs,
            "doc_type_counts": type_counts,
            "indexed_at": (
                datetime.utcfromtimestamp(indexed_at).isoformat() if indexed_at else None
            ),
            "mtime_drift_count": drift,
            "stale_index": drift > 0,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_fts(query: str) -> str:
        """Strip FTS5 metacharacters that would otherwise break MATCH."""
        # FTS5 query syntax allows " * ( ) AND OR NOT NEAR — we keep terms
        # only so a free-form query is treated as a phrase / OR of terms.
        cleaned = re.sub(r"[\"\(\)\*\:]", " ", query)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return ""
        # Wrap each term so users can't accidentally trigger FTS operators.
        terms = [t for t in cleaned.split() if t.lower() not in {"and", "or", "not", "near"}]
        if not terms:
            return ""
        return " OR ".join(f'"{t}"' for t in terms)


# ── CLI ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="qmd", description=__doc__)
    parser.add_argument(
        "-c", "--collection", default="workspace",
        help="Collection name (index file under AGENT_HOME/qmd_index/)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON output",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="BM25 keyword search")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("-n", type=int, default=DEFAULT_N)
    p_search.add_argument("--types", nargs="*", default=None)

    p_v = sub.add_parser("vsearch", help="Vector similarity search")
    p_v.add_argument("query", nargs="+")
    p_v.add_argument("-n", type=int, default=DEFAULT_N)
    p_v.add_argument("--types", nargs="*", default=None)

    p_h = sub.add_parser("hybrid", help="Hybrid BM25 + vector")
    p_h.add_argument("query", nargs="+")
    p_h.add_argument("-n", type=int, default=DEFAULT_N)
    p_h.add_argument("--alpha", type=float, default=DEFAULT_HYBRID_ALPHA)

    p_get = sub.add_parser("get", help="Fetch a doc by path or hash")
    p_get.add_argument("path_or_hash")
    p_get.add_argument("--full", action="store_true")

    sub.add_parser("index", help="Build / rebuild the index")
    sub.add_parser("update", help="Re-index changed files only")
    sub.add_parser("status", help="Show index health")

    args = parser.parse_args()
    q = QMD(collection=args.collection)

    def _emit(obj: Any) -> None:
        if args.json:
            print(json.dumps(obj, indent=2, default=str))
        else:
            print(json.dumps(obj, indent=2, default=str))

    if args.cmd == "search":
        _emit(q.search(" ".join(args.query), n=args.n, doc_types=args.types))
    elif args.cmd == "vsearch":
        _emit(q.vsearch(" ".join(args.query), n=args.n, doc_types=args.types))
    elif args.cmd == "hybrid":
        _emit(q.hybrid(" ".join(args.query), n=args.n, alpha=args.alpha))
    elif args.cmd == "get":
        _emit(q.get(args.path_or_hash, full=args.full))
    elif args.cmd == "index":
        _emit(q.index(full=True))
    elif args.cmd == "update":
        _emit(q.update())
    elif args.cmd == "status":
        _emit(q.status())
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())

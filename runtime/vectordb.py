#!/usr/bin/env python3
"""
AGENT VECTORDB — Vector Database Support
LanceDB, ChromaDB, Qdrant, or numpy fallback.

Proper vector storage for semantic memory.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from enum import Enum
import os
# Configuration
AGENT_DIR = Path(os.getenv("AGENT_HOME", str(Path.home() / ".agent")))
VECTOR_DB_DIR = AGENT_DIR / "vector_db"
CONFIG_FILE = AGENT_DIR / "vector_config.json"


class VectorBackend(Enum):
    """Available vector backends."""
    LANCEDB = "lancedb"
    CHROMADB = "chromadb"
    QDRANT = "qdrant"
    NUMPY = "numpy"  # Fallback


class VectorDB:
    """Vector database wrapper."""
    
    def __init__(self, backend: str = "auto"):
        self.backend = self._select_backend(backend)
        self.client = None
        self.collection = None
        self._init()
    
    def _select_backend(self, backend: str) -> str:
        """Select best available backend."""
        
        if backend != "auto":
            return backend
        
        # Try each backend
        backends = ["lancedb", "chromadb", "qdrant", "numpy"]
        
        for b in backends:
            if self._check_backend(b):
                return b
        
        return "numpy"
    
    def _check_backend(self, backend: str) -> bool:
        """Check if backend is available."""

        try:
            if backend == "lancedb":
                import lancedb  # noqa: F401
                return True
            elif backend == "chromadb":
                import chromadb  # noqa: F401
                return True
            elif backend == "qdrant":
                # Real package name is `qdrant_client`, not `qdrant`.
                import qdrant_client  # noqa: F401
                return True
            elif backend == "numpy":
                return True
        except ImportError:
            pass

        return False
    
    def _init(self):
        """Initialize the backend."""
        
        VECTOR_DB_DIR.mkdir(exist_ok=True)
        
        if self.backend == "lancedb":
            self._init_lancedb()
        elif self.backend == "chromadb":
            self._init_chromadb()
        elif self.backend == "qdrant":
            self._init_qdrant()
        elif self.backend == "numpy":
            self._init_numpy()
    
    def _init_lancedb(self):
        """Initialize LanceDB.

        NOTE: the current `_add_lancedb` is a stub that writes to in-memory
        numpy lists rather than the LanceDB table — see its docstring. The
        LanceDB connection is opened here for forward compatibility but
        nothing reads from it yet. Storage is non-persistent until that's
        wired. Use the `numpy` or `chromadb` backend if you need persistence.
        """
        try:
            import lancedb
            self.client = lancedb.connect(str(VECTOR_DB_DIR / "lancedb"))

            # Open existing table if present, otherwise leave self.collection
            # as None — we never want to overwrite live data on startup.
            try:
                self.collection = self.client.open_table("agent_memory")
            except Exception:
                self.collection = None

            # Initialize numpy-backed lists used by the stub _add_lancedb.
            self._init_numpy()

        except ImportError:
            print("LanceDB not available, falling back to numpy")
            self.backend = "numpy"
            self._init_numpy()
    
    def _init_chromadb(self):
        """Initialize ChromaDB."""
        
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR / "chromadb"))
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection("agent_memory")
        
        except ImportError:
            print("ChromaDB not available, falling back to numpy")
            self.backend = "numpy"
            self._init_numpy()
    
    def _init_qdrant(self):
        """Initialize Qdrant — opens client and ensures the collection exists."""

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qmodels
            self.client = QdrantClient(path=str(VECTOR_DB_DIR / "qdrant"))

            # Ensure the collection exists. We use a 256-d vector to match
            # what _embed() returns (128 hash bytes + 128 zero pad).
            try:
                existing = {c.name for c in self.client.get_collections().collections}
            except Exception:
                existing = set()
            if "agent_memory" not in existing:
                try:
                    self.client.recreate_collection(
                        collection_name="agent_memory",
                        vectors_config=qmodels.VectorParams(
                            size=256, distance=qmodels.Distance.COSINE
                        ),
                    )
                except Exception as e:
                    print(f"Qdrant collection init failed: {e}; falling back to numpy")
                    self.backend = "numpy"
                    self._init_numpy()

        except ImportError:
            print("Qdrant not available, falling back to numpy")
            self.backend = "numpy"
            self._init_numpy()
    
    def _init_numpy(self):
        """Initialize numpy fallback."""
        
        self.vectors = []
        self.metadata = []
        self.ids = []
        self.next_id = 0
    
    def add(self, text: str, metadata: Dict = None, id: str = None):
        """Add a vector."""
        
        vector = self._embed(text)
        
        if id is None:
            id = f"doc_{self.next_id}"
            self.next_id += 1
        
        if self.backend == "lancedb":
            self._add_lancedb(vector, text, metadata, id)
        elif self.backend == "chromadb":
            self._add_chromadb(vector, text, metadata, id)
        elif self.backend == "qdrant":
            self._add_qdrant(vector, text, metadata, id)
        elif self.backend == "numpy":
            self._add_numpy(vector, text, metadata, id)
    
    def _embed(self, text: str) -> List[float]:
        """Get embedding for text."""
        
        # Try sentence-transformers first
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            return model.encode(text).tolist()
        except ImportError:
            pass
        
        # Fallback: simple hash-based vector
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in h[:128]] + [0.0] * 128
    
    def _add_lancedb(self, vector, text, metadata, id):
        """Add to LanceDB.

        STUB: actual LanceDB writes are not yet wired — we mirror the entry
        into the in-memory numpy lists instead so search still works. Text is
        stored alongside metadata so search results carry it back.
        """
        self.vectors.append(vector)
        md = dict(metadata or {})
        md.setdefault("text", text)
        self.metadata.append(md)
        self.ids.append(id)
    
    def _add_chromadb(self, vector, text, metadata, id):
        """Add to ChromaDB."""
        
        self.collection.add(
            embeddings=[vector],
            documents=[text],
            metadatas=[metadata or {}],
            ids=[id]
        )
    
    def _add_qdrant(self, vector, text, metadata, id):
        """Add to Qdrant. id must be int or UUID — we hash strings to int."""
        from qdrant_client.http import models as qmodels

        # Qdrant requires int or UUID ids — coerce strings deterministically.
        if isinstance(id, str):
            import hashlib
            point_id = int(hashlib.md5(id.encode()).hexdigest()[:15], 16)
        else:
            point_id = id

        self.client.upsert(
            collection_name="agent_memory",
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": text, **(metadata or {})},
                )
            ],
        )
    
    def _add_numpy(self, vector, text, metadata, id):
        """Add to numpy fallback. Stores text inside metadata so search
        results can return it (search reads metadata['text'])."""
        self.vectors.append(vector)
        md = dict(metadata or {})
        md.setdefault("text", text)
        self.metadata.append(md)
        self.ids.append(id)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar vectors."""

        query_vector = self._embed(query)

        if self.backend == "chromadb":
            return self._search_chromadb(query_vector, top_k)
        elif self.backend == "qdrant":
            return self._search_qdrant(query_vector, top_k)
        # lancedb stub uses the numpy lists, so fall through to numpy.
        return self._search_numpy(query_vector, top_k)

    def _search_qdrant(self, query_vector, top_k):
        """Search Qdrant collection."""
        try:
            hits = self.client.search(
                collection_name="agent_memory",
                query_vector=query_vector,
                limit=top_k,
            )
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []

        out = []
        for h in hits:
            payload = getattr(h, "payload", None) or {}
            score = getattr(h, "score", 0.0) or 0.0
            out.append({
                "text": payload.get("text", ""),
                "metadata": payload,
                "distance": float(1.0 - score),
            })
        return out
    
    def _search_chromadb(self, query_vector, top_k):
        """Search ChromaDB."""
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )
        
        return [
            {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            }
            for i in range(len(results["documents"][0]))
        ]
    
    def _search_numpy(self, query_vector, top_k):
        """Search numpy fallback."""
        
        import numpy as np
        
        if not self.vectors:
            return []
        
        # Calculate cosine similarity
        vectors = np.array(self.vectors)
        query = np.array(query_vector)
        
        # Normalize
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        query = query / np.linalg.norm(query)
        
        # Similarity
        similarities = np.dot(vectors, query)
        
        # Top k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [
            {
                "text": self.metadata[i].get("text", ""),
                "metadata": self.metadata[i],
                "distance": float(1 - similarities[i])
            }
            for i in top_indices
        ]
    
    def delete(self, id: str):
        """Delete a vector."""
        
        if self.backend == "chromadb":
            self.collection.delete(ids=[id])
        elif self.backend == "numpy":
            idx = self.ids.index(id)
            del self.vectors[idx]
            del self.metadata[idx]
            del self.ids[idx]
    
    def count(self) -> int:
        """Count vectors."""
        
        if self.backend == "chromadb":
            return self.collection.count()
        elif self.backend == "numpy":
            return len(self.vectors)
        
        return len(self.vectors)


class VectorMemory:
    """Vector-backed semantic memory."""
    
    def __init__(self, backend: str = "auto"):
        self.db = VectorDB(backend)
    
    def remember(self, content: str, memory_type: str = "episodic", importance: int = 5):
        """Remember something with vector storage."""
        
        self.db.add(
            text=content,
            metadata={
                "type": memory_type,
                "importance": importance,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall relevant memories."""
        
        results = self.db.search(query, top_k=limit)
        
        return [
            {
                "content": r.get("text", r.get("metadata", {}).get("text", "")),
                "relevance": 1 - r.get("distance", 0),
                "metadata": r.get("metadata", {})
            }
            for r in results
        ]


# CLI
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="the agent VectorDB")
    parser.add_argument('command', choices=['status', 'search', 'add', 'migrate', 'clear'])
    parser.add_argument('args', nargs='*')
    parser.add_argument('--backend', default='auto')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        db = VectorDB(args.backend)
        print(f"Backend: {db.backend}")
        print(f"Vectors: {db.count()}")
    
    elif args.command == 'search' and args.args:
        db = VectorDB(args.backend)
        query = ' '.join(args.args)
        results = db.search(query)
        
        print(f"\nSearch: {query}")
        print(f"Results: {len(results)}\n")
        
        for i, r in enumerate(results, 1):
            text = r.get("text", "")[:100]
            dist = r.get("distance", 0)
            print(f"{i}. {text}... (dist: {dist:.3f})")
    
    elif args.command == 'add' and args.args:
        db = VectorDB(args.backend)
        text = ' '.join(args.args)
        db.add(text, {"source": "cli"})
        print(f"Added: {text[:50]}...")
    
    elif args.command == 'migrate':
        # No source schema is wired in this module — migration is the
        # caller's responsibility. We surface that explicitly rather than
        # silently no-op'ing.
        print("migrate: no source schema configured in vectordb.py.")
        print("        Pass your source records to VectorDB().add() in your own script.")

    elif args.command == 'clear':
        db = VectorDB(args.backend)
        if db.backend == "numpy":
            db.vectors = []
            db.metadata = []
            db.ids = []
            print(f"Cleared in-memory vectors (backend={db.backend})")
        elif db.backend == "chromadb":
            try:
                db.client.delete_collection("agent_memory")
                print("Cleared chromadb collection 'agent_memory'")
            except Exception as e:
                print(f"clear failed: {e}")
        else:
            print(f"clear not yet wired for backend={db.backend}; "
                  f"delete the directory under {VECTOR_DB_DIR} manually")


if __name__ == '__main__':
    main()

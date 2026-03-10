"""A very simple on‑disk vector store implementation used for both document
retrieval and conversation memory.

The goal is not to be production‑grade; it is just enough to get a RAG proof‑of‑
concept working inside the existing project structure.  The backing store is a
pickle file containing three parallel lists (ids, texts, vectors).  Searches are
done with brute‑force cosine similarity.
"""

import os
import pickle
from typing import Any

import numpy as np

from pipelines.embeddings import get_embeddings


class VectorStore:
    def __init__(self, path: str | None = None):
        self.path = path
        self.ids: list[str] = []
        self.texts: list[str] = []
        self.vectors: list[list[float]] = []

        if path and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                    self.ids = data.get("ids", [])
                    self.texts = data.get("texts", [])
                    self.vectors = data.get("vectors", [])
            except Exception:
                # corrupted file, start fresh
                self.ids = []
                self.texts = []
                self.vectors = []

    def add(self, id: str, text: str, embedding: list[float]) -> None:
        """Add a single (id, text, embedding) triple to the store."""
        self.ids.append(id)
        self.texts.append(text)
        self.vectors.append(embedding)

    def search_by_embedding(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Return the ``top_k`` documents whose vectors are closest to ``query_embedding``.

        Each hit is a dict with keys ``id``, ``text`` and ``score`` (cosine
        similarity).
        """
        if not self.vectors:
            return []

        arr = np.array(self.vectors, dtype=np.float32)
        q = np.array(query_embedding, dtype=np.float32)
        # cosine similarity = dot(a, b) / (||a||*||b||); since we only need
        # relative ordering we can omit the denominator.
        sims = arr.dot(q)
        best_idx = np.argsort(-sims)[:top_k]
        results = []
        for i in best_idx:
            results.append({
                "id": self.ids[i],
                "text": self.texts[i],
                "score": float(sims[i]),
            })
        return results

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Convenience wrapper that embeds ``query`` and calls :meth:`search_by_embedding`."""
        query_emb = get_embeddings([query])
        if not query_emb:
            return []
        return self.search_by_embedding(query_emb[0], top_k)

    def save(self) -> None:
        """Persist the store to disk if a path was provided."""
        if not self.path:
            return
        try:
            with open(self.path, "wb") as f:
                pickle.dump({
                    "ids": self.ids,
                    "texts": self.texts,
                    "vectors": self.vectors,
                }, f)
        except Exception:
            pass

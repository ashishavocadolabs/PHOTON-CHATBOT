"""High‑level helper that reads documents from disk, chunks them, computes
embeddings and indexes them in a vector store.

This module is deliberately thin; it glues together the lower‑level pipeline
steps that are implemented elsewhere in the repository.
"""

import os
from .chunking import chunk_text
from .embeddings import get_embeddings
from retrieval.vector_store import VectorStore


def ingest_directory(path: str, index_path: str) -> VectorStore:
    """Walk ``path`` recursively and add every file to a vector index.

    The generated index is persisted to ``index_path`` so subsequent runs can
    load the already-built store and add new documents incrementally.
    """

    store = VectorStore(index_path)

    for root, _, files in os.walk(path):
        for filename in files:
            full = os.path.join(root, filename)
            text = None
            if full.lower().endswith(".pdf"):
                # simple PDF text extraction
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(full)
                    pages = []
                    for p in reader.pages:
                        pages.append(p.extract_text() or "")
                    text = "\n".join(pages)
                except Exception:
                    text = None
            else:
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    text = None
            if not text:
                # skip binary / unreadable files
                continue

            chunks = chunk_text(text)
            if not chunks:
                continue

            embeddings = get_embeddings(chunks)
            for chunk, emb in zip(chunks, embeddings):
                store.add(id=full, text=chunk, embedding=emb)

    store.save()
    return store

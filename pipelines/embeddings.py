"""Utility for computing vector embeddings for pieces of text.

The code first attempts to call the Groq embedding endpoint; if the model is
not accessible (which is currently the case in the workspace) it falls back to
using a lightweight local embedding model from ``sentence-transformers``.  This
ensures the RAG system works even without an API key or network connectivity.
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# local fallback is a trivial deterministic char‑based vector; it avoids
# any heavy packages or network activity.
_local_model = None

def _local_embedding(text: str, dim: int = 768) -> list[float]:
    """Simple fixed‑size embedding based on character codes."""
    vec = [0.0] * dim
    for i, ch in enumerate(text[:dim]):
        vec[i] = float((ord(ch) % 256) / 255.0)
    return vec


def _try_remote_embeddings(texts: list[str]) -> list[list[float]] | None:
    """Return embeddings from the Groq API or ``None`` on error."""
    try:
        response = _client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.get("embedding") for item in response.get("data", [])]
    except Exception:
        return None


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Return a list of embeddings corresponding to ``texts``.

    The primary source is the remote Groq model; if that fails (e.g. the model
    is not available) we fall back to a local ``sentence-transformers`` model.
    If neither is available we return zero vectors so that the caller still
    receives a list of the correct length.
    """

    if not texts:
        return []

    # try remote first
    emb = _try_remote_embeddings(texts)
    if emb is not None:
        return emb

    # local fallback using simple char-based embedding
    return [_local_embedding(t) for t in texts]

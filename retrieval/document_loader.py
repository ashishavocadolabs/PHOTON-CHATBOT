"""
Document Loader
Reads .txt files from the knowledge_base folder and prepares them for chunking.
"""
import os
import hashlib
from retrieval.rag_config import KNOWLEDGE_BASE_DIR, SUPPORTED_EXTENSIONS


def _file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def load_documents() -> list[dict]:
    """
    Scan knowledge_base directory and return a list of document dicts:
      { "text": str, "metadata": { "source": str, "file_hash": str } }
    """
    documents = []

    if not os.path.isdir(KNOWLEDGE_BASE_DIR):
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        return documents

    for root, _, files in os.walk(KNOWLEDGE_BASE_DIR):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, KNOWLEDGE_BASE_DIR)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="latin-1") as f:
                    content = f.read().strip()

            if not content:
                continue

            documents.append({
                "text": content,
                "metadata": {
                    "source": rel_path,
                    "file_hash": _file_hash(filepath),
                }
            })

    return documents

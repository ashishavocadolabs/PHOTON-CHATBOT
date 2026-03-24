"""
Vector Store
ChromaDB-backed persistent vector store for document embeddings.
Handles collection management, upserting, and deduplication via file hashes.
"""
import os
import chromadb
from retrieval.rag_config import CHROMA_PERSIST_DIR, COLLECTION_NAME
from retrieval.embedding_manager import embed_texts

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def get_indexed_hashes() -> set:
    """Return set of file_hashes already stored in the collection."""
    collection = get_collection()
    if collection.count() == 0:
        return set()

    results = collection.get(include=["metadatas"])
    hashes = set()
    for meta in results["metadatas"]:
        if meta and "file_hash" in meta:
            hashes.add(meta["file_hash"])
    return hashes


def remove_by_hash(file_hash: str):
    """Delete all chunks belonging to a specific file hash."""
    collection = get_collection()
    if collection.count() == 0:
        return

    results = collection.get(
        where={"file_hash": file_hash},
        include=["metadatas"],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])


def upsert_chunks(chunks: list[dict]):
    """
    Insert or update chunks into ChromaDB.
    Each chunk: { "text": str, "metadata": { "source", "file_hash", "chunk_index" } }
    Deduplication: if a file_hash already exists, its old chunks are removed first.
    """
    if not chunks:
        return

    collection = get_collection()

    # Group by file_hash for dedup
    hash_groups: dict[str, list[dict]] = {}
    for chunk in chunks:
        fh = chunk["metadata"]["file_hash"]
        hash_groups.setdefault(fh, []).append(chunk)

    existing_hashes = get_indexed_hashes()

    for file_hash, file_chunks in hash_groups.items():
        # Remove old version if it exists
        if file_hash in existing_hashes:
            remove_by_hash(file_hash)

        ids = []
        documents = []
        metadatas = []
        texts_for_embedding = []

        for chunk in file_chunks:
            chunk_id = f"{file_hash}_{chunk['metadata']['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])
            texts_for_embedding.append(chunk["text"])

        # Batch embed
        embeddings = embed_texts(texts_for_embedding)

        # Upsert in batches of 500 (ChromaDB limit safe)
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            collection.upsert(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )


def get_store_stats() -> dict:
    """Return basic stats about the vector store."""
    collection = get_collection()
    count = collection.count()
    hashes = get_indexed_hashes()
    return {
        "total_chunks": count,
        "total_documents": len(hashes),
    }

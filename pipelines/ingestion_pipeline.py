"""
Ingestion Pipeline
End-to-end pipeline: Load documents → Chunk → Embed → Store in ChromaDB.
Supports incremental ingestion (only processes new/changed files).
"""
import logging
from retrieval.document_loader import load_documents
from retrieval.text_chunker import chunk_documents
from retrieval.vector_store import upsert_chunks, get_indexed_hashes, get_store_stats

logger = logging.getLogger("photon.ingestion")


def ingest_documents(force: bool = False) -> dict:
    """
    Run the full ingestion pipeline.

    Args:
        force: If True, re-ingest all documents regardless of hash.

    Returns:
        dict with ingestion stats.
    """
    documents = load_documents()

    if not documents:
        return {
            "status": "no_documents",
            "message": "No .txt files found in knowledge_base/",
            "files_processed": 0,
            "chunks_created": 0,
        }

    # Incremental: skip files whose hash is already indexed
    if not force:
        existing_hashes = get_indexed_hashes()
        new_documents = [
            doc for doc in documents
            if doc["metadata"]["file_hash"] not in existing_hashes
        ]
    else:
        new_documents = documents

    if not new_documents:
        stats = get_store_stats()
        return {
            "status": "up_to_date",
            "message": "All documents already indexed. No new files to process.",
            "files_processed": 0,
            "chunks_created": 0,
            "total_chunks": stats["total_chunks"],
            "total_documents": stats["total_documents"],
        }

    # Chunk the new documents
    chunks = chunk_documents(new_documents)

    # Embed and store
    upsert_chunks(chunks)

    stats = get_store_stats()

    file_names = [doc["metadata"]["source"] for doc in new_documents]
    logger.info(f"Ingested {len(new_documents)} files → {len(chunks)} chunks")

    return {
        "status": "success",
        "message": f"Ingested {len(new_documents)} file(s) into vector store.",
        "files_processed": len(new_documents),
        "files": file_names,
        "chunks_created": len(chunks),
        "total_chunks": stats["total_chunks"],
        "total_documents": stats["total_documents"],
    }

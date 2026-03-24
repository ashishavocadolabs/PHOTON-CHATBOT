"""
RAG Retriever
Queries the ChromaDB vector store and returns relevant context chunks.
Includes source-boost logic to prioritize exact document matches.
"""
import os
from retrieval.vector_store import get_collection
from retrieval.embedding_manager import embed_query
from retrieval.rag_config import TOP_K_RESULTS, SIMILARITY_THRESHOLD


def _detect_target_source(query: str) -> str | None:
    """
    Detect if the user is asking about a specific known document/module.
    Returns the expected source filename or None.
    """
    q = query.lower().strip()

    # Order matters: check more specific names first
    source_map = [
        (["spot rate request", "spot rate", "spot request"], "Spot Rate Request.txt"),
        (["rate request", "rate shopping"], "Rate Request.txt"),
        (["dashboard", "analytics dashboard", "logistics dashboard"], "Dashboard.txt"),
        (["report module", "report", "reports"], "Report_Module.txt"),
        (["shipment module", "ship a box", "mass shipping", "sap shipping"], "Shipment_Module.txt"),
        (["get quote", "quote module"], "Get Quote.txt"),
    ]

    for phrases, source_file in source_map:
        for phrase in phrases:
            if phrase in q:
                return source_file
    return None


def retrieve(query: str, top_k: int = TOP_K_RESULTS) -> list[dict]:
    """
    Perform semantic search against the vector store.
    If user is asking about a specific module, boost chunks from that source.

    Returns list of:
      { "text": str, "source": str, "score": float }
    """
    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = embed_query(query)

    # Fetch more results to allow source-boosting to work
    fetch_count = min(top_k * 3, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=fetch_count,
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    seen_texts = set()

    if not results or not results["documents"] or not results["documents"][0]:
        return []

    target_source = _detect_target_source(query)

    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Deduplicate identical chunks
        text_key = doc[:120]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        score = 1 - (distance / 2)

        if score < SIMILARITY_THRESHOLD:
            continue

        # Source-boost: if user is asking about a specific module,
        # boost chunks from the matching document
        source = meta.get("source", "unknown")
        if target_source:
            if source == target_source:
                score += 0.15  # Boost matching source
            else:
                score -= 0.05  # Slight penalty for non-matching

        retrieved.append({
            "text": doc,
            "source": source,
            "score": round(score, 4),
        })

    retrieved.sort(key=lambda x: x["score"], reverse=True)

    return retrieved[:top_k]


def build_context(query: str, top_k: int = TOP_K_RESULTS) -> str:
    """
    Retrieve relevant chunks, group by source document, and format
    as a structured context block for LLM injection.
    Returns empty string if no relevant context found.
    """
    results = retrieve(query, top_k)

    if not results:
        return ""

    # Group chunks by source document
    source_groups: dict[str, list[dict]] = {}
    seen_texts = set()

    for r in results:
        text_key = r["text"][:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        source = r["source"]
        source_groups.setdefault(source, []).append(r)

    # Build context with clear document separation
    context_parts = []
    for source, chunks in source_groups.items():
        doc_name = source.replace(".txt", "").replace("_", " ")
        avg_score = round(sum(c["score"] for c in chunks) / len(chunks), 4)
        section = f"=== DOCUMENT: {doc_name} (Relevance: {avg_score}) ==="
        for chunk in chunks:
            section += f"\n{chunk['text']}"
        context_parts.append(section)

    return "\n\n" + "\n\n".join(context_parts)

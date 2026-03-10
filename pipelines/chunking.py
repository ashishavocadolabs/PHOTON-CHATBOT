"""Simple text chunking utilities used by the ingestion pipeline.

The rough idea is to break large documents into smaller overlapping pieces so that
neighbouring chunks share some context.  The current implementation is very naive
(operates on character counts) but it is enough to get a working RAG system.  You
can always swap it out for a tokenizer-based splitter later.
"""

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Split ``text`` into chunks of at most ``max_chars`` characters.

    ``overlap`` characters are repeated between consecutive chunks so that the
    vector store retrieval has a little bit of contextual continuity.
    """

    if not text:
        return []

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(length, start + max_chars)
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        # avoid infinite loop when text shorter than max_chars
        if end == length:
            break

    return chunks

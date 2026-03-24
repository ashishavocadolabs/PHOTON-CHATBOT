"""
Text Chunker
Splits documents into overlapping chunks with metadata preserved.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from retrieval.rag_config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Takes raw documents and returns chunks:
      { "text": str, "metadata": { "source": str, "file_hash": str, "chunk_index": int } }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = []

    for doc in documents:
        text_chunks = splitter.split_text(doc["text"])

        for idx, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": idx,
                }
            })

    return chunks

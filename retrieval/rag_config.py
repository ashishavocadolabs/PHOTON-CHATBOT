"""
RAG Configuration
Centralized settings for the Retrieval-Augmented Generation pipeline.
"""
import os

# =====================================================
# PATHS
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "vector_store", "chroma_db")

# =====================================================
# EMBEDDING MODEL
# =====================================================
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# =====================================================
# CHUNKING
# =====================================================
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# =====================================================
# CHROMA COLLECTION
# =====================================================
COLLECTION_NAME = "photon_knowledge"

# =====================================================
# RETRIEVAL
# =====================================================
TOP_K_RESULTS = 8
SIMILARITY_THRESHOLD = 0.35

# =====================================================
# SUPPORTED FILE TYPES
# =====================================================
SUPPORTED_EXTENSIONS = [".txt"]

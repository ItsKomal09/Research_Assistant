import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_huggingface import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# 1. EMBEDDING MODEL SETUP
# ────────────────────────────────────────────────────

_embedding_model = None  # module-level singleton


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Returns a singleton embedding model.
    
    Singleton pattern because:
    - Model takes ~3-5 seconds to load from disk
    - Loading it fresh on every request would kill performance
    - One instance shared across vectorstore + retriever
    
    BAAI/bge-base-en-v1.5 is chosen because:
    - Free, runs fully local (no API key)
    - 768-dim embeddings, strong on academic/technical text
    - Consistently ranks top on MTEB benchmark
    - Small enough to run on CPU without issues
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        logger.info("First load takes 30-60 seconds, cached after that...")

        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},    # change to "cuda" if you have GPU
            encode_kwargs={
                "normalize_embeddings": True,  # required for BAAI/bge models
                "batch_size": 32               # process 32 chunks at once
            }
        )
        logger.info("Embedding model loaded successfully")

    return _embedding_model


# ────────────────────────────────────────────────────
# 2. EMBED DOCUMENTS (used for testing + validation)
# ────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Directly embed a list of strings.
    Used in tests to verify the model is working.
    
    Returns list of vectors, one per input text.
    Each vector is 768 floats for BAAI/bge-base-en-v1.5.
    """
    model = get_embedding_model()
    vectors = model.embed_documents(texts)
    logger.info(f"Embedded {len(texts)} texts → {len(vectors[0])}-dim vectors")
    return vectors


def embed_query(query: str) -> list[float]:
    """
    Embed a single query string.
    Used by retriever at search time (different from doc embedding).
    
    Note: BAAI/bge models use a special query prefix internally,
    normalize_embeddings=True handles this automatically.
    """
    model = get_embedding_model()
    vector = model.embed_query(query)
    logger.info(f"Query embedded → {len(vector)}-dim vector")
    return vector
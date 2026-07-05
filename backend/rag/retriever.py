import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_chroma import Chroma
from rag.vectorstore import get_vectorstore
from config import RETRIEVER_K, RETRIEVER_FETCH_K, BM25_K, DENSE_WEIGHT, SPARSE_WEIGHT
from typing import List
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# 1. DENSE RETRIEVER (MMR)
# ────────────────────────────────────────────────────

def get_dense_retriever(vectorstore: Chroma, k: int = RETRIEVER_K):
    """
    MMR = Maximal Marginal Relevance.
    
    Standard top-k just returns the k most similar chunks.
    Problem: if your PDF has the same concept on 5 pages,
    you get 5 near-identical chunks — wasted context window.
    
    MMR balances:
    - Relevance  → chunk must be similar to the query
    - Diversity  → chunk must be different from already-selected chunks
    
    fetch_k=20 → fetch 20 candidates from vector store
    k=6        → MMR picks best 6 from those 20
    """
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": RETRIEVER_FETCH_K,
            "lambda_mult": 0.6   # 0=max diversity, 1=max relevance, 0.6 is balanced
        }
    )


# ────────────────────────────────────────────────────
# 2. SPARSE RETRIEVER (BM25)
# ────────────────────────────────────────────────────

def get_sparse_retriever(docs: List[Document], k: int = BM25_K) -> BM25Retriever:
    """
    BM25 = Best Match 25 (classic information retrieval algorithm).
    
    Works on raw text — no embeddings needed.
    Strong when the query contains specific technical terms,
    author names, paper titles, or acronyms that vector search
    might miss due to tokenization.
    
    Example where BM25 wins:
    Query: "FAISS index flat L2"
    Vector search: finds semantically similar text about indexing
    BM25: directly finds chunks containing "FAISS", "flat", "L2"
    """
    if not docs:
        logger.warning("BM25 retriever created with empty document list")

    retriever = BM25Retriever.from_documents(docs)
    retriever.k = k
    return retriever


# ────────────────────────────────────────────────────
# 3. HYBRID RETRIEVER (BM25 + MMR)
# ────────────────────────────────────────────────────

def get_hybrid_retriever(docs: List[Document] = None) -> EnsembleRetriever:
    """
    Combines dense (MMR) + sparse (BM25) retrieval.
    
    weights=[0.6, 0.4] means:
    - 60% weight to semantic similarity (MMR)
    - 40% weight to keyword matching (BM25)
    
    Why 0.6/0.4 and not 0.5/0.5?
    Academic/research queries tend to be conceptual
    so semantic search should lead, but keywords matter too.
    This ratio is tunable — mention this in your interview.
    
    Args:
        docs: all documents in the knowledge base (needed for BM25)
              if None, fetched automatically from ChromaDB
    """
    vectorstore = get_vectorstore()

    # fetch all docs from ChromaDB for BM25 if not provided
    if docs is None:
        docs = _fetch_all_docs(vectorstore)

    if not docs:
        logger.warning("No documents in knowledge base — retriever will return empty results")

    dense_retriever  = get_dense_retriever(vectorstore)
    sparse_retriever = get_sparse_retriever(docs)

    hybrid = EnsembleRetriever(
        retrievers=[dense_retriever, sparse_retriever],
        weights=[DENSE_WEIGHT, SPARSE_WEIGHT]
    )

    logger.info(
        f"Hybrid retriever ready — "
        f"MMR({DENSE_WEIGHT}) + BM25({SPARSE_WEIGHT}) "
        f"over {len(docs)} chunks"
    )
    return hybrid


# ────────────────────────────────────────────────────
# 4. RETRIEVAL WITH SCORES + METADATA
# ────────────────────────────────────────────────────

def retrieve_with_metadata(query: str, k: int = RETRIEVER_K) -> List[dict]:
    """
    Retrieves chunks and returns them as clean dicts.
    Member 3's API endpoint returns this directly as JSON.
    Member 4's citation panel renders this in the UI.
    
    Returns:
    [
        {
            "content": "chunk text...",
            "display_source": "Paper Title  •  arXiv  •  2020",
            "source_type": "arxiv",
            "title": "Paper Title",
            "chunk_index": 0,
            "word_count": 143,
            "session_id": "abc123"
        },
        ...
    ]
    """
    retriever = get_hybrid_retriever()
    docs = retriever.invoke(query)

    results = []
    for doc in docs[:k]:
        results.append({
            "content": doc.page_content,
            "display_source": doc.metadata.get("display_source", "Unknown"),
            "source_type":    doc.metadata.get("source_type", "unknown"),
            "title":          doc.metadata.get("title", ""),
            "chunk_index":    doc.metadata.get("chunk_index", 0),
            "word_count":     doc.metadata.get("word_count", 0),
            "session_id":     doc.metadata.get("session_id", ""),
            "ingested_at":    doc.metadata.get("ingested_at", ""),
        })

    logger.info(f"Retrieved {len(results)} chunks for: '{query[:60]}'")
    return results


# ────────────────────────────────────────────────────
# 5. HELPER
# ────────────────────────────────────────────────────

def _fetch_all_docs(vectorstore: Chroma) -> List[Document]:
    """
    Pull all stored chunks from ChromaDB for BM25 indexing.
    BM25 needs the full corpus to compute term frequencies.
    """
    try:
        count = vectorstore._collection.count()
        if count == 0:
            return []

        result = vectorstore.get(limit=count, include=["documents", "metadatas"])
        docs = []

        for content, metadata in zip(result["documents"], result["metadatas"]):
            docs.append(Document(
                page_content=content,
                metadata=metadata or {}
            ))

        logger.info(f"Fetched {len(docs)} docs from ChromaDB for BM25")
        return docs

    except Exception as e:
        logger.error(f"Failed to fetch docs for BM25: {e}")
        return []
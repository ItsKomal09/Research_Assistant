import sys
import os
import chromadb
chromadb.Settings(anonymized_telemetry=False)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rag.embeddings import get_embedding_model
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from typing import List
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# 1. GET OR CREATE VECTOR STORE
# ────────────────────────────────────────────────────

_vectorstore = None  # singleton


def get_vectorstore() -> Chroma:
    """
    Returns a singleton ChromaDB instance.
    
    - If ./data/chroma_db exists → loads existing vectors from disk
    - If not → creates a fresh empty collection
    
    Singleton because:
    - ChromaDB holds an open connection to disk
    - Creating multiple instances causes file lock conflicts
    """
    global _vectorstore

    if _vectorstore is None:
        logger.info(f"Connecting to ChromaDB at: {CHROMA_PERSIST_DIR}")

        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        _vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=get_embedding_model(),
            persist_directory=CHROMA_PERSIST_DIR,
        )

        count = _vectorstore._collection.count()
        logger.info(f"ChromaDB ready — {count} chunks in collection")

    return _vectorstore


# ────────────────────────────────────────────────────
# 2. ADD DOCUMENTS
# ────────────────────────────────────────────────────

def add_documents(docs: List[Document]) -> dict:
    """
    Add enriched chunks into ChromaDB.
    Uses chunk_id from metadata.py as the ChromaDB document ID.
    
    This means:
    - Same chunk ingested twice → silently skipped (no duplicates)
    - Every chunk is traceable back to its source
    
    Returns ingestion summary for the API response.
    """
    if not docs:
        logger.warning("add_documents called with empty list")
        return {"added": 0, "message": "No documents to add"}

    vs = get_vectorstore()

    # extract IDs from metadata (set in metadata.py)
    ids = [doc.metadata.get("chunk_id", str(i)) for i, doc in enumerate(docs)]

    # check existing IDs to skip duplicates
    existing = _get_existing_ids(vs)
    new_docs = [doc for doc, id_ in zip(docs, ids) if id_ not in existing]
    new_ids  = [id_ for id_ in ids if id_ not in existing]

    skipped = len(docs) - len(new_docs)

    if not new_docs:
        logger.info("All chunks already exist in ChromaDB — skipping")
        return {"added": 0, "skipped": skipped, "message": "All chunks already ingested"}

    logger.info(f"Adding {len(new_docs)} new chunks to ChromaDB...")
    vs.add_documents(documents=new_docs, ids=new_ids)

    total = vs._collection.count()
    logger.info(f"Done — collection now has {total} total chunks")

    return {
        "added": len(new_docs),
        "skipped": skipped,
        "total_in_store": total,
        "message": f"Successfully added {len(new_docs)} chunks"
    }


# ────────────────────────────────────────────────────
# 3. SEARCH (used in retriever + agent tools)
# ────────────────────────────────────────────────────

def similarity_search(query: str, k: int = 6) -> List[Document]:
    """
    Basic semantic search — returns top k most similar chunks.
    Used by Member 2's agent search tool directly.
    """
    vs = get_vectorstore()
    results = vs.similarity_search(query, k=k)
    logger.info(f"Similarity search: '{query[:50]}' → {len(results)} results")
    return results


def similarity_search_with_scores(query: str, k: int = 6) -> List[tuple]:
    """
    Same as above but returns (Document, score) tuples.
    Score is cosine distance — lower = more similar.
    Member 4 uses scores to show relevance percentage in citations.
    """
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(query, k=k)
    logger.info(f"Scored search: '{query[:50]}' → {len(results)} results")
    return results


# ────────────────────────────────────────────────────
# 4. COLLECTION MANAGEMENT
# ────────────────────────────────────────────────────

def get_collection_stats() -> dict:
    """
    Returns current state of the ChromaDB collection.
    Member 4's dashboard shows these stats.
    """
    vs = get_vectorstore()
    count = vs._collection.count()

    # sample a few docs to show source breakdown
    if count > 0:
        # sample = vs.get(limit=min(count, 500))
        sample = vs.get(limit=count)
        metadatas = sample.get("metadatas", [])

        source_counts = {}
        for meta in metadatas:
            st = meta.get("source_type", "unknown")
            source_counts[st] = source_counts.get(st, 0) + 1
    else:
        source_counts = {}

    return {
        "total_chunks": count,
        "source_breakdown": source_counts,
        "collection_name": CHROMA_COLLECTION_NAME,
        "persist_dir": CHROMA_PERSIST_DIR,
    }


def delete_collection() -> dict:
    """
    Wipe the entire collection — useful during development.
    Call this if you want a fresh start.
    """
    global _vectorstore
    vs = get_vectorstore()
    vs.delete_collection()
    _vectorstore = None
    logger.warning("ChromaDB collection deleted")
    return {"message": "Collection deleted successfully"}


def delete_by_session(session_id: str) -> dict:
    """
    Delete all chunks from a specific ingestion session.
    Member 4 uses this for the 'remove this document' button.
    """
    vs = get_vectorstore()

    results = vs.get(where={"session_id": session_id})
    ids_to_delete = results.get("ids", [])

    if not ids_to_delete:
        return {"deleted": 0, "message": f"No chunks found for session {session_id}"}

    vs.delete(ids=ids_to_delete)
    logger.info(f"Deleted {len(ids_to_delete)} chunks for session {session_id}")

    return {
        "deleted": len(ids_to_delete),
        "message": f"Removed session {session_id} from knowledge base"
    }


# ────────────────────────────────────────────────────
# 5. HELPER
# ────────────────────────────────────────────────────

def _get_existing_ids(vs: Chroma) -> set:
    """Fetch all existing document IDs from ChromaDB."""
    try:
        result = vs.get()
        return set(result.get("ids", []))
    except Exception:
        return set()
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.tools import tool
from langchain_core.documents import Document
from typing import List, Tuple
import logging

from rag.retriever import get_hybrid_retriever
from ingestion.loaders import load_arxiv, load_wikipedia
from ingestion.splitters import process_documents
from ingestion.metadata import enrich_metadata
from rag.vectorstore import add_documents
from config import RETRIEVER_K

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# SHARED HELPER — turn LangChain Documents into the same
# citation-ready dict shape Member 4's UI already expects
# (matches rag/retriever.py's retrieve_with_metadata output)
# ────────────────────────────────────────────────────

def _docs_to_sources(docs: List[Document]) -> List[dict]:
    sources = []
    for doc in docs:
        sources.append({
            "content": doc.page_content[:500],
            "display_source": doc.metadata.get(
                "display_source", doc.metadata.get("source", "Unknown Source")
            ),
            "source_type": doc.metadata.get("source_type", "unknown"),
            "title": doc.metadata.get("title", ""),
        })
    return sources


def _persist_to_kb(docs: List[Document], session_id: str) -> None:
    """
    Live-fetched docs (arXiv/Wikipedia) get chunked, enriched, and saved
    into ChromaDB — reusing Member 1's exact ingestion pipeline — so the
    next question on the same topic hits the knowledge base directly
    instead of re-fetching from the internet.
    """
    try:
        chunks = process_documents(docs)
        enriched = enrich_metadata(chunks, session_id=session_id)
        add_documents(enriched)
    except Exception as e:
        # persistence is a nice-to-have, never let it break the tool call
        logger.warning(f"Could not persist fetched docs to knowledge base: {e}")


# ────────────────────────────────────────────────────
# TOOL 1 — SEARCH KNOWLEDGE BASE
# ────────────────────────────────────────────────────

@tool(response_format="content_and_artifact")
def search_knowledge_base(query: str) -> Tuple[str, List[dict]]:
    """
    Search the user's own knowledge base — PDFs, URLs, and any arXiv or
    Wikipedia content already ingested — using hybrid retrieval
    (BM25 + vector similarity + MMR). Always try this before fetching
    anything live from the internet.
    """
    try:
        retriever = get_hybrid_retriever()
        docs = retriever.invoke(query)[:RETRIEVER_K]
    except Exception as e:
        logger.error(f"search_knowledge_base failed: {e}")
        return f"Knowledge base search failed: {e}", []

    if not docs:
        return "No relevant documents found in the knowledge base.", []

    content = "\n\n".join(
        f"[{i + 1}] {d.metadata.get('display_source', 'Unknown Source')}\n{d.page_content}"
        for i, d in enumerate(docs)
    )
    return content, _docs_to_sources(docs)


# ────────────────────────────────────────────────────
# TOOL 2 — FETCH LIVE ARXIV PAPERS
# ────────────────────────────────────────────────────

@tool(response_format="content_and_artifact")
def fetch_arxiv_papers(query: str, max_results: int = 3) -> Tuple[str, List[dict]]:
    """
    Fetch live research papers from arXiv when the knowledge base doesn't
    have enough information. Best for specific, technical, or recent
    academic questions. Results are also saved into the knowledge base
    for future questions on the same topic.
    """
    docs = load_arxiv(query, max_results=max_results)
    if not docs:
        return f"No arXiv papers found for '{query}'.", []

    _persist_to_kb(docs, session_id="agent-arxiv-fetch")

    content = "\n\n".join(
        f"[{i + 1}] {d.metadata.get('title', 'Unknown')} "
        f"({str(d.metadata.get('published', ''))[:4]})\n{d.page_content[:600]}"
        for i, d in enumerate(docs)
    )
    return content, _docs_to_sources(docs)


# ────────────────────────────────────────────────────
# TOOL 3 — FETCH WIKIPEDIA BACKGROUND
# ────────────────────────────────────────────────────

@tool(response_format="content_and_artifact")
def fetch_wikipedia_article(query: str) -> Tuple[str, List[dict]]:
    """
    Fetch general background or conceptual context from Wikipedia. Best
    when the question needs grounding in a well-known concept rather than
    a specific research paper. Results are also saved into the knowledge
    base for future questions on the same topic.
    """
    docs = load_wikipedia(query)
    if not docs:
        return f"No Wikipedia article found for '{query}'.", []

    _persist_to_kb(docs, session_id="agent-wikipedia-fetch")

    content = "\n\n".join(
        f"[{i + 1}] {d.metadata.get('title', query)}\n{d.page_content[:800]}"
        for i, d in enumerate(docs)
    )
    return content, _docs_to_sources(docs)


# ────────────────────────────────────────────────────
# TOOL 4 — FLAG A KNOWLEDGE GAP
# ────────────────────────────────────────────────────

@tool
def flag_knowledge_gap(topic: str, reason: str) -> str:
    """
    Call this when, even after searching the knowledge base and trying a
    live fetch, you still can't find enough information to answer
    confidently. This tells the user explicitly what's missing instead of
    guessing or hallucinating an answer.
    """
    logger.info(f"Knowledge gap flagged — topic='{topic}' reason='{reason}'")
    return f"Knowledge gap flagged for '{topic}': {reason}"


AGENT_TOOLS = [
    search_knowledge_base,
    fetch_arxiv_papers,
    fetch_wikipedia_article,
    flag_knowledge_gap,
]

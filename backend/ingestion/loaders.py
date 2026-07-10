import sys
import os

# Wikipedia now requires a User-Agent header on all API requests (returns
# 403 without one, as of a recent policy change). Patching Session.request
# directly (rather than requests.get) guarantees this applies no matter
# which module or import order pulls in the wikipedia package internally.
import requests
_original_request = requests.Session.request
def _request_with_user_agent(self, method, url, **kwargs):
    headers = kwargs.get("headers") or {}
    headers.setdefault("User-Agent", "ResearchMind/1.0 (student project)")
    kwargs["headers"] = headers
    return _original_request(self, method, url, **kwargs)
requests.Session.request = _request_with_user_agent

os.environ.setdefault("USER_AGENT", "researchmind-bot/1.0")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_community.document_loaders import WikipediaLoader
from langchain_community.document_loaders import ArxivLoader
from langchain_core.documents import Document
from config import ARXIV_MAX_RESULTS
from typing import List
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────
# 1. PDF LOADER
# ────────────────────────────────────────────────────

def load_pdf(file_path: str) -> List[Document]:
    """
    Load a PDF from disk path.
    Each page becomes one Document with metadata.
    """
    try:
        logger.info(f"Loading PDF: {file_path}")
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        # tag every page with source type
        for i, doc in enumerate(docs):
            doc.metadata.update({
                "source_type": "pdf",
                "file_name": os.path.basename(file_path),
                "page_number": doc.metadata.get("page", i),
            })

        logger.info(f"PDF loaded: {len(docs)} pages from {os.path.basename(file_path)}")
        return docs

    except Exception as e:
        logger.error(f"Failed to load PDF {file_path}: {e}")
        return []


def load_pdf_from_bytes(file_bytes: bytes, filename: str) -> List[Document]:
    """
    Load a PDF from raw bytes (used by FastAPI file upload endpoint).
    Writes to a temp file, loads, then cleans up.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        docs = load_pdf(tmp_path)

        # replace temp path with real filename in metadata
        for doc in docs:
            doc.metadata["file_name"] = filename
            doc.metadata["source"] = filename

        return docs

    except Exception as e:
        logger.error(f"Failed to load PDF from bytes: {e}")
        return []

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ────────────────────────────────────────────────────
# 2. URL LOADER
# ────────────────────────────────────────────────────

def load_url(url: str) -> List[Document]:
    """
    Scrape and load content from any public URL.
    Blogs, documentation, news articles — anything web-accessible.
    """
    try:
        logger.info(f"Loading URL: {url}")
        loader = WebBaseLoader(url)
        docs = loader.load()

        for doc in docs:
            doc.metadata.update({
                "source_type": "url",
                "url": url,
                "source": url,
            })

        logger.info(f"URL loaded: {len(docs)} document(s) from {url}")
        return docs

    except Exception as e:
        logger.error(f"Failed to load URL {url}: {e}")
        return []


def load_multiple_urls(urls: List[str]) -> List[Document]:
    """Load multiple URLs and combine into one list."""
    all_docs = []
    for url in urls:
        docs = load_url(url)
        all_docs.extend(docs)
    logger.info(f"Total URL docs loaded: {len(all_docs)}")
    return all_docs


# ────────────────────────────────────────────────────
# 3. ARXIV LOADER
# ────────────────────────────────────────────────────

def load_arxiv(query: str, max_results: int = ARXIV_MAX_RESULTS) -> List[Document]:
    """
    Fetch papers from arXiv by search query.
    Returns abstracts + metadata (title, authors, published date).
    No API key needed — arXiv is public.
    
    Example query: "retrieval augmented generation 2024"
    """
    try:
        logger.info(f"Fetching arXiv papers for: '{query}'")
        loader = ArxivLoader(
            query=query,
            load_max_docs=max_results,
            load_all_available_meta=True
        )
        docs = loader.load()

        for doc in docs:
            doc.metadata.update({
                "source_type": "arxiv",
                "query": query,
                "title": doc.metadata.get("Title", "Unknown"),
                "authors": doc.metadata.get("Authors", "Unknown"),
                "published": doc.metadata.get("Published", "Unknown"),
                "source": f"arXiv: {doc.metadata.get('Title', query)}",
            })

        logger.info(f"arXiv loaded: {len(docs)} papers for '{query}'")
        return docs

    except Exception as e:
        logger.error(f"Failed to load arXiv for query '{query}': {e}")
        return []


# ────────────────────────────────────────────────────
# 4. WIKIPEDIA LOADER
# ────────────────────────────────────────────────────

def load_wikipedia(query: str, lang: str = "en") -> List[Document]:
    """
    Load Wikipedia article(s) for a topic.
    Useful when the agent needs background context on a concept.
    
    Example query: "Transformer neural network architecture"
    """
    try:
        logger.info(f"Loading Wikipedia: '{query}'")
        loader = WikipediaLoader(
            query=query,
            lang=lang,
            load_max_docs=2,            # top 2 matching articles
            doc_content_chars_max=8000  # cap to avoid huge dumps
        )
        docs = loader.load()

        for doc in docs:
            doc.metadata.update({
                "source_type": "wikipedia",
                "query": query,
                "source": f"Wikipedia: {doc.metadata.get('title', query)}",
            })

        logger.info(f"Wikipedia loaded: {len(docs)} article(s) for '{query}'")
        return docs

    except Exception as e:
        logger.error(f"Failed to load Wikipedia for '{query}': {e}")
        return []


# ────────────────────────────────────────────────────
# 5. UNIFIED LOADER (Member 2 uses this in agent tools)
# ────────────────────────────────────────────────────

def load_documents(source_type: str, source: str, **kwargs) -> List[Document]:
    """
    Single entry point for all loaders.
    Member 2's agent calls this instead of individual functions.

    Args:
        source_type : "pdf" | "url" | "arxiv" | "wikipedia"
        source      : file path, URL, or search query
        **kwargs    : extra args (e.g. max_results for arxiv)

    Returns:
        List of Document objects, all with consistent metadata
    """
    loaders = {
        "pdf":       lambda: load_pdf(source),
        "url":       lambda: load_url(source),
        "arxiv":     lambda: load_arxiv(source, **kwargs),
        "wikipedia": lambda: load_wikipedia(source, **kwargs),
    }

    if source_type not in loaders:
        logger.error(f"Unknown source type: {source_type}")
        return []

    return loaders[source_type]()
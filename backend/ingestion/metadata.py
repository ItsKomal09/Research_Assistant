import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from typing import List
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# 1. CORE METADATA ENRICHER
# ────────────────────────────────────────────────────

def enrich_metadata(docs: List[Document], session_id: str = "default") -> List[Document]:
    """
    Main function — call this on every chunk before storing in ChromaDB.
    
    Adds:
    - chunk_id       : unique hash for deduplication
    - session_id     : which upload session this came from
    - ingested_at    : timestamp for "researched last week" memory
    - display_source : clean human-readable label for frontend citations
    - word_count     : rough quality signal
    """
    for doc in docs:
        source_type = doc.metadata.get("source_type", "unknown")

        # unique ID for this chunk (content hash — same chunk never duplicates)
        doc.metadata["chunk_id"] = _generate_chunk_id(doc.page_content)

        # session tracking (Member 4 uses this for memory panel)
        doc.metadata["session_id"] = session_id
        doc.metadata["ingested_at"] = datetime.now().isoformat()

        # clean label shown in UI citation cards
        doc.metadata["display_source"] = _build_display_source(doc.metadata, source_type)

        # word count (rough quality signal, shown in source panel)
        doc.metadata["word_count"] = len(doc.page_content.split())

        # normalize missing fields so ChromaDB never gets None values
        doc.metadata = _normalize_metadata(doc.metadata)

    logger.info(f"Metadata enriched for {len(docs)} chunks")
    return docs


# ────────────────────────────────────────────────────
# 2. DISPLAY SOURCE BUILDER
# ────────────────────────────────────────────────────

def _build_display_source(metadata: dict, source_type: str) -> str:
    """
    Builds the human-readable citation label shown in the frontend.
    
    PDF     → "paper.pdf  •  Page 4"
    arXiv   → "Attention Is All You Need  •  arXiv  •  2017"
    URL     → "https://example.com/article"
    Wiki    → "Wikipedia: Transformer (ML)"
    """
    if source_type == "pdf":
        filename = metadata.get("file_name", "document.pdf")
        page = metadata.get("page_number", "")
        return f"{filename}  •  Page {page}" if page != "" else filename

    elif source_type == "arxiv":
        title = metadata.get("title", "arXiv Paper")
        published = metadata.get("published", "")
        year = published[:4] if published else ""
        return f"{title}  •  arXiv  •  {year}" if year else f"{title}  •  arXiv"

    elif source_type == "url":
        return metadata.get("url", metadata.get("source", "Web Source"))

    elif source_type == "wikipedia":
        title = metadata.get("title", metadata.get("query", "Wikipedia"))
        return f"Wikipedia: {title}"

    return metadata.get("source", "Unknown Source")


# ────────────────────────────────────────────────────
# 3. CHUNK ID GENERATOR
# ────────────────────────────────────────────────────

def _generate_chunk_id(content: str) -> str:
    """
    MD5 hash of first 500 chars of content.
    Same chunk ingested twice → same ID → ChromaDB skips duplicate.
    """
    return hashlib.md5(content[:500].encode()).hexdigest()


# ────────────────────────────────────────────────────
# 4. METADATA NORMALIZER
# ────────────────────────────────────────────────────

def _normalize_metadata(metadata: dict) -> dict:
    """
    ChromaDB crashes if any metadata value is None or a list.
    This converts everything to safe types (str, int, float, bool).
    
    Common crash source: authors field from arXiv comes as a list.
    """
    clean = {}
    for key, value in metadata.items():
        if value is None:
            clean[key] = ""
        elif isinstance(value, list):
            # arXiv authors = ["Author A", "Author B"] → "Author A, Author B"
            clean[key] = ", ".join(str(v) for v in value)
        elif isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


# ────────────────────────────────────────────────────
# 5. SESSION SUMMARY (Member 4 uses this for memory panel)
# ────────────────────────────────────────────────────

def get_session_summary(docs: List[Document]) -> dict:
    """
    Returns a summary of what was ingested in a session.
    Member 4's frontend shows this in the memory panel.
    
    Example return:
    {
        "total_chunks": 42,
        "sources": {
            "pdf": 2,
            "arxiv": 3,
            "wikipedia": 1,
            "url": 0
        },
        "ingested_at": "2024-01-15T10:30:00",
        "titles": ["Attention Is All You Need", "RAG paper..."]
    }
    """
    source_counts = {"pdf": 0, "arxiv": 0, "wikipedia": 0, "url": 0}
    titles = []

    for doc in docs:
        source_type = doc.metadata.get("source_type", "unknown")
        if source_type in source_counts:
            source_counts[source_type] += 1

        title = doc.metadata.get("title") or doc.metadata.get("file_name", "")
        if title and title not in titles:
            titles.append(title)

    return {
        "total_chunks": len(docs),
        "sources": source_counts,
        "ingested_at": datetime.now().isoformat(),
        "titles": titles[:10]      # cap at 10 for UI
    }
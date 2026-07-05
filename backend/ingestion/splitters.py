import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import CHUNK_SIZE, CHUNK_OVERLAP
from typing import List
import logging

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────
# 1. BASE SPLITTER
# ────────────────────────────────────────────────────

def get_text_splitter(
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> RecursiveCharacterTextSplitter:
    """
    RecursiveCharacterTextSplitter tries to split on:
    paragraphs → sentences → words → characters (in that order)
    
    This preserves meaning better than naive character splitting.
    chunk_size=800 is the sweet spot for BAAI/bge-base-en-v1.5
    (too large = diluted embeddings, too small = missing context)
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""]
    )


# ────────────────────────────────────────────────────
# 2. SOURCE-AWARE SPLITTING
# ────────────────────────────────────────────────────

def split_documents(docs: List[Document]) -> List[Document]:
    """
    Main function — splits any list of documents.
    Detects source type and applies the right strategy.
    
    PDF   → smaller chunks (dense academic text)
    arXiv → medium chunks (structured abstracts)
    URL   → larger chunks (web content is loosely structured)
    Wiki  → larger chunks (encyclopedic, needs more context per chunk)
    """
    if not docs:
        logger.warning("split_documents received empty list")
        return []

    chunks = []
    
    for doc in docs:
        source_type = doc.metadata.get("source_type", "unknown")
        doc_chunks = _split_by_source_type(doc, source_type)
        chunks.extend(doc_chunks)

    logger.info(f"Splitting complete: {len(docs)} docs → {len(chunks)} chunks")
    return chunks


def _split_by_source_type(doc: Document, source_type: str) -> List[Document]:
    """
    Different sources need different chunk sizes.
    Academic PDFs are dense → smaller chunks for precision.
    Web/Wiki content is loose → larger chunks for context.
    """
    size_map = {
        "pdf":       {"chunk_size": 700,  "chunk_overlap": 100},
        "arxiv":     {"chunk_size": 800,  "chunk_overlap": 150},
        "url":       {"chunk_size": 1000, "chunk_overlap": 200},
        "wikipedia": {"chunk_size": 1000, "chunk_overlap": 200},
        "unknown":   {"chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP},
    }

    params = size_map.get(source_type, size_map["unknown"])
    splitter = get_text_splitter(**params)
    chunks = splitter.split_documents([doc])

    # tag each chunk with its position (useful for citations)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["total_chunks"] = len(chunks)

    return chunks


# ────────────────────────────────────────────────────
# 3. CHUNK QUALITY FILTER
# ────────────────────────────────────────────────────

def filter_chunks(chunks: List[Document]) -> List[Document]:
    """
    Remove garbage chunks before they pollute your vector store.
    
    Filters out:
    - Chunks shorter than 50 chars (headers, page numbers, stray text)
    - Chunks that are mostly whitespace
    - Duplicate chunks (same content from multiple ingestion runs)
    """
    seen = set()
    clean = []

    for chunk in chunks:
        content = chunk.page_content.strip()

        # too short
        if len(content) < 50:
            continue

        # mostly whitespace
        if len(content.replace(" ", "").replace("\n", "")) < 30:
            continue

        # duplicate
        content_hash = hash(content[:200])
        if content_hash in seen:
            continue

        seen.add(content_hash)
        chunk.page_content = content  # store stripped version
        clean.append(chunk)

    removed = len(chunks) - len(clean)
    if removed > 0:
        logger.info(f"Filtered out {removed} low-quality chunks")

    return clean


# ────────────────────────────────────────────────────
# 4. FULL PIPELINE (split + filter together)
# ────────────────────────────────────────────────────

def process_documents(docs: List[Document]) -> List[Document]:
    """
    The function every other module actually calls.
    
    Flow: raw docs → split → filter → clean chunks
    Member 3's ingestion endpoint calls this directly.
    """
    logger.info(f"Processing {len(docs)} documents...")

    chunks = split_documents(docs)
    clean_chunks = filter_chunks(chunks)

    logger.info(
        f"Pipeline complete: {len(docs)} docs "
        f"→ {len(chunks)} chunks "
        f"→ {len(clean_chunks)} after filtering"
    )

    return clean_chunks
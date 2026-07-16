from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import uuid

from ingestion.loaders import load_pdf_from_bytes, load_url, load_arxiv, load_wikipedia
# get_collection_stats() and delete_by_session() already existed in rag/vectorstore.py
from ingestion.splitters import process_documents
from ingestion.metadata import enrich_metadata
from rag.vectorstore import add_documents, get_collection_stats, delete_by_session

router = APIRouter()


class UrlIngestRequest(BaseModel):
    url: str
    session_id: str | None = None


class ArxivIngestRequest(BaseModel):
    query: str
    max_results: int = 5
    session_id: str | None = None


class WikipediaIngestRequest(BaseModel):
    query: str
    session_id: str | None = None


def _pipeline(raw_docs, session_id: str):
    """Shared logic: split → enrich → store. Used by every ingest endpoint."""
    if not raw_docs:
        raise HTTPException(status_code=400, detail="No content could be loaded from source")
    chunks = process_documents(raw_docs)
    enriched = enrich_metadata(chunks, session_id=session_id)
    result = add_documents(enriched)
    return result


def _with_document_metadata(result: dict, session_id: str, file_name: str) -> dict:
    """
    Attaches file_name + chunk_count on top of whatever add_documents()
    returned, so the frontend's document manager (Knowledge Base page) and
    chat doc-pills have something stable to display and reference for
    deletion, regardless of source type.
    """
    return {
        "session_id": session_id,
        "file_name": file_name,
        "chunk_count": result.get("added", 0),
        **result,
    }


@router.post("/pdf")
async def ingest_pdf(file: UploadFile = File(...), session_id: str = None):
    session_id = session_id or str(uuid.uuid4())
    file_bytes = await file.read()
    raw_docs = load_pdf_from_bytes(file_bytes, file.filename)
    result = _pipeline(raw_docs, session_id)
    return _with_document_metadata(result, session_id, file.filename)


@router.post("/url")
async def ingest_url(request: UrlIngestRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_docs = load_url(request.url)
    result = _pipeline(raw_docs, session_id)
    return _with_document_metadata(result, session_id, request.url)


@router.post("/arxiv")
async def ingest_arxiv(request: ArxivIngestRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_docs = load_arxiv(request.query, max_results=request.max_results)
    result = _pipeline(raw_docs, session_id)
    return _with_document_metadata(result, session_id, f"arXiv: {request.query}")


@router.post("/wikipedia")
async def ingest_wikipedia(request: WikipediaIngestRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_docs = load_wikipedia(request.query)
    result = _pipeline(raw_docs, session_id)
    return _with_document_metadata(result, session_id, f"Wikipedia: {request.query}")


@router.get("/stats")
async def ingest_stats():
    """Collection-level stats for Member 4's dashboard."""
    return get_collection_stats()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Remove all chunks belonging to one ingestion session."""
    return delete_by_session(session_id)
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import uuid

from ingestion.loaders import load_pdf_from_bytes, load_url, load_arxiv, load_wikipedia
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


@router.post("/pdf")
async def ingest_pdf(file: UploadFile = File(...), session_id: str = None):
    session_id = session_id or str(uuid.uuid4())
    file_bytes = await file.read()
    raw_docs = load_pdf_from_bytes(file_bytes, file.filename)
    result = _pipeline(raw_docs, session_id)
    return {"session_id": session_id, **result}


@router.post("/url")
async def ingest_url(request: UrlIngestRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_docs = load_url(request.url)
    result = _pipeline(raw_docs, session_id)
    return {"session_id": session_id, **result}


@router.post("/arxiv")
async def ingest_arxiv(request: ArxivIngestRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_docs = load_arxiv(request.query, max_results=request.max_results)
    result = _pipeline(raw_docs, session_id)
    return {"session_id": session_id, **result}
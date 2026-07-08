from fastapi import APIRouter
from pydantic import BaseModel
import uuid

from rag.chains import query_with_citations, query_with_history
from session.manager import create_session, get_history, add_message, session_exists

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


@router.post("/query")
async def query(request: QueryRequest):
    """Single-shot query, no conversation memory."""
    result = query_with_citations(request.question)
    return result


@router.post("/conversation")
async def conversation(request: QueryRequest):
    """Multi-turn query — uses session history for context."""
    session_id = request.session_id or create_session()

    if not session_exists(session_id):
        session_id = create_session()

    history = get_history(session_id)
    result = query_with_history(request.question, chat_history=history)

    add_message(session_id, "user", request.question)
    add_message(session_id, "assistant", result["answer"])

    return {"session_id": session_id, **result}


@router.get("/history/{session_id}")
async def history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}
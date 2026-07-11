from fastapi import APIRouter
from pydantic import BaseModel
import uuid

from rag.chains import query_with_citations, query_with_history
from agent.service import run_agent
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


@router.post("/agent")
async def agent_query(request: QueryRequest):
    """
    Agentic query — a LangGraph ReAct agent decides at runtime whether to
    search the knowledge base, fetch a live arXiv paper, fetch Wikipedia
    background, or flag a knowledge gap. Returns the answer plus a visible
    step-by-step reasoning trace (Member 4's Agent Trace UI) and every
    source touched along the way (Member 4's citation panel).

    Conversation memory is handled two ways: LangGraph's own checkpointer
    keeps the full tool-call/message history per session_id so follow-ups
    stay in context, and we also mirror user/assistant turns into
    session.manager so GET /history/{session_id} shows agent turns too.
    """
    session_id = request.session_id or create_session()

    if not session_exists(session_id):
        session_id = create_session()

    result = run_agent(request.question, session_id=session_id)

    add_message(session_id, "user", request.question)
    add_message(session_id, "assistant", result["answer"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "reasoning_trace": result["reasoning_trace"],
        "sources": result["sources"],
        "question": result["question"],
    }


@router.get("/history/{session_id}")
async def history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.documents import Document
from rag.retriever import get_hybrid_retriever, retrieve_with_metadata
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, RETRIEVER_K
from typing import List
import logging

logger = logging.getLogger(__name__)



# 1. LLM SETUP

def get_llm() -> ChatOllama:
    """
    Returns Ollama LLM instance.
    temperature=0.1 keeps answers factual and grounded.
    Higher temperature = more creative but less reliable for research.
    """
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.1,
    )



# 2. PROMPTS


RAG_PROMPT = ChatPromptTemplate.from_template("""
You are ResearchMind, an expert AI research assistant.
Answer the question using ONLY the provided context.
If the context does not contain enough information, say:
"I don't have enough information in the knowledge base to answer this."

Rules:
- Be precise and cite sources by mentioning document titles
- Use bullet points for multi-part answers
- Never make up facts outside the provided context
- Keep answers focused and under 300 words unless detail is needed

Context:
{context}

Question: {question}

Answer:
""")


CONDENSE_PROMPT = ChatPromptTemplate.from_template("""
Given the conversation history and a follow-up question,
rephrase the follow-up as a standalone question that contains
all necessary context for retrieval.

Chat History:
{chat_history}

Follow-up Question: {question}

Standalone Question:
""")


# ────────────────────────────────────────────────────
# 3. CONTEXT FORMATTER
# ────────────────────────────────────────────────────

def format_context(docs: List[Document]) -> str:
    """
    Formats retrieved chunks into a clean context string for the LLM.
    Each chunk is labelled with its source so the LLM can cite it.
    
    Output example:
    [Source 1: RAG Paper  •  arXiv  •  2020]
    RAG combines parametric and non-parametric memory...
    
    [Source 2: paper.pdf  •  Page 4]
    The retrieval component fetches relevant passages...
    """
    if not docs:
        return "No relevant documents found in the knowledge base."

    formatted = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("display_source", "Unknown Source")
        formatted.append(
            f"[Source {i+1}: {source}]\n{doc.page_content}"
        )

    return "\n\n".join(formatted)


# ────────────────────────────────────────────────────
# 4. CORE RAG CHAIN
# ────────────────────────────────────────────────────

def build_rag_chain():
    """
    Builds the core RAG chain using LCEL (LangChain Expression Language).
    
    Flow:
    question → retriever → format context → prompt → LLM → answer
    
    RunnableParallel runs retrieval and passes question simultaneously.
    RunnablePassthrough passes the question through unchanged.
    """
    llm       = get_llm()
    retriever = get_hybrid_retriever()

    # run retrieval and question formatting in parallel
    setup = RunnableParallel({
        "context":  retriever | format_context,
        "question": RunnablePassthrough()
    })

    chain = setup | RAG_PROMPT | llm | StrOutputParser()

    logger.info("RAG chain built successfully")
    return chain


# ────────────────────────────────────────────────────
# 5. QUERY WITH CITATIONS (main function)
# ────────────────────────────────────────────────────

def query_with_citations(question: str) -> dict:
    """
    The function Member 3's API endpoint calls.
    
    Returns both the answer AND the source citations
    so Member 4 can render them in the citation panel.
    
    Returns:
    {
        "answer": "RAG improves LLM accuracy by...",
        "sources": [
            {
                "display_source": "RAG Paper  •  arXiv  •  2020",
                "content": "chunk text snippet...",
                "source_type": "arxiv",
                "title": "...",
            },
            ...
        ],
        "question": "original question"
    }
    """
    logger.info(f"Processing query: '{question[:80]}'")

    # retrieve sources first (for citations)
    sources = retrieve_with_metadata(question, k=RETRIEVER_K)

    # build and run the chain
    chain  = build_rag_chain()
    answer = chain.invoke(question)

    logger.info(f"Answer generated ({len(answer)} chars)")

    return {
        "answer":   answer,
        "sources":  sources,
        "question": question,
    }


# ────────────────────────────────────────────────────
# 6. CONVERSATIONAL RAG (with chat history)
# ────────────────────────────────────────────────────

def query_with_history(question: str, chat_history: list) -> dict:
    """
    Handles follow-up questions by condensing chat history
    into a standalone question before retrieval.
    
    Example:
    History:  "What is RAG?"  →  "RAG is retrieval augmented generation"
    Follow-up: "How does it handle hallucinations?"
    Condensed: "How does RAG handle hallucinations?"  ← better retrieval
    
    Member 3's session management calls this for multi-turn chat.
    """
    llm = get_llm()

    # step 1 — condense follow-up into standalone question
    if chat_history:
        formatted_history = _format_chat_history(chat_history)
        condense_chain    = CONDENSE_PROMPT | llm | StrOutputParser()
        standalone_question = condense_chain.invoke({
            "chat_history": formatted_history,
            "question":     question
        })
        logger.info(f"Condensed question: '{standalone_question[:80]}'")
    else:
        standalone_question = question

    # step 2 — run normal RAG with condensed question
    return query_with_citations(standalone_question)


def _format_chat_history(chat_history: list) -> str:
    """
    Converts chat history list into a readable string.
    
    Input:  [{"role": "user", "content": "..."}, ...]
    Output: "Human: ...\nAssistant: ..."
    """
    lines = []
    for msg in chat_history[-6:]:   # last 6 messages only — keeps context tight
        role    = "Human" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
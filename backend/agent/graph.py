import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama

from agent.tools import AGENT_TOOLS
from agent.prompts import AGENT_SYSTEM_PROMPT
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────
# MEMORY
# ────────────────────────────────────────────────────
# MemorySaver checkpoints the full message state per thread_id.
# We use the chat session_id as the thread_id, so the agent remembers
# earlier turns (and earlier tool results) within the same session —
# this is what gives the agent "conversation memory" on top of RAG.

_checkpointer = MemorySaver()
_graph = None  # singleton, built once and reused


# ────────────────────────────────────────────────────
# LLM — bound to tools so it can decide to call them
# ────────────────────────────────────────────────────

def get_agent_llm() -> ChatOllama:
    """
    Same Ollama/Llama 3.2 model Member 3 wired up for plain RAG, but with
    tools bound so the model can emit tool calls instead of only text.
    temperature=0.1 keeps tool-selection decisions consistent.
    """
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.1,
    )
    return llm.bind_tools(AGENT_TOOLS)


# ────────────────────────────────────────────────────
# NODES
# ────────────────────────────────────────────────────

def agent_node(state: MessagesState) -> dict:
    """
    The 'reasoning' node. Looks at the conversation so far (including any
    tool results already gathered) and decides whether to call another
    tool or produce a final answer.
    """
    messages = state["messages"]

    # inject the system prompt once, at the front, if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + list(messages)

    llm = get_agent_llm()
    response = llm.invoke(messages)
    return {"messages": [response]}


# ────────────────────────────────────────────────────
# GRAPH — the ReAct loop
# ────────────────────────────────────────────────────
#
#        ┌─────────┐   has tool_calls?   ┌───────┐
#  ─────▶│  agent  │────────────────────▶│ tools │
#        └─────────┘                      └───┬───┘
#             ▲                                │
#             └────────────────────────────────┘
#             no tool_calls → END (final answer)

def build_agent_graph():
    """
    Builds (once) and returns the compiled LangGraph ReAct agent.
    Member 3's/Member 4's callers should go through agent.service.run_agent
    rather than calling this directly.
    """
    global _graph
    if _graph is not None:
        return _graph

    workflow = StateGraph(MessagesState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(AGENT_TOOLS))

    workflow.set_entry_point("agent")

    # tools_condition inspects the last AIMessage: routes to "tools" if it
    # has tool_calls, otherwise routes to END (the model produced a final answer)
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    workflow.add_edge("tools", "agent")

    _graph = workflow.compile(checkpointer=_checkpointer)
    logger.info("LangGraph ReAct agent compiled")
    return _graph

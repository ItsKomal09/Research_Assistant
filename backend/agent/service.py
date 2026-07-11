import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from agent.graph import build_agent_graph

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 12  # recursion_limit safety net — stops runaway tool loops


def run_agent(question: str, session_id: str = "default") -> dict:
    """
    The function Member 3's/Member 4's API endpoint calls.

    Runs one turn of the LangGraph ReAct agent and returns the final
    answer along with a step-by-step reasoning trace and every source the
    agent touched — Member 4's Agent Trace UI and citation panel render
    this directly.

    Returns:
    {
        "answer": "...",
        "reasoning_trace": [
            {"step": 1, "type": "action", "thought": "...", "tool": "search_knowledge_base", "input": {...}},
            {"step": 2, "type": "observation", "tool": "search_knowledge_base", "output": "..."},
            ...
        ],
        "sources": [ {display_source, content, source_type, title}, ... ],
        "question": "...",
        "session_id": "..."
    }
    """
    graph = build_agent_graph()
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": MAX_AGENT_STEPS,
    }

    logger.info(f"Running agent for session={session_id} question='{question[:80]}'")

    result = graph.invoke({"messages": [HumanMessage(content=question)]}, config=config)
    messages = result["messages"]

    reasoning_trace, sources = _build_trace_and_sources(messages)

    final_message = messages[-1]
    raw_answer = final_message.content if isinstance(final_message, AIMessage) else str(final_message.content)
    answer = _clean_leaked_tool_call(raw_answer)

    logger.info(
        f"Agent run complete — {len(reasoning_trace)} trace steps, {len(sources)} sources"
    )

    return {
        "answer": answer,
        "reasoning_trace": reasoning_trace,
        "sources": sources,
        "question": question,
        "session_id": session_id,
    }



def _clean_leaked_tool_call(text: str) -> str:
    """
    Local Ollama models don't always emit a second/refined tool call in
    the proper structured format LangGraph expects — sometimes the model
    writes the tool call as plain JSON text inside its response instead.
    When that happens, this strips the leaked JSON rather than showing it
    to the user, and adds an honest note that a follow-up lookup was
    attempted but didn't complete cleanly.
    """
    if not isinstance(text, str):
        return text

    leaked_pattern = re.search(r'\{\s*"name"\s*:\s*".+?"\s*,\s*"parameters"\s*:.*?\}', text, re.DOTALL)
    if leaked_pattern:
        cleaned = text[:leaked_pattern.start()].strip()
        note = "\n\n*(The agent attempted a follow-up lookup that didn't complete cleanly — the answer above reflects what it had gathered so far.)*"
        return (cleaned + note) if cleaned else "I wasn't able to complete this lookup cleanly. Please try rephrasing the question."

    return text


def _build_trace_and_sources(messages: list) -> tuple:
    """
    Walks the full message list from one graph run and turns it into a
    human-readable reasoning trace (Thought → Action → Observation) plus
    a deduplicated list of every source the agent actually touched.

    Only looks at messages generated in THIS run's tail — the checkpointer
    replays prior turns too, but we only want the new turn's trace, so the
    caller should slice appropriately if replaying full history matters.
    Here we keep it simple and show the whole trace for the current state,
    which is what a "show your reasoning" panel wants anyway.
    """
    reasoning_trace = []
    raw_sources = []
    step = 1

    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            thought = msg.content.strip() if isinstance(msg.content, str) and msg.content.strip() else None
            for call in msg.tool_calls:
                reasoning_trace.append({
                    "step": step,
                    "type": "action",
                    "thought": thought,
                    "tool": call["name"],
                    "input": call.get("args", {}),
                })
                step += 1

        elif isinstance(msg, ToolMessage):
            output = msg.content if isinstance(msg.content, str) else str(msg.content)
            reasoning_trace.append({
                "step": step,
                "type": "observation",
                "tool": msg.name,
                "output": output[:1000],
            })
            step += 1

            artifact = getattr(msg, "artifact", None)
            if isinstance(artifact, list):
                raw_sources.extend(artifact)

        elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None) and msg.content:
            reasoning_trace.append({
                "step": step,
                "type": "final_answer",
                "output": msg.content if isinstance(msg.content, str) else str(msg.content),
            })
            step += 1

    sources = _dedupe_sources(raw_sources)
    return reasoning_trace, sources


def _dedupe_sources(sources: list) -> list:
    seen = set()
    deduped = []
    for s in sources:
        key = s.get("display_source")
        if key and key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped

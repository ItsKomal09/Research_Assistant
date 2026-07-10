"""
RAGAS evaluation for ResearchMind — Member 4's responsibility.

Runs each question through the existing RAG chain (rag/chains.py, built by
Member 1) and scores the resulting (question, answer, contexts) triples with
RAGAS's `faithfulness` and `answer_relevancy` metrics.

Kept deliberately separate from rag/chains.py — evaluation is a consumer of
the RAG pipeline, not part of it.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone
from typing import List, Dict

from ragas.run_config import RunConfig

from rag.chains import query_with_citations

logger = logging.getLogger(__name__)

# In-memory cache of the most recent run, so the dashboard can show
# something on load without forcing a re-run every time.
_latest_result: dict | None = None


def _build_ragas_llm_and_embeddings():
    """
    RAGAS needs an LLM + embeddings to judge faithfulness/relevancy.
    We reuse the same Ollama model and embedding model the rest of the
    app already runs, so evaluation doesn't require a separate API key.
    """
    from langchain_ollama import ChatOllama
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    from rag.embeddings import get_embedding_model

    llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0)
    return (
        LangchainLLMWrapper(llm),
        LangchainEmbeddingsWrapper(get_embedding_model()),
    )


def run_evaluation(questions: List[str]) -> Dict:
    """
    For each question:
      1. Run it through query_with_citations() to get an answer + sources
      2. Score (question, answer, retrieved contexts) with RAGAS

    Returns:
    {
        "results": [{"question", "answer", "faithfulness", "answer_relevancy"}, ...],
        "averages": {"faithfulness": float, "answer_relevancy": float},
        "generated_at": iso timestamp
    }
    """
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy

    if not questions:
        raise ValueError("No questions provided for evaluation")

    rows = []
    for q in questions:
        logger.info(f"[eval] running query: {q[:80]}")
        result = query_with_citations(q)
        contexts = [s.get("content", "") for s in result.get("sources", [])] or [""]
        rows.append({
            "question": q,
            "answer": result["answer"],
            "contexts": contexts,
        })

    dataset = Dataset.from_list(rows)
    ragas_llm, ragas_embeddings = _build_ragas_llm_and_embeddings()

    scored = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=ragas_llm,
    embeddings=ragas_embeddings,
    run_config=RunConfig(timeout=900, max_workers=1),
)
    scored_df = scored.to_pandas()

    results = []
    for i, row in enumerate(rows):
        # Pull question/answer from our own generated rows (not from RAGAS's
        # output table) — different ragas versions name these columns
        # differently internally, but we already know these values ourselves.
        score_row = scored_df.iloc[i] if i < len(scored_df) else {}
        results.append({
            "question": row["question"],
            "answer": row["answer"],
            "faithfulness": _safe_float(score_row.get("faithfulness")) if hasattr(score_row, "get") else None,
            "answer_relevancy": _safe_float(score_row.get("answer_relevancy")) if hasattr(score_row, "get") else None,
        })

    averages = {
        "faithfulness": _safe_mean([r["faithfulness"] for r in results]),
        "answer_relevancy": _safe_mean([r["answer_relevancy"] for r in results]),
    }

    global _latest_result
    _latest_result = {
        "results": results,
        "averages": averages,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return _latest_result


def get_latest_evaluation() -> Dict:
    return _latest_result or {"results": [], "averages": {}, "generated_at": None}


def _safe_float(v):
    try:
        f = float(v)
        return f if f == f else None  # filter NaN
    except (TypeError, ValueError):
        return None


def _safe_mean(values):
    clean = [v for v in values if isinstance(v, (int, float))]
    return round(sum(clean) / len(clean), 3) if clean else None

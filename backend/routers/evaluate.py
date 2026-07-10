from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from evaluation.ragas_eval import run_evaluation, get_latest_evaluation

router = APIRouter()


class EvaluationRequest(BaseModel):
    questions: List[str]


@router.post("/run")
async def evaluate_run(request: EvaluationRequest):
    """
    Runs RAGAS evaluation over the given questions using the live RAG chain.
    This calls the local LLM once per question (for the answer) plus a few
    more times per metric (for judging), so keep question lists short —
    5-10 is plenty for a demo/dashboard run.
    """
    try:
        return run_evaluation(request.questions)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/latest")
async def evaluate_latest():
    """Returns the most recent evaluation run (empty if none yet this session)."""
    return get_latest_evaluation()

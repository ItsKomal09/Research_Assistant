# ResearchMind - Backend

FastAPI backend for the ResearchMind agentic research assistant.

## Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Endpoints (Day 1)
- GET /health — health check
- POST /chat — dummy chat response (LLM integration pending)
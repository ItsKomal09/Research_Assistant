# ResearchMind — Frontend (Member 4)

React + Vite UI for ResearchMind: chat, knowledge-base ingestion, agent
reasoning trace, and a RAGAS evaluation dashboard.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. API calls to `/api/*` are proxied to your
FastAPI backend at `http://localhost:8000` (see `vite.config.js`). Make sure
the backend is running and Ollama is up (`ollama serve`) before testing chat.

## Structure

```
src/
  api/client.js          all backend calls in one place
  components/
    ChatView.jsx          composer + message list + trace panel layout
    MessageBubble.jsx      one chat message (markdown-rendered)
    SourceCitations.jsx    collapsible citation cards under an answer
    TracePanel.jsx         agent reasoning log (THOUGHT/ACTION/OBSERVATION)
    UploadView.jsx         PDF drag-drop, URL, arXiv, Wikipedia ingestion
    DashboardView.jsx      collection stats chart + RAGAS eval runner
  styles/index.css        design tokens + all component styles
```

## Design concept

The reasoning trace is treated like a real terminal log rather than a
generic sidebar, because a ReAct agent's steps are genuinely sequential —
numbering and step labels (`THOUGHT`, `ACTION`, `OBSERVATION`) encode real
information about what the agent did and in what order.

## Known gap: agent trace

Member 2's LangGraph agent isn't wired into the chat API yet. `TracePanel`
is built to read a `trace: [{ type, content, tool? }]` array from the chat
response — as soon as `/chat/query` or `/chat/conversation` include that
field, the panel will start rendering real steps with zero frontend changes.
Until then it shows an honest "no trace yet" state instead of faking it.

## RAGAS dashboard

`DashboardView` calls two endpoints added for this work:
- `GET /ingest/stats` — collection totals + source-type breakdown (chart)
- `POST /evaluate/run` — runs given questions through the RAG chain and
  scores them with RAGAS `faithfulness` / `answer_relevancy`
- `GET /evaluate/latest` — last run's scores, cached in-memory server-side

These live in `backend/routers/evaluate.py` and
`backend/evaluation/ragas_eval.py`, and are already registered in
`backend/main.py`. Install the new deps before running the backend:

```bash
pip install -r requirements.txt
```

Note: evaluation calls the local Ollama model once per question for the
answer, plus more calls per metric to judge it — keep eval question lists
to 5–10 items.

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

## Design

Dark, glassmorphism theme — deep purple/violet gradient background, translucent
blurred panels, pill-shaped controls. Citations render as small numbered badges;
the reasoning trace renders as a stack of cards, since a ReAct agent's steps are
genuinely sequential — the numbering and step labels (`THOUGHT`, `ACTION`,
`OBSERVATION`) encode real information about what the agent did and in what order.

## Agent integration

Chat calls `POST /chat/agent` (Member 2's LangGraph ReAct agent), not the older
plain-RAG `/chat/query` / `/chat/conversation` endpoints. The backend returns
`reasoning_trace` in its own shape; `formatTrace()` in `ChatView.jsx` adapts that
into what `TracePanel.jsx` expects (`{ type, content, tool? }`) without needing to
change the panel itself.

**Known limitation, not a frontend bug:** local Ollama models don't always emit
tool calls reliably, especially on a second/refined call within one turn. Two
defensive patches currently live in `backend/agent/service.py` and
`backend/agent/prompts.py` to catch the visible symptoms (raw tool-call JSON
leaking into an answer; the model fabricating a "according to X" attribution when
a tool actually returned nothing useful). These are mitigations for a model
reliability limitation, not a full fix — see commit history for details if this
needs revisiting.

## RAGAS dashboard

`DashboardView` calls:
- `GET /ingest/stats` — collection totals + source-type breakdown (chart)
- `POST /evaluate/run` — runs given questions through the RAG chain and scores
  them with RAGAS `faithfulness` / `answer_relevancy`
- `GET /evaluate/latest` — last run's scores, cached in-memory server-side

These live in `backend/routers/evaluate.py` and `backend/evaluation/ragas_eval.py`.
Install the deps before running the backend:

```bash
pip install -r requirements.txt
```

**Important:** evaluation calls the local Ollama model once per question for the
answer, plus several more calls per metric to judge it. On CPU-only local
hardware this is genuinely slow — a single question can take 10-15+ minutes.
Keep eval question lists short (1-3 items) for interactive testing, and treat a
full run as something to do once and save the results, not something to
re-run live in a demo.
# ResearchMind — Frontend (Member 4)

React + Vite UI for ResearchMind: chat with inline document attachment and a
live reasoning trace, a knowledge-base document manager, and a RAGAS
evaluation dashboard.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. API calls to `/api/*` are proxied to your FastAPI
backend at `http://localhost:8000` (see `vite.config.js`). Make sure the backend is
running and Ollama is up (`ollama serve`, with `llama3.2` pulled) before testing chat.

## Structure

```
src/
api/client.js          all backend calls in one place
utils/documentStore.js localStorage-backed record of every document ingested this browser (no backend "list documents" endpoint exists)
components/
ChatView.jsx          message list + two-row composer + trace panel layout
AttachmentBar.jsx      composer's second row — attach a PDF, URL, arXiv paper, or Wikipedia article without leaving the chat
MessageBubble.jsx      one chat message (markdown-rendered)
SourceCitations.jsx    collapsible citation cards under an answer
TracePanel.jsx         agent reasoning log (THOUGHT/ACTION/OBSERVATION)
UploadView.jsx         Knowledge Base page — document manager (list + delete) only; adding documents happens in Chat now
DashboardView.jsx      collection stats chart + RAGAS eval runner
styles/index.css        design tokens + all component styles

```

## Design

Dark, glassmorphism theme — deep purple/violet gradient background, translucent
blurred panels, pill-shaped controls. Citations render as small numbered badges;
the reasoning trace renders as a stack of cards, since a ReAct agent's steps are
genuinely sequential — the numbering and step labels (`THOUGHT`, `ACTION`,
`OBSERVATION`) encode real information about what the agent did and in what order.

## Where document ingestion lives

Attaching a document happens **from the chat composer** (`AttachmentBar.jsx`),
not the Knowledge Base page — PDF opens a file picker directly; URL, arXiv,
and Wikipedia open a small inline prompt for the query/link. The Knowledge
Base page (`UploadView.jsx`) is document *management* only: a list of
everything ever ingested (read from `documentStore.js`, a local record kept
since there's no backend "list all documents" endpoint) with delete buttons
wired to `DELETE /ingest/session/{session_id}`.

Every attachment gets its own unique backend `session_id` regardless of which
chat it was uploaded from — this matters because ChromaDB deletion happens
by `session_id`, and reusing the chat's own conversation ID for multiple
documents would delete all of them together when only one is removed.
`chatSessionId` is a separate, purely local field used only to decide which
doc pills to show above a given conversation's composer.

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

**Also known:** `GET /ingest/stats` (used by the Dashboard chart) only samples
the first 500 chunks in `rag/vectorstore.py`'s `get_collection_stats()`, so
source types added after the collection passes 500 total chunks can appear
missing from the breakdown even though they're correctly stored. Fix is a
one-line change (`sample = vs.get(limit=count)` instead of `limit=min(count, 500)`)
— flagged to Member 1 since it's their file.

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

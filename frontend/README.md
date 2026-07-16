# ResearchMind — Frontend (Member 4)

React + Vite UI for ResearchMind. Chat with inline document attachment and a live reasoning trace, a knowledge base doc manager, and a RAGAS eval dashboard.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. API calls to `/api/*` get proxied to the FastAPI backend at `http://localhost:8000` (see `vite.config.js`). Backend needs to be running, and Ollama needs to be up too (`ollama serve`, with `llama3.2` pulled) before chat will actually work.

## Structure

```
src/
api/client.js          all backend calls in one place
utils/documentStore.js localStorage record of every doc ingested in this browser (there's no backend "list documents" endpoint)
components/
ChatView.jsx          message list + two-row composer + trace panel layout
AttachmentBar.jsx      composer's second row — attach a PDF, URL, arXiv paper, or Wikipedia article without leaving the chat
MessageBubble.jsx      one chat message (markdown-rendered)
SourceCitations.jsx    collapsible citation cards under an answer
TracePanel.jsx         agent reasoning log (THOUGHT/ACTION/OBSERVATION)
UploadView.jsx         Knowledge Base page — document manager
DashboardView.jsx      collection stats chart + RAGAS eval runner
styles/index.css        design tokens + all component styles

```

## Design

Dark glassmorphism theme — deep purple/violet gradient background, translucent blurred panels, pill-shaped controls. Citations show up as small numbered badges. The reasoning trace is a stack of cards, since a ReAct agent's steps are actually sequential — the numbering and step labels (`THOUGHT`, `ACTION`, `OBSERVATION`) mean something about what the agent did and when.

## Where document ingestion lives

You attach docs from the chat composer (`AttachmentBar.jsx`) — PDF opens a file picker, URL/arXiv/Wikipedia open a small inline prompt for the link or query. The Knowledge Base page (`UploadView.jsx`) is just for managing what's already been ingested: a list of everything, read from `documentStore.js` (a local record, since there's no backend endpoint to list all docs), with delete buttons wired to `DELETE /ingest/session/{session_id}`.

Every attachment gets its own backend `session_id`, no matter which chat it came from. This matters because ChromaDB deletes by `session_id` — if we reused the chat's conversation ID for every doc in it, deleting one document would wipe out all of them. `chatSessionId` is separate and purely local, just used to decide which doc pills show up above a given conversation's composer.

## Agent integration

Chat hits `POST /chat/agent` (Member 2's LangGraph ReAct agent), not the older plain-RAG `/chat/query` / `/chat/conversation` endpoints. The backend's `reasoning_trace` comes back in its own shape, and `formatTrace()` in `ChatView.jsx` converts it into what `TracePanel.jsx` expects (`{ type, content, tool? }`), so the panel itself didn't need to change.

**Not a frontend bug, but worth knowing:** local Ollama models don't reliably emit tool calls, especially on a second/refined call within the same turn. There are two patches for this in `backend/agent/service.py` and `backend/agent/prompts.py` that catch the visible symptoms — raw tool-call JSON leaking into an answer, or the model making up an "according to X" attribution when a tool actually returned nothing useful. These are band-aids for a model reliability issue, not a real fix. Check commit history if this needs revisiting.

**Also worth knowing:** `GET /ingest/stats` (used by the Dashboard chart) only samples the first 500 chunks in `rag/vectorstore.py`'s `get_collection_stats()`. So source types added after the collection passes 500 total chunks can look missing from the breakdown even though they're stored fine. Fix is a one-liner (`sample = vs.get(limit=count)` instead of `limit=min(count, 500)`) — flagged to Member 1 since it's their file.

## RAGAS dashboard

`DashboardView` calls:
- `GET /ingest/stats` — collection totals + source-type breakdown (chart)
- `POST /evaluate/run` — runs the given questions through the RAG chain and scores them with RAGAS `faithfulness` / `answer_relevancy`
- `GET /evaluate/latest` — last run's scores, cached in-memory server-side

These live in `backend/routers/evaluate.py` and `backend/evaluation/ragas_eval.py`. Install the deps before running the backend:

```bash
pip install -r requirements.txt
```

**Heads up:** evaluation calls the local Ollama model once per question for the answer, then several more times per metric to judge it. On CPU-only hardware this is slow — one question can take 10-15+ minutes. Keep eval question lists short (1-3 items) for testing, and don't try to run a full eval live in a demo — do it once ahead of time and save the results.

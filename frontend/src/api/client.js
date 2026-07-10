// Central place for every backend call. Vite's dev proxy (see vite.config.js)
// forwards "/api/*" to http://localhost:8000/*, so the same base works in
// dev and prod as long as you set VITE_API_BASE for prod deployments.

const BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData
      ? undefined
      : { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errBody = await res.json();
      detail = errBody.detail || JSON.stringify(errBody);
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

// ── Chat ──────────────────────────────────────────
export const chatApi = {
  query: (question) =>
    request('/chat/query', { method: 'POST', body: JSON.stringify({ question }) }),

  converse: (question, sessionId) =>
    request('/chat/conversation', {
      method: 'POST',
      body: JSON.stringify({ question, session_id: sessionId }),
    }),

  history: (sessionId) => request(`/chat/history/${sessionId}`),
};

// ── Ingestion ─────────────────────────────────────
export const ingestApi = {
  pdf: (file, sessionId) => {
    const form = new FormData();
    form.append('file', file);
    const qs = sessionId ? `?session_id=${sessionId}` : '';
    return request(`/ingest/pdf${qs}`, { method: 'POST', body: form });
  },

  url: (url, sessionId) =>
    request('/ingest/url', {
      method: 'POST',
      body: JSON.stringify({ url, session_id: sessionId }),
    }),

  arxiv: (query, maxResults, sessionId) =>
    request('/ingest/arxiv', {
      method: 'POST',
      body: JSON.stringify({ query, max_results: maxResults, session_id: sessionId }),
    }),

  wikipedia: (query, sessionId) =>
    request('/ingest/wikipedia', {
      method: 'POST',
      body: JSON.stringify({ query, session_id: sessionId }),
    }),

  stats: () => request('/ingest/stats'),
};

// ── Evaluation (RAGAS) ────────────────────────────
export const evalApi = {
  run: (questions) =>
    request('/evaluate/run', { method: 'POST', body: JSON.stringify({ questions }) }),

  latest: () => request('/evaluate/latest'),
};

// ── Health ────────────────────────────────────────
export const healthApi = {
  check: () => request('/health'),
};

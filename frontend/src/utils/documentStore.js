// Client-side record of every document ingested this browser, since there's
// no backend "list all documents" endpoint — only aggregate stats. Used by
// both the chat composer's doc pills and the Knowledge Base document
// manager. Persisted the same way chat history is (localStorage), so it
// survives refreshes.
//
// IMPORTANT: two different IDs are tracked per document, deliberately kept
// separate:
//   - sessionId     → the backend's own per-document ChromaDB session_id
//                      (unique per upload). This is what DELETE
//                      /ingest/session/{id} actually deletes by — it must
//                      never be shared between two different documents, or
//                      deleting one deletes both.
//   - chatSessionId → which CHAT conversation this document was uploaded
//                      from (if any), used only to decide which doc pills
//                      to show above that conversation's composer. Purely
//                      local bookkeeping — never sent to the backend.

const STORAGE_KEY = 'researchmind:documents';

function loadDocuments() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveDocuments(docs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
  } catch {
    // non-fatal — worst case, document history doesn't survive a refresh
  }
}

const listeners = new Set();
function notify() {
  const docs = loadDocuments();
  listeners.forEach((fn) => fn(docs));
}

export function subscribe(fn) {
  listeners.add(fn);
  fn(loadDocuments());
  return () => listeners.delete(fn);
}

export function getDocuments() {
  return loadDocuments();
}

/**
 * Records a document from a successful ingest API response.
 * `sessionId` MUST be the backend's own response.session_id for THIS
 * upload (never a reused chat session_id), so each document has its own
 * independently deletable identity in ChromaDB.
 * `chatSessionId` is optional — set only when uploaded from an active chat
 * conversation, purely for grouping doc pills under that conversation.
 */
export function addDocument({ sessionId, chatSessionId, fileName, chunkCount, sourceType }) {
  const docs = loadDocuments();
  docs.unshift({
    id: `${sessionId}-${Date.now()}`,
    sessionId,
    chatSessionId: chatSessionId || null,
    fileName: fileName || 'Untitled document',
    chunkCount: chunkCount ?? 0,
    sourceType: sourceType || 'unknown',
    ingestedAt: new Date().toISOString(),
  });
  saveDocuments(docs);
  notify();
}

/**
 * Removes the document(s) matching this document's own unique sessionId.
 * Since every document now gets its own unique sessionId (never shared),
 * this only ever removes the one document the user actually deleted.
 */
export function removeBySession(sessionId) {
  const docs = loadDocuments();
  const remaining = docs.filter((d) => d.sessionId !== sessionId);
  saveDocuments(remaining);
  notify();
}

export function clearAllDocuments() {
  saveDocuments([]);
  notify();
}
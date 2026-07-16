import { useEffect, useState } from 'react';
import { ingestApi } from '../api/client.js';
import { subscribe as subscribeDocuments, removeBySession } from '../utils/documentStore.js';

const SOURCE_ICON = { pdf: '📄', url: '🔗', arxiv: '📚', wikipedia: '📖', unknown: '📁' };

/**
 * Knowledge Base page — document management only (list + delete).
 * Adding documents happens from the chat composer's attachment bar
 * (AttachmentBar.jsx) instead, so this page isn't a duplicate ingestion
 * form anymore — it's the one place to see everything ever ingested,
 * across every conversation, and remove it.
 */
export default function UploadView() {
  const [documents, setDocuments] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const [log, setLog] = useState([]);

  useEffect(() => subscribeDocuments(setDocuments), []);

  function pushLog(text, ok = true) {
    setLog((prev) => [...prev, { text, ok, ts: new Date().toLocaleTimeString() }]);
  }

  async function handleDelete(doc) {
    setDeletingId(doc.id);
    try {
      await ingestApi.deleteSession(doc.sessionId);
      removeBySession(doc.sessionId);
      pushLog(`Deleted ${doc.fileName}`);
    } catch (err) {
      pushLog(`Failed to delete ${doc.fileName}: ${err.message}`, false);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="panel-view">
      <h1 className="panel-title">Knowledge base</h1>
      <p className="panel-sub">
        Everything ingested across every conversation. To add a new source, use
        the attachment bar in Chat — this page is for reviewing and removing
        what's already there.
      </p>

      <div className="chart-card">
        <h3>Document manager</h3>
        {documents.length === 0 ? (
          <div className="doc-manager-empty">
            Nothing ingested yet — attach a PDF, URL, arXiv paper, or
            Wikipedia article from the Chat composer to get started.
          </div>
        ) : (
          <div className="doc-manager-list">
            {documents.map((doc) => (
              <div className="doc-manager-row" key={doc.id}>
                <span className="doc-manager-icon">{SOURCE_ICON[doc.sourceType] || SOURCE_ICON.unknown}</span>
                <div className="doc-manager-info">
                  <div className="doc-manager-name">{doc.fileName}</div>
                  <div className="doc-manager-meta">
                    {doc.chunkCount} chunks · {doc.sourceType} · {new Date(doc.ingestedAt).toLocaleString()}
                  </div>
                </div>
                <button
                  className="doc-manager-delete"
                  disabled={deletingId === doc.id}
                  onClick={() => handleDelete(doc)}
                >
                  {deletingId === doc.id ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {log.length > 0 && (
        <div className="ingest-log">
          {log.map((l, i) => (
            <div className={`log-line ${l.ok ? 'ok' : 'err'}`} key={i}>
              [{l.ts}] {l.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
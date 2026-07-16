import { useRef, useState } from 'react';
import { ingestApi } from '../api/client.js';
import { addDocument } from '../utils/documentStore.js';

/**
 * Shared upload control. `compact` renders as a single icon button for the
 * chat composer; the full (non-compact) form is used on the Knowledge Base
 * page.
 *
 * `chatSessionId` (only relevant when compact/used inside a chat) is ONLY
 * used to tag the document locally for doc-pill grouping — it is NOT sent
 * to the backend. Each upload always requests its own fresh session_id
 * from the backend (by not passing one), so every document gets an
 * independently deletable identity and deleting one never removes another.
 */
export default function DocumentUpload({ compact = false, chatSessionId, onUploaded }) {
  const fileInputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleFiles(files) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      for (const file of files) {
        // No sessionId passed here on purpose — see note above.
        const result = await ingestApi.pdf(file);
        addDocument({
          sessionId: result.session_id,
          chatSessionId,
          fileName: result.file_name || file.name,
          chunkCount: result.chunk_count,
          sourceType: 'pdf',
        });
        onUploaded?.(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  if (compact) {
    return (
      <>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          style={{ display: 'none' }}
          disabled={busy}
          onChange={(e) => handleFiles(Array.from(e.target.files))}
        />
        <button
          type="button"
          className="composer-upload-btn"
          title="Attach a PDF"
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
        >
          {busy ? '…' : '📎'}
        </button>
        {error && <span className="composer-upload-error">{error}</span>}
      </>
    );
  }

  return (
    <div className="ingest-card">
      <h3>PDF upload</h3>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        multiple
        disabled={busy}
        onChange={(e) => handleFiles(Array.from(e.target.files))}
      />
      {busy && <div className="ingest-log-inline">Uploading…</div>}
      {error && <div className="ingest-log-inline error">{error}</div>}
    </div>
  );
}
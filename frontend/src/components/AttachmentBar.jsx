import { useRef, useState } from 'react';
import { ingestApi } from '../api/client.js';
import { addDocument } from '../utils/documentStore.js';

const SOURCES = [
  { key: 'pdf', label: 'PDF', icon: '📄' },
  { key: 'url', label: 'URL', icon: '🔗' },
  { key: 'arxiv', label: 'arXiv', icon: '📚' },
  { key: 'wikipedia', label: 'Wiki', icon: '📖' },
];

const PLACEHOLDERS = {
  url: 'https://example.com/article',
  arxiv: 'e.g. retrieval augmented generation',
  wikipedia: 'e.g. Transformer architecture',
};

/**
 * Second row inside the chat composer — lets you attach a document from
 * any of the four ingestion sources without leaving the conversation.
 * PDF opens a native file picker directly; URL/arXiv/Wikipedia open a
 * small inline prompt for the query/link, since those need typed input
 * rather than a file.
 *
 * `chatSessionId` is only used for local doc-pill grouping (never sent to
 * the backend) — see documentStore.js for why that separation matters.
 */
export default function AttachmentBar({ chatSessionId, onUploaded }) {
  const [activeType, setActiveType] = useState(null); // 'url' | 'arxiv' | 'wikipedia' | null
  const [promptValue, setPromptValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  function toggleType(key) {
    if (key === 'pdf') {
      fileInputRef.current?.click();
      return;
    }
    setError(null);
    setActiveType((prev) => (prev === key ? null : key));
    setPromptValue('');
  }

  async function handlePdfFiles(files) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      for (const file of files) {
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

  async function handlePromptSubmit() {
    const value = promptValue.trim();
    if (!value || busy) return;
    setBusy(true);
    setError(null);
    try {
      let result;
      let fileName;
      if (activeType === 'url') {
        result = await ingestApi.url(value);
        fileName = result.file_name || value;
      } else if (activeType === 'arxiv') {
        result = await ingestApi.arxiv(value, 5);
        fileName = result.file_name || `arXiv: ${value}`;
      } else if (activeType === 'wikipedia') {
        result = await ingestApi.wikipedia(value);
        fileName = result.file_name || `Wikipedia: ${value}`;
      }
      addDocument({
        sessionId: result.session_id,
        chatSessionId,
        fileName,
        chunkCount: result.chunk_count,
        sourceType: activeType,
      });
      onUploaded?.(result);
      setActiveType(null);
      setPromptValue('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="attachment-wrap">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        style={{ display: 'none' }}
        disabled={busy}
        onChange={(e) => handlePdfFiles(Array.from(e.target.files))}
      />

      {activeType && (
        <div className="attachment-prompt">
          <input
            type="text"
            autoFocus
            placeholder={PLACEHOLDERS[activeType]}
            value={promptValue}
            disabled={busy}
            onChange={(e) => setPromptValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
          />
          <button
            type="button"
            className="attachment-prompt-go"
            disabled={busy || !promptValue.trim()}
            onClick={handlePromptSubmit}
          >
            {busy ? '…' : 'Add'}
          </button>
          <button
            type="button"
            className="attachment-prompt-cancel"
            disabled={busy}
            onClick={() => { setActiveType(null); setPromptValue(''); }}
          >
            ×
          </button>
        </div>
      )}

      {error && <div className="attachment-error">{error}</div>}

      <div className="attachment-row">
        {SOURCES.map((s) => (
          <button
            key={s.key}
            type="button"
            className={`attachment-btn ${activeType === s.key ? 'active' : ''}`}
            disabled={busy}
            onClick={() => toggleType(s.key)}
          >
            <span>{s.icon}</span> {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
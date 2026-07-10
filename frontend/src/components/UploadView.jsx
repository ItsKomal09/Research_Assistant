import { useState } from 'react';
import { ingestApi } from '../api/client.js';

export default function UploadView() {
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [urlInput, setUrlInput] = useState('');
  const [arxivInput, setArxivInput] = useState('');
  const [wikiInput, setWikiInput] = useState('');

  function pushLog(text, ok = true) {
    setLog((prev) => [...prev, { text, ok, ts: new Date().toLocaleTimeString() }]);
  }

  async function withBusy(fn) {
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      pushLog(err.message, false);
    } finally {
      setBusy(false);
    }
  }

  function handlePdfFiles(files) {
    if (!files || files.length === 0) return;
    withBusy(async () => {
      for (const file of files) {
        pushLog(`Uploading ${file.name}…`);
        const res = await ingestApi.pdf(file);
        pushLog(`${file.name}: ${res.message || `added ${res.added} chunks`}`);
      }
    });
  }

  function handleUrl() {
    if (!urlInput.trim()) return;
    withBusy(async () => {
      pushLog(`Fetching ${urlInput}…`);
      const res = await ingestApi.url(urlInput.trim());
      pushLog(res.message || `added ${res.added} chunks`);
      setUrlInput('');
    });
  }

  function handleArxiv() {
    if (!arxivInput.trim()) return;
    withBusy(async () => {
      pushLog(`Searching arXiv for "${arxivInput}"…`);
      const res = await ingestApi.arxiv(arxivInput.trim(), 5);
      pushLog(res.message || `added ${res.added} chunks`);
      setArxivInput('');
    });
  }

  function handleWikipedia() {
    if (!wikiInput.trim()) return;
    withBusy(async () => {
      pushLog(`Searching Wikipedia for "${wikiInput}"…`);
      const res = await ingestApi.wikipedia(wikiInput.trim());
      pushLog(res.message || `added ${res.added} chunks`);
      setWikiInput('');
    });
  }

  return (
    <div className="panel-view">
      <h1 className="panel-title">Knowledge base</h1>
      <p className="panel-sub">Add sources for the agent to reason over.</p>

      <div className="ingest-grid">
        <div className="ingest-card">
          <h3>PDF upload</h3>
          <div
            className={`dropzone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handlePdfFiles(Array.from(e.dataTransfer.files).filter((f) => f.type === 'application/pdf'));
            }}
          >
            Drag a PDF here, or
            <div style={{ marginTop: 8 }}>
              <input
                type="file"
                accept="application/pdf"
                multiple
                disabled={busy}
                onChange={(e) => handlePdfFiles(Array.from(e.target.files))}
              />
            </div>
          </div>
        </div>

        <div className="ingest-card">
          <h3>From URL</h3>
          <input
            type="text"
            placeholder="https://example.com/article"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUrl()}
          />
          <button onClick={handleUrl} disabled={busy || !urlInput.trim()}>Ingest URL</button>
        </div>

        <div className="ingest-card">
          <h3>arXiv search</h3>
          <input
            type="text"
            placeholder="e.g. retrieval augmented generation"
            value={arxivInput}
            onChange={(e) => setArxivInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleArxiv()}
          />
          <button onClick={handleArxiv} disabled={busy || !arxivInput.trim()}>Fetch papers</button>
        </div>

        <div className="ingest-card">
          <h3>Wikipedia</h3>
          <input
            type="text"
            placeholder="e.g. Transformer architecture"
            value={wikiInput}
            onChange={(e) => setWikiInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleWikipedia()}
          />
          <button onClick={handleWikipedia} disabled={busy || !wikiInput.trim()}>Fetch article</button>
        </div>
      </div>

      <div className="ingest-log">
        {log.length === 0 && <div className="log-line">No activity yet.</div>}
        {log.map((l, i) => (
          <div className={`log-line ${l.ok ? 'ok' : 'err'}`} key={i}>
            [{l.ts}] {l.text}
          </div>
        ))}
      </div>
    </div>
  );
}

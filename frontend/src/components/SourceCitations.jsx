import { useState } from 'react';

/**
 * Renders the "sources" array returned alongside a chat answer.
 * Backend shape (see rag/chains.py query_with_citations):
 * { display_source, content, source_type, title, score? }
 *
 * Each citation renders as a rotated accession-stamp badge (№01, №02…),
 * like a library's own stamping system — the signature visual element.
 */
export default function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-block">
      <button className="sources-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? '▾' : '▸'} {sources.length} source{sources.length > 1 ? 's' : ''} cited
      </button>

      {open &&
        sources.map((s, i) => {
          const title = s.display_source || s.title || 'Unknown source';
          const snippet = (s.content || '').slice(0, 220);
          const relevance =
            typeof s.score === 'number' ? scoreToRelevance(s.score) : null;

          return (
            <div className="source-card" key={i}>
              <div className="source-stamp">
                <span className="source-stamp-inner">{String(i + 1).padStart(2, '0')}</span>
              </div>
              <div className="source-card-body">
                <div className="source-card-head">
                  <span className="source-title">{title}</span>
                  {relevance !== null && (
                    <span className="source-score">{relevance}% match</span>
                  )}
                </div>
                {s.source_type && <span className="source-tag">{s.source_type}</span>}
                <div className="source-snippet">
                  {snippet}
                  {s.content && s.content.length > 220 ? '…' : ''}
                </div>
              </div>
            </div>
          );
        })}
    </div>
  );
}

// Chroma returns cosine *distance* (lower = closer). Convert to a rough
// 0-100 "relevance" percentage for display purposes only.
function scoreToRelevance(distance) {
  const clamped = Math.max(0, Math.min(1, distance));
  return Math.round((1 - clamped) * 100);
}
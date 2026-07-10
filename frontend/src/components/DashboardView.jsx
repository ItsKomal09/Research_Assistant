import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { ingestApi, evalApi } from '../api/client.js';

export default function DashboardView() {
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(null);

  const [questions, setQuestions] = useState(
    'What is retrieval augmented generation?\nHow does the hybrid retriever combine BM25 and vector search?'
  );
  const [evalResult, setEvalResult] = useState(null);
  const [evalError, setEvalError] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    ingestApi.stats().then(setStats).catch((e) => setStatsError(e.message));
    evalApi.latest().then(setEvalResult).catch(() => {});
  }, []);

  async function runEvaluation() {
    setRunning(true);
    setEvalError(null);
    try {
      const qList = questions.split('\n').map((q) => q.trim()).filter(Boolean);
      const res = await evalApi.run(qList);
      setEvalResult(res);
    } catch (err) {
      setEvalError(err.message);
    } finally {
      setRunning(false);
    }
  }

  const breakdown = stats?.source_breakdown
    ? Object.entries(stats.source_breakdown).map(([name, count]) => ({ name, count }))
    : [];

  return (
    <div className="panel-view">
      <h1 className="panel-title">Dashboard</h1>
      <p className="panel-sub">Knowledge base health and RAGAS evaluation scores.</p>

      {statsError && (
        <div className="ingest-log" style={{ marginBottom: 20 }}>
          <div className="log-line err">
            Couldn't load stats: {statsError}. Make sure GET /ingest/stats is
            registered on the backend (see backend/routers/ingest.py).
          </div>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total_chunks ?? '—'}</div>
          <div className="stat-label">Total chunks</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{breakdown.length}</div>
          <div className="stat-label">Source types</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.collection_name ?? '—'}</div>
          <div className="stat-label">Collection</div>
        </div>
      </div>

      {breakdown.length > 0 && (
        <div className="chart-card">
          <h3>Chunks by source type</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={breakdown}>
              <CartesianGrid stroke="#d8d4bd" vertical={false} />
              <XAxis dataKey="name" stroke="#8c9282" fontSize={11} />
              <YAxis stroke="#8c9282" fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#f5f6ee', border: '1px solid #c6c2a8', fontSize: 12 }}
              />
              <Bar dataKey="count" fill="#9c3a2c" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="chart-card">
        <h3>RAGAS evaluation</h3>
        <p className="panel-sub" style={{ marginBottom: 12 }}>
          Runs each question through the RAG chain and scores faithfulness
          and answer relevancy against the retrieved context.
        </p>
        <textarea
          rows={4}
          style={{
            width: '100%', background: '#f5f6ee', border: '1px solid #c6c2a8',
            borderRadius: 3, color: '#202b23', fontFamily: 'IBM Plex Mono, monospace',
            fontSize: 12.5, padding: 10, marginBottom: 12,
          }}
          value={questions}
          onChange={(e) => setQuestions(e.target.value)}
          placeholder="One question per line"
        />
        <div>
          <button className="run-eval-btn" onClick={runEvaluation} disabled={running}>
            {running ? 'Running evaluation…' : 'Run RAGAS evaluation'}
          </button>
        </div>

        {evalError && <div className="log-line err" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>{evalError}</div>}

        {evalResult?.results && (
          <table className="eval-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Faithfulness</th>
                <th>Relevancy</th>
              </tr>
            </thead>
            <tbody>
              {evalResult.results.map((r, i) => (
                <tr key={i}>
                  <td>{r.question}</td>
                  <td>{formatScore(r.faithfulness)}</td>
                  <td>{formatScore(r.answer_relevancy)}</td>
                </tr>
              ))}
            </tbody>
            {evalResult.averages && (
              <tfoot>
                <tr>
                  <td><strong>Average</strong></td>
                  <td><strong>{formatScore(evalResult.averages.faithfulness)}</strong></td>
                  <td><strong>{formatScore(evalResult.averages.answer_relevancy)}</strong></td>
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </div>
    </div>
  );
}

function formatScore(v) {
  if (typeof v !== 'number') return '—';
  return v.toFixed(2);
}

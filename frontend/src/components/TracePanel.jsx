/**
 * Shows the agent's reasoning trace for the currently selected message.
 *
 * Expected shape once Member 2's LangGraph agent exposes it:
 *   trace: [{ type: "thought" | "action" | "observation" | "answer", content, tool? }]
 *
 * Until that field exists on an API response, this renders an honest
 * empty state instead of pretending to show reasoning that isn't there.
 * Each step renders as an index card, since a ReAct trace is genuinely
 * an ordered stack of entries — that's real information, not decoration.
 */
export default function TracePanel({ trace, loading }) {
  return (
    <aside className="trace-panel">
      <div className="trace-header">
        <span>Reasoning trace</span>
      </div>
      <div className="trace-body">
        {loading && (
          <div className="trace-step">
            <span className="trace-step-num">card ·</span>
            <span className="trace-step-label thought">THINKING</span>
            <div className="trace-step-content">
              agent is deciding which tool to use
              <span className="cursor-blink" />
            </div>
          </div>
        )}

        {!loading && (!trace || trace.length === 0) && (
          <div className="trace-empty">
            No trace for this message yet.{'\n\n'}
            This panel renders the agent's THOUGHT → ACTION → OBSERVATION
            steps as index cards as soon as the agent API includes a
            `trace` array in its response.
          </div>
        )}

        {!loading &&
          trace &&
          trace.map((step, i) => (
            <div className="trace-step" key={i}>
              <span className="trace-step-num">card {String(i + 1).padStart(2, '0')}</span>
              <span className={`trace-step-label ${step.type}`}>
                {labelFor(step.type)}
                {step.tool ? ` · ${step.tool}` : ''}
              </span>
              <div className="trace-step-content">{step.content}</div>
            </div>
          ))}
      </div>
    </aside>
  );
}

function labelFor(type) {
  switch (type) {
    case 'thought': return 'THOUGHT';
    case 'action': return 'ACTION';
    case 'observation': return 'OBSERVATION';
    case 'answer': return 'ANSWER';
    default: return (type || 'STEP').toUpperCase();
  }
}
import ReactMarkdown from 'react-markdown';
import SourceCitations from './SourceCitations.jsx';

export default function MessageBubble({ message, isSelected, onSelect }) {
  const { role, content, sources, pending, error } = message;

  return (
    <div
      className={`msg-row ${role}`}
      onClick={role === 'assistant' ? onSelect : undefined}
      style={role === 'assistant' ? { cursor: 'pointer' } : undefined}
    >
      <span className="msg-role">{role === 'user' ? 'You' : 'ResearchMind'}</span>
      <div
        className={`msg-bubble ${pending ? 'pending' : ''} ${error ? 'error' : ''} ${
          isSelected ? 'selected' : ''
        }`}
      >
        {pending ? (
          <span>
            thinking<span className="cursor-blink" />
          </span>
        ) : error ? (
          content
        ) : (
          <ReactMarkdown>{content}</ReactMarkdown>
        )}
      </div>
      {!pending && !error && role === 'assistant' && (
        <SourceCitations sources={sources} />
      )}
    </div>
  );
}

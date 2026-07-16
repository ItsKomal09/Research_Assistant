import { useEffect, useRef, useState } from 'react';
import { chatApi } from '../api/client.js';
import MessageBubble from './MessageBubble.jsx';
import TracePanel from './TracePanel.jsx';
import AttachmentBar from './AttachmentBar.jsx';
import { subscribe as subscribeDocuments } from '../utils/documentStore.js';

const STORAGE_KEY = 'researchmind:chat';

function formatTrace(rawTrace) {
  if (!Array.isArray(rawTrace)) return [];
  const steps = [];

  for (const s of rawTrace) {
    if (s.type === 'action') {
      if (s.thought) {
        steps.push({ type: 'thought', content: s.thought });
      }
      const args = s.input && Object.keys(s.input).length ? JSON.stringify(s.input) : '';
      steps.push({
        type: 'action',
        tool: s.tool,
        content: args ? `Calling ${s.tool}(${args})` : `Calling ${s.tool}`,
      });
    } else if (s.type === 'observation') {
      steps.push({ type: 'observation', tool: s.tool, content: s.output });
    } else if (s.type === 'final_answer') {
      steps.push({ type: 'answer', content: s.output });
    }
  }

  return steps;
}

function loadStoredChat() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { messages: [], sessionId: null };
    const parsed = JSON.parse(raw);
    const rawMessages = Array.isArray(parsed.messages) ? parsed.messages : [];

    const messages = rawMessages.map((m) =>
      m.pending
        ? {
            role: 'assistant',
            content: 'This response was interrupted (page was refreshed or closed while waiting). Please resend your question.',
            error: true,
          }
        : m
    );

    return { messages, sessionId: parsed.sessionId || null };
  } catch {
    return { messages: [], sessionId: null };
  }
}

export default function ChatView() {
  const initial = loadStoredChat();
  const [messages, setMessages] = useState(initial.messages);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(initial.sessionId);
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [documents, setDocuments] = useState([]);
  const scrollRef = useRef(null);

  const selected = selectedIdx !== null ? messages[selectedIdx] : null;

  const sessionDocuments = documents.filter((d) => d.chatSessionId === sessionId);

  useEffect(() => subscribeDocuments(setDocuments), []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, sessionId }));
    } catch {
      // non-fatal
    }
  }, [messages, sessionId]);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    });
  }

  function handleClearChat() {
    setMessages([]);
    setSessionId(null);
    setSelectedIdx(null);
    localStorage.removeItem(STORAGE_KEY);
  }

  async function handleSend() {
    const question = input.trim();
    if (!question || sending) return;

    const assistantIndex = messages.length + 1;
    setInput('');
    setSending(true);

    const userMsg = { role: 'user', content: question };
    const pendingMsg = { role: 'assistant', content: '', pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setSelectedIdx(assistantIndex);
    scrollToBottom();

    try {
      const result = await chatApi.agent(question, sessionId);
      if (result.session_id) setSessionId(result.session_id);

      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: 'assistant',
          content: result.answer,
          sources: result.sources,
          trace: formatTrace(result.reasoning_trace),
        };
        return next;
      });
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: 'assistant',
          content: `Something went wrong reaching the backend: ${err.message}`,
          error: true,
        };
        return next;
      });
    } finally {
      setSending(false);
      scrollToBottom();
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-view">
      <div className="chat-column">
        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-title">Open a new case file</div>
              Ask a question about anything you've ingested — a PDF, a paper
              pulled from arXiv, or a Wikipedia article. Answers come with
              cited sources and a visible reasoning trace on the right,
              showing exactly which tools the agent used to get there.
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              message={m}
              isSelected={i === selectedIdx}
              onSelect={() => setSelectedIdx(i)}
            />
          ))}
        </div>

        {sessionDocuments.length > 0 && (
          <div className="doc-pills-row">
            {sessionDocuments.map((doc) => (
              <span className="doc-pill" key={doc.id} title={`${doc.chunkCount} chunks`}>
                📄 {doc.fileName}
              </span>
            ))}
          </div>
        )}

        <div className="composer-box">
          <div className="composer-row-top">
            <textarea
              rows={2}
              placeholder="Ask ResearchMind… (Enter to send, Shift+Enter for newline)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="send" onClick={handleSend} disabled={sending || !input.trim()}>
              Send
            </button>
            {messages.length > 0 && (
              <button
                onClick={handleClearChat}
                title="Clear conversation"
                style={{
                  background: 'transparent', border: '1px solid var(--glass-border-strong)',
                  color: 'var(--text-faint)', borderRadius: 100, padding: '0 14px', fontSize: 12,
                }}
              >
                Clear
              </button>
            )}
          </div>
          <AttachmentBar chatSessionId={sessionId} />
        </div>
      </div>

      <TracePanel
        trace={selected?.trace}
        loading={sending && selectedIdx === messages.length - 1}
      />
    </div>
  );
}
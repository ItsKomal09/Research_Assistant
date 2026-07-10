import { useEffect, useRef, useState } from 'react';
import { chatApi } from '../api/client.js';
import MessageBubble from './MessageBubble.jsx';
import TracePanel from './TracePanel.jsx';

const STORAGE_KEY = 'researchmind:chat';

function loadStoredChat() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { messages: [], sessionId: null };
    const parsed = JSON.parse(raw);
    const rawMessages = Array.isArray(parsed.messages) ? parsed.messages : [];

    // If the page was refreshed while a response was still in flight, that
    // message got saved mid-"thinking". There's no real request behind it
    // anymore, so it would otherwise show a frozen spinner forever.
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
  const scrollRef = useRef(null);

  const selected = selectedIdx !== null ? messages[selectedIdx] : null;

  // Persist to localStorage whenever the conversation changes, so a
  // browser refresh (not just switching tabs inside the app) survives.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, sessionId }));
    } catch {
      // localStorage can fail in rare cases (private browsing quotas, etc.) —
      // non-fatal, chat still works, it just won't survive a refresh.
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

    setInput('');
    setSending(true);

    const userMsg = { role: 'user', content: question };
    const pendingMsg = { role: 'assistant', content: '', pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    scrollToBottom();

    try {
      const result = await chatApi.converse(question, sessionId);
      if (result.session_id) setSessionId(result.session_id);

      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: 'assistant',
          content: result.answer,
          sources: result.sources,
          trace: result.trace, // present once Member 2's agent adds it
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
              cited sources and, once the agent trace is wired up, a visible
              reasoning log on the right.
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

        <div className="composer">
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
                background: 'transparent', border: '1px solid var(--border)',
                color: 'var(--text-faint)', borderRadius: 6, padding: '0 12px', fontSize: 12,
              }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <TracePanel
        trace={selected?.trace}
        loading={sending && selectedIdx === messages.length - 1}
      />
    </div>
  );
}
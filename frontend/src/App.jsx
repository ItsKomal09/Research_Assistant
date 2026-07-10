import { useEffect, useState } from 'react';
import ChatView from './components/ChatView.jsx';
import UploadView from './components/UploadView.jsx';
import DashboardView from './components/DashboardView.jsx';
import { healthApi } from './api/client.js';

const VIEWS = [
  { id: 'chat', label: 'Chat' },
  { id: 'upload', label: 'Knowledge base' },
  { id: 'dashboard', label: 'Dashboard' },
];

export default function App() {
  const [view, setView] = useState('chat');
  const [online, setOnline] = useState(null);

  useEffect(() => {
    healthApi.check().then(() => setOnline(true)).catch(() => setOnline(false));
    const interval = setInterval(() => {
      healthApi.check().then(() => setOnline(true)).catch(() => setOnline(false));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-shell">
      <div className="app-topbar">
        <span className="brand">ResearchMind<span className="brand-dot">.</span></span>
        <span className="status-pill">
          <span className={`status-dot ${online === null ? '' : online ? 'online' : 'offline'}`} />
          {online === null ? 'checking…' : online ? 'backend online' : 'backend unreachable'}
        </span>
      </div>

      <nav className="app-sidebar">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            className={`nav-item ${view === v.id ? 'active' : ''}`}
            onClick={() => setView(v.id)}
          >
            {v.label}
          </button>
        ))}
        <div className="sidebar-footer">ResearchMind v1.0</div>
      </nav>

      <main className="app-main">
        <div style={{ display: view === 'chat' ? 'flex' : 'none', width: '100%' }}>
          <ChatView />
        </div>
        <div style={{ display: view === 'upload' ? 'block' : 'none', width: '100%' }}>
          <UploadView />
        </div>
        <div style={{ display: view === 'dashboard' ? 'block' : 'none', width: '100%' }}>
          <DashboardView />
        </div>
      </main>
    </div>
  );
}
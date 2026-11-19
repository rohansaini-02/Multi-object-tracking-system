import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';
import { getHealthApi } from '../api/client';

const PAGE_TITLES = {
  dashboard: 'Tracking Dashboard',
  ingest: 'Upload & Configure',
  upload: 'Upload & Configure',
  workspace: 'Detection Workspace',
  results: 'Detection Workspace',
  benchmark: 'MOT17 Benchmark Suite',
  history: 'Tracking History',
  config: 'System Settings',
  settings: 'System Settings',
  login: 'Authentication',
};

export default function TopHeader({ activePage = 'dashboard', setActivePage }) {
  const [utcTime, setUtcTime] = useState('');
  const [backendHealth, setBackendHealth] = useState({
    connected: false,
    version: 'v0.1.0',
    loading: true,
  });

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const hours = String(now.getUTCHours()).padStart(2, '0');
      const minutes = String(now.getUTCMinutes()).padStart(2, '0');
      const seconds = String(now.getUTCSeconds()).padStart(2, '0');
      const ms = String(Math.floor(now.getUTCMilliseconds() / 10)).padStart(2, '0');
      setUtcTime(`${hours}:${minutes}:${seconds}.${ms}`);
    };

    updateClock();
    const timer = setInterval(updateClock, 100);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const checkHealth = async () => {
      try {
        const data = await getHealthApi();
        if (cancelled) return;
        if (data && data.status === 'ok') {
          setBackendHealth({
            connected: true,
            version: data.version ? `v${data.version}` : 'v0.1.0',
            loading: false,
          });
        } else {
          setBackendHealth((prev) => ({ ...prev, connected: false, loading: false }));
        }
      } catch {
        if (!cancelled) {
          setBackendHealth((prev) => ({ ...prev, connected: false, loading: false }));
        }
      }
    };

    checkHealth();
    const pollTimer = setInterval(checkHealth, 5000);
    return () => {
      cancelled = true;
      clearInterval(pollTimer);
    };
  }, []);

  const pageTitle = PAGE_TITLES[activePage] || 'Tracking Dashboard';

  return (
    <header style={{
      height: '44px',
      backgroundColor: 'var(--bg-header)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      flexShrink: 0,
      zIndex: 5,
    }}>
      {/* Left Dynamic Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
        <span
          className="font-mono"
          onClick={() => setActivePage && setActivePage('dashboard')}
          title="Return to Dashboard"
          style={{
            color: 'var(--text-muted)',
            letterSpacing: '0.05em',
            cursor: setActivePage ? 'pointer' : 'default',
            transition: 'color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            if (setActivePage) e.currentTarget.style.color = 'var(--accent-cyan)';
          }}
          onMouseLeave={(e) => {
            if (setActivePage) e.currentTarget.style.color = 'var(--text-muted)';
          }}
        >
          HOME
        </span>
        <span style={{ color: 'var(--text-muted)' }}>/</span>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{pageTitle}</span>
      </div>

      {/* Right Telemetry Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.75rem' }}>
        {/* Dynamic Connection Status Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 10px',
          borderRadius: '4px',
          backgroundColor: backendHealth.connected ? 'var(--accent-emerald-bg)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${backendHealth.connected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          color: backendHealth.connected ? 'var(--accent-emerald)' : 'var(--accent-rose)',
          fontSize: '0.7rem',
          fontWeight: 600,
          transition: 'all 0.3s ease',
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: backendHealth.connected ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            boxShadow: `0 0 6px ${backendHealth.connected ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`
          }}></span>
          <span>{backendHealth.connected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          <span style={{ color: 'var(--text-muted)', margin: '0 2px' }}>|</span>
          <span style={{ color: 'var(--text-secondary)' }}>
            {backendHealth.connected ? `Backend ${backendHealth.version}` : 'Backend Offline'}
          </span>
        </div>

        {/* UTC Real-time Clock */}
        <div className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={13} color="var(--text-muted)" />
          <span>UTC {utcTime || '—'}</span>
        </div>
      </div>
    </header>
  );
}

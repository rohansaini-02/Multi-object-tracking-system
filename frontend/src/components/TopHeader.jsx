import React, { useState, useEffect } from 'react';

export default function TopHeader() {
  const [utcTime, setUtcTime] = useState('');

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

  return (
    <header style={{
      height: '44px',
      backgroundColor: 'var(--bg-header)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justify: 'space-between',
      padding: '0 24px',
      flexShrink: 0,
      zIndex: 5,
    }}>
      {/* Left Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
        <span className="font-mono" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>WORKSTATION</span>
        <span style={{ color: 'var(--text-muted)' }}>/</span>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Operational Suite</span>
      </div>

      {/* Right Telemetry Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.75rem' }}>
        {/* System Online Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 10px',
          borderRadius: '4px',
          backgroundColor: 'var(--accent-emerald-bg)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: 'var(--accent-emerald)',
          fontSize: '0.7rem',
          fontWeight: 600
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: 'var(--accent-emerald)',
            boxShadow: '0 0 6px var(--accent-emerald)'
          }}></span>
          <span>SYSTEM ONLINE</span>
          <span style={{ color: 'var(--text-muted)', margin: '0 2px' }}>|</span>
          <span style={{ color: 'var(--text-secondary)' }}>Backend v0.1.0</span>
        </div>

        {/* UTC Real-time Clock */}
        <div className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>🕒</span>
          <span>UTC {utcTime || '14:02:49.08'}</span>
        </div>
      </div>
    </header>
  );
}

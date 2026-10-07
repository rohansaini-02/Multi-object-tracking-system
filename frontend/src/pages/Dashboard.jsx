import React from 'react';

export default function Dashboard() {
  return (
    <div className="app-container">
      <h2 style={{ marginBottom: '8px' }}>System Overview Dashboard</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
        High-level tracking job statistics and system throughput metrics.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total Jobs Run</span>
          <h3 style={{ fontSize: '1.8rem', marginTop: '8px', color: 'var(--primary)' }}>128</h3>
        </div>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Average MOTA</span>
          <h3 style={{ fontSize: '1.8rem', marginTop: '8px', color: 'var(--accent-emerald)' }}>60.4%</h3>
        </div>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Average IDF1</span>
          <h3 style={{ fontSize: '1.8rem', marginTop: '8px', color: 'var(--accent-cyan)' }}>63.5%</h3>
        </div>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>System Worker Queue</span>
          <h3 style={{ fontSize: '1.8rem', marginTop: '8px' }}>0 Jobs Queued</h3>
        </div>
      </div>
    </div>
  );
}

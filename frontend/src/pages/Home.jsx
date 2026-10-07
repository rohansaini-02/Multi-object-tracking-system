import React from 'react';

export default function Home({ setActivePage }) {
  return (
    <div className="app-container" style={{ paddingTop: '48px' }}>
      <div style={{ textAlign: 'center', maxWidth: '800px', margin: '0 auto 64px auto' }}>
        <span className="badge badge-cyan" style={{ marginBottom: '16px', display: 'inline-block' }}>
          DeepSORT + YOLOv8 System
        </span>
        <h1 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '20px', lineHeight: 1.2 }}>
          Multi-Object Tracking & Evaluation Engine
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', marginBottom: '32px' }}>
          Real-time and offline pedestrian detection, trajectory tracking, and MOT17 benchmark evaluation powered by FastAPI and DeepSORT.
        </p>
        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <button className="btn-primary" onClick={() => setActivePage('upload')}>
            Launch Tracker 🚀
          </button>
          <button className="btn-secondary" onClick={() => setActivePage('benchmark')}>
            View MOT17 Benchmarks 📊
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⚡</div>
          <h3 style={{ marginBottom: '8px' }}>Sub-300ms Interactive API</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            FastAPI async backend for lightning-fast job status polling and real-time frame progress updates.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>🎯</div>
          <h3 style={{ marginBottom: '8px' }}>YOLOv8 + Re-ID DeepSORT</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Combines Kalman motion filter with PyTorch L2-normalized appearance embeddings to prevent identity switches.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📈</div>
          <h3 style={{ marginBottom: '8px' }}>MOT17 Protocol Evaluation</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Compute MOTA, IDF1, and ID Switch metrics against MOT17 ground truth annotations.
          </p>
        </div>
      </div>
    </div>
  );
}

import React from 'react';

export default function ResultsViewer() {
  return (
    <div className="app-container">
      <h2 style={{ marginBottom: '8px' }}>Tracking Results & Video Player</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
        View processed annotated video playback with bounding boxes, ID trajectory overlays, and frame statistics.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{
            width: '100%',
            aspectRatio: '16/9',
            background: '#000',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
          }}>
            <span>🎥 Video playback will render here when job completes</span>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>Telemetry Summary</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total Unique Tracks</span>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary)' }}>42 objects</p>
            </div>
            <div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Processing FPS</span>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>34.2 FPS</p>
            </div>
            <div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total Processed Frames</span>
              <p style={{ fontSize: '1.5rem', fontWeight: 700 }}>525 frames</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

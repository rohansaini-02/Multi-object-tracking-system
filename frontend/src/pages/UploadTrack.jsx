import React, { useState } from 'react';

export default function UploadTrack() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [confThreshold, setConfThreshold] = useState(0.5);
  const [maxAge, setMaxAge] = useState(30);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  return (
    <div className="app-container">
      <h2 style={{ marginBottom: '8px' }}>Upload Video & Run Tracker</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
        Select an MP4 or AVI video file to process through YOLOv8 + DeepSORT tracking pipeline.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '32px', textAlign: 'center' }}>
          <div style={{
            border: '2px dashed var(--border-glow)',
            borderRadius: '12px',
            padding: '48px 24px',
            background: 'rgba(99, 102, 241, 0.03)',
            cursor: 'pointer',
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📁</div>
            <h4 style={{ marginBottom: '8px' }}>
              {selectedFile ? selectedFile.name : 'Drag and drop video file here'}
            </h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '16px' }}>
              Supported formats: .mp4, .avi (Max 500MB)
            </p>
            <input
              type="file"
              accept="video/mp4,video/avi"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              id="file-upload"
            />
            <label htmlFor="file-upload" className="btn-secondary" style={{ cursor: 'pointer' }}>
              Browse File
            </label>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '20px' }}>Tracker Configuration</h3>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              Confidence Threshold: <strong>{confThreshold}</strong>
            </label>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={confThreshold}
              onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>
              Max Coasting Age: <strong>{maxAge} frames</strong>
            </label>
            <input
              type="range"
              min="10"
              max="90"
              step="5"
              value={maxAge}
              onChange={(e) => setMaxAge(parseInt(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <button
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            disabled={!selectedFile}
          >
            Start Tracking Job 🚀
          </button>
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { uploadVideoApi, createJobApi } from '../api/client';

export default function UploadIngest({ setActivePage, setSelectedJobId, setUploadedVideoUrl }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [confThreshold, setConfThreshold] = useState(0.25);
  const [cosineDist, setCosineDist] = useState(0.20);
  const [maxAge, setMaxAge] = useState(30);
  const [nInit, setNInit] = useState(1);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock video metadata
  const videoMeta = {
    filename: selectedFile ? selectedFile.name : 'crossroad_traffic_cam_04.mp4',
    resolution: '1920×1080',
    framerate: '60 FPS',
    duration: '42.5s',
    size: selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB` : '84.2 MB',
    totalFrames: '2,550 frames',
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (previewUrl && setUploadedVideoUrl) {
        setUploadedVideoUrl(previewUrl);
      }

      // 1. Upload video file asset if user picked a file
      let videoRecord = { id: 'vid-default' };
      if (selectedFile) {
        videoRecord = await uploadVideoApi(selectedFile);
      }

      // 2. Dispatch tracking job to ML backend
      const jobRecord = await createJobApi({
        videoId: videoRecord.id,
        confThreshold,
        cosineDist,
        maxAge,
        nInit,
      });

      setIsSubmitting(false);
      if (setSelectedJobId) setSelectedJobId(jobRecord.id);
      setActivePage('workspace');
    } catch (err) {
      setIsSubmitting(false);
      alert('Something went wrong: ' + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', letterSpacing: '0.1em', fontWeight: 600 }}>
          UPLOAD & CONFIGURE
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            Upload Video & Configure Tracking
          </h1>
          <div style={{ display: 'flex', gap: '10px' }}>
            <span className="badge badge-cyan">Mode: Real-Time Tracking</span>
            <span className="badge badge-emerald">Ready</span>
          </div>
        </div>
      </div>

      {/* 2 Step Cards Layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
        gap: '24px',
        alignItems: 'start'
      }}>
        {/* Step 1: Video Source Asset Card */}
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="badge badge-cyan font-mono" style={{ fontSize: '0.65rem' }}>STEP 01</span>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                1. Select Video
              </h2>
            </div>
            <span className="badge badge-emerald">• Ready</span>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            Your video is ready for tracking. You can replace it below.
          </p>

          {/* Video Preview Box */}
          <div style={{
            position: 'relative',
            borderRadius: '8px',
            overflow: 'hidden',
            border: '1px solid var(--border-strong)',
            backgroundColor: '#000',
            aspectRatio: '16/9',
            display: 'flex',
            alignItems: 'center',
            justify: 'center'
          }}>
            {previewUrl ? (
              <video
                src={previewUrl}
                controls
                muted
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <div style={{
                width: '100%',
                height: '100%',
                background: 'linear-gradient(180deg, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.95) 100%), #050505',
                display: 'flex',
                flexDirection: 'column',
                justify: 'space-between',
                padding: '16px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', background: 'rgba(0,0,0,0.6)', padding: '2px 8px', borderRadius: '4px' }}>
                    CAM_04 // Night Traffic
                  </span>
                  <span className="badge badge-emerald">• SYNCED</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <div>
                    <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {videoMeta.filename}
                    </div>
                    <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {videoMeta.totalFrames}
                    </div>
                  </div>
                  <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    1080p • 60 FPS
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Metadata Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '8px',
            backgroundColor: 'var(--bg-elevated)',
            padding: '12px',
            borderRadius: '6px',
            textAlign: 'center'
          }}>
            <div>
              <div className="font-mono" style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>RESOLUTION</div>
              <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{videoMeta.resolution}</div>
            </div>
            <div>
              <div className="font-mono" style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>FRAMERATE</div>
              <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{videoMeta.framerate}</div>
            </div>
            <div>
              <div className="font-mono" style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>DURATION</div>
              <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{videoMeta.duration}</div>
            </div>
            <div>
              <div className="font-mono" style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>SIZE</div>
              <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{videoMeta.size}</div>
            </div>
          </div>

          {/* Drag & Drop Replace Zone */}
          <label style={{
            border: '2px dashed var(--border-strong)',
            borderRadius: '8px',
            padding: '24px',
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            transition: 'border-color 0.2s ease',
            display: 'block'
          }}>
            <input type="file" accept="video/*" onChange={handleFileChange} style={{ display: 'none' }} />
            <div style={{ fontSize: '1.6rem', color: 'var(--accent-cyan)', marginBottom: '8px' }}>☁️</div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              Replace Video File
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Drag and drop replacement video here or click to browse
            </div>
          </label>
        </div>

        {/* Step 2: Pipeline Parameters Card */}
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="badge badge-cyan font-mono" style={{ fontSize: '0.65rem' }}>STEP 02</span>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                2. Tracking Settings
              </h2>
            </div>
            <span className="badge badge-cyan">YOLOv8 + DeepSORT</span>
          </div>

          <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            Configure object detection sensitivity and spatial-temporal tracking association.
          </p>

          {/* Slider 1: Confidence Threshold */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: 'var(--bg-elevated)', padding: '16px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                Detection Sensitivity
              </label>
              <span className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {confThreshold.toFixed(2)} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>/ 1.00</span>
              </span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.95"
              step="0.05"
              value={confThreshold}
              onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
              style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer', width: '100%' }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Minimum detection confidence score to register an object bounding box. Higher values detect fewer objects but with more certainty.
            </span>
          </div>

          {/* Slider 2: Tracking Strictness */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: 'var(--bg-elevated)', padding: '16px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                Tracking Strictness
              </label>
              <span className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {cosineDist.toFixed(2)} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>dist</span>
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.05"
              value={cosineDist}
              onChange={(e) => setCosineDist(parseFloat(e.target.value))}
              style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer', width: '100%' }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Appearance Re-ID matching threshold for identity persistence.
            </span>
          </div>

          {/* Advanced Tuning Accordion */}
          <div style={{ border: '1px solid var(--border-subtle)', borderRadius: '6px', overflow: 'hidden' }}>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{
                width: '100%',
                padding: '12px 16px',
                background: 'var(--bg-elevated)',
                border: 'none',
                color: 'var(--text-primary)',
                fontWeight: 600,
                fontSize: '0.82rem',
                display: 'flex',
                justify: 'space-between',
                alignItems: 'center',
                cursor: 'pointer'
              }}
            >
              <span>{showAdvanced ? '▼' : '▶'} Advanced Tuning (Max Track Age, Initial Hits)</span>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Default preset</span>
            </button>
            {showAdvanced && (
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg-card)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Max Track Age (frames):</span>
                  <span className="font-mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{maxAge}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Initial Hits Required:</span>
                  <span className="font-mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{nInit}</span>
                </div>
              </div>
            )}
          </div>

          {/* Rate & Queue Estimate */}
          <div style={{
            display: 'flex',
            justify: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--bg-elevated)',
            padding: '12px 16px',
            borderRadius: '6px',
            fontSize: '0.8rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--accent-emerald)' }}>⚡</span>
              <span>Estimated speed: <strong>~30 FPS</strong></span>
            </div>
            <span className="badge badge-emerald font-mono">EST: 85S</span>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="btn btn-cyan"
            style={{
              width: '100%',
              padding: '14px',
              fontSize: '0.95rem',
              letterSpacing: '0.02em',
              marginTop: '4px'
            }}
          >
            {isSubmitting ? (
              <span>⏳ Dispatching Job to Queue...</span>
            ) : (
              <span>🚀 Start Tracking →</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

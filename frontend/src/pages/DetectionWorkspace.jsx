import React, { useState, useRef, useEffect } from 'react';

export default function DetectionWorkspace({ selectedJobId, uploadedVideoUrl }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(1);
  const [totalFrames, setTotalFrames] = useState(2550);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState(null);
  const [jobStatus, setJobStatus] = useState('PROCESSING');
  const videoRef = useRef(null);

  // Poll backend for annotated video output
  useEffect(() => {
    let timer;
    const checkOutput = async () => {
      if (!selectedJobId) return;
      const targetUrl = `http://localhost:8000/uploads/outputs/${selectedJobId}_annotated.mp4`;
      try {
        const res = await fetch(targetUrl, { method: 'HEAD' });
        if (res.ok) {
          setAnnotatedVideoUrl(targetUrl);
          setJobStatus('COMPLETED');
          if (timer) clearInterval(timer);
        } else {
          // Check backend job endpoint status
          const jobRes = await fetch(`http://localhost:8000/api/v1/jobs/${selectedJobId}`);
          if (jobRes.ok) {
            const data = await jobRes.json();
            setJobStatus(data.status || 'PROCESSING');
          }
        }
      } catch (err) {
        // Mock fallback check
      }
    };

    checkOutput();
    timer = setInterval(checkOutput, 2000);
    return () => clearInterval(timer);
  }, [selectedJobId]);

  const activeVideoSrc = annotatedVideoUrl || uploadedVideoUrl;

  // Overlay Toggles
  const [overlays, setOverlays] = useState({
    boundingBoxes: true,
    trackIds: true,
    confidence: true,
    trajectory: false,
  });

  // Object Class Filter Chips
  const [classes, setClasses] = useState({
    person: { checked: true, count: 14 },
    vehicle: { checked: true, count: 8 },
    bus: { checked: true, count: 2 },
    bicycle: { checked: false, count: 1 },
  });

  const toggleOverlay = (key) => {
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleClass = (key) => {
    setClasses((prev) => ({
      ...prev,
      [key]: { ...prev[key], checked: !prev[key].checked },
    }));
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
        setIsPlaying(true);
      } else {
        videoRef.current.pause();
        setIsPlaying(false);
      }
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleSpeedChange = (spd) => {
    setPlaybackSpeed(spd);
    if (videoRef.current) {
      videoRef.current.playbackRate = spd;
    }
  };

  const handleFrameStep = (delta) => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
      const fps = 30;
      videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime + (delta / fps));
    } else {
      setCurrentFrame((prev) => Math.min(totalFrames, Math.max(1, prev + delta)));
    }
  };

  const handleScrubberChange = (val) => {
    setCurrentFrame(val);
    if (videoRef.current && videoRef.current.duration) {
      videoRef.current.currentTime = (val / totalFrames) * videoRef.current.duration;
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current && videoRef.current.duration) {
      const progressRatio = videoRef.current.currentTime / videoRef.current.duration;
      const frame = Math.floor(progressRatio * totalFrames);
      setCurrentFrame(Math.max(1, frame));
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current && videoRef.current.duration) {
      const estimatedFrames = Math.floor(videoRef.current.duration * 30);
      setTotalFrames(estimatedFrames || 2550);
    }
  };

  // Convert frame number to mm:ss.ms
  const formatTime = (frame) => {
    const totalSeconds = (frame / 30);
    const mins = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const secs = String(Math.floor(totalSeconds % 60)).padStart(2, '0');
    const ms = String(Math.floor((totalSeconds % 1) * 100)).padStart(2, '0');
    return `${mins}:${secs}.${ms}`;
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '240px 1fr 280px',
      gap: '16px',
      height: 'calc(100vh - 92px)',
      overflow: 'hidden'
    }}>
      {/* LEFT PANEL: Overlays, Filters & Track States */}
      <div className="glass-card" style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        overflowY: 'auto'
      }}>
        {/* Active Sequence Header */}
        <div>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            CURRENT VIDEO
          </div>
          <div className="font-mono" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
            crossroad_traffic_cam_04.mp4
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            1920x1080 • 60 FPS • 42.5s
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Display Overlays Section */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              SHOW ON VIDEO
            </span>
            <span className="badge badge-cyan font-mono" style={{ fontSize: '0.62rem' }}>4 Active</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { id: 'boundingBoxes', label: 'Bounding Boxes', icon: '⊡' },
              { id: 'trackIds', label: 'Object ID Labels', icon: '🏷️' },
              { id: 'confidence', label: 'Confidence Scores', icon: '%' },
              { id: 'trajectory', label: 'Motion Path', icon: '📈' },
            ].map((item) => (
              <label
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justify: 'space-between',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  backgroundColor: '#000000',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                  color: overlays[item.id] ? 'var(--text-primary)' : 'var(--text-muted)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
                <input
                  type="checkbox"
                  checked={overlays[item.id]}
                  onChange={() => toggleOverlay(item.id)}
                  style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
                />
              </label>
            ))}
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Object Classes Filter Chips */}
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '10px' }}>
            OBJECT TYPES
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { id: 'person', label: 'Person', count: 14 },
              { id: 'vehicle', label: 'Vehicle', count: 8 },
              { id: 'bus', label: 'Bus / Truck', count: 2 },
              { id: 'bicycle', label: 'Bicycle', count: 1 },
            ].map((cls) => {
              const active = classes[cls.id].checked;
              return (
                <button
                  key={cls.id}
                  onClick={() => toggleClass(cls.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justify: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: active ? '1px solid var(--border-cyan)' : '1px solid var(--border-subtle)',
                    backgroundColor: active ? 'rgba(0, 229, 255, 0.1)' : '#000000',
                    color: active ? 'var(--accent-cyan)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: active ? 600 : 400,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{active ? '☑' : '☐'}</span>
                    <span>{cls.label}</span>
                  </div>
                  <span className="badge badge-cyan font-mono" style={{ fontSize: '0.65rem' }}>
                    {cls.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Track States Footer */}
        <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
            TRACKING STATUS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', textAlign: 'center' }}>
            <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>18</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-emerald)' }}>ACTIVE</div>
            </div>
            <div style={{ backgroundColor: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-amber)' }}>4</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-amber)' }}>NEW</div>
            </div>
            <div style={{ backgroundColor: 'rgba(244, 63, 94, 0.12)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-rose)' }}>3</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-rose)' }}>LOST</div>
            </div>
          </div>
        </div>
      </div>

      {/* CENTER PANEL: Video Canvas & Interactive Scrubber Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
        {/* Telemetry Bar */}
        <div className="glass-card" style={{ padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            crossroad_traffic_cam_04.mp4
          </div>
          <div className="font-mono" style={{ display: 'flex', gap: '16px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            <span>⚡ 29.84 FPS</span>
            <span>HD 1080p</span>
            <span style={{ color: 'var(--accent-cyan)' }}>YOLOv8 + DeepSORT</span>
          </div>
        </div>

        {/* Video Canvas Container */}
        <div style={{
          flex: 1,
          backgroundColor: '#000',
          borderRadius: '10px',
          border: '1px solid var(--border-strong)',
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justify: 'center'
        }}>
          {activeVideoSrc ? (
            <video
              key={activeVideoSrc}
              ref={videoRef}
              src={activeVideoSrc}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              controls
              autoPlay
              loop
              muted
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              backgroundImage: 'url("https://images.unsplash.com/photo-1506521782023-6058fda6888d?q=80&w=1200&auto=format&fit=crop")',
              backgroundSize: 'cover',
              backgroundPosition: 'center'
            }} />
          )}

          {/* OVERLAY LAYER */}
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
            {/* Processing Banner if job is running */}
            {jobStatus === 'PROCESSING' && activeVideoSrc && !annotatedVideoUrl && (
              <div style={{
                position: 'absolute',
                top: '12px',
                left: '50%',
                transform: 'translateX(-50%)',
                backgroundColor: 'rgba(245, 158, 11, 0.9)',
                color: '#040D14',
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '6px 16px',
                borderRadius: '20px',
                boxShadow: '0 0 16px rgba(245, 158, 11, 0.5)',
                zIndex: 10
              }}>
                ⚡YOLOv8 + DeepSORT Processing video...Drawing Bounding Boxes & Tracking IDs
              </div>
            )}

            {/* Dark contrast vignette overlay */}
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0, 0, 0, 0.12)' }} />

            {/* Render mock CSS bounding boxes ONLY in sample preview mode (when no video uploaded) */}
            {!activeVideoSrc && (
              <>
                {/* Bounding Box 1 (#104 Person - Active Highlighted Target) */}
                {overlays.boundingBoxes && classes.person.checked && (
                  <div style={{
                    position: 'absolute',
                    top: '38%',
                    left: '32%',
                    width: '70px',
                    height: '130px',
                    border: '2px solid var(--accent-cyan)',
                    borderRadius: '2px',
                    boxShadow: '0 0 16px rgba(0, 229, 255, 0.6)',
                    backgroundColor: 'rgba(0, 229, 255, 0.08)',
                    pointerEvents: 'auto'
                  }}>
                    <div className="font-mono" style={{
                      position: 'absolute',
                      top: '-22px',
                      left: '-2px',
                      backgroundColor: 'var(--accent-cyan)',
                      color: '#040D14',
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      padding: '2px 6px',
                      borderRadius: '2px',
                      whiteSpace: 'nowrap'
                    }}>
                      #104 Person {overlays.confidence ? '94%' : ''}
                    </div>
                  </div>
                )}

                {/* Bounding Box 2 (#118 Vehicle) */}
                {overlays.boundingBoxes && classes.vehicle.checked && (
                  <div style={{
                    position: 'absolute',
                    top: '48%',
                    left: '52%',
                    width: '120px',
                    height: '80px',
                    border: '2px solid var(--accent-emerald)',
                    borderRadius: '2px',
                    boxShadow: '0 0 12px rgba(16, 185, 129, 0.4)',
                    backgroundColor: 'rgba(16, 185, 129, 0.08)',
                    pointerEvents: 'auto'
                  }}>
                    <div className="font-mono" style={{
                      position: 'absolute',
                      top: '-22px',
                      left: '-2px',
                      backgroundColor: 'var(--accent-emerald)',
                      color: '#040D14',
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      padding: '2px 6px',
                      borderRadius: '2px',
                      whiteSpace: 'nowrap'
                    }}>
                      #118 Vehicle {overlays.confidence ? '89%' : ''}
                    </div>
                  </div>
                )}

                {/* Bounding Box 3 (#108 Bus / Truck) */}
                {overlays.boundingBoxes && classes.bus.checked && (
                  <div style={{
                    position: 'absolute',
                    top: '28%',
                    left: '68%',
                    width: '140px',
                    height: '110px',
                    border: '2px solid var(--accent-amber)',
                    borderRadius: '2px',
                    boxShadow: '0 0 12px rgba(245, 158, 11, 0.4)',
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    pointerEvents: 'auto'
                  }}>
                    <div className="font-mono" style={{
                      position: 'absolute',
                      top: '-22px',
                      left: '-2px',
                      backgroundColor: 'var(--accent-amber)',
                      color: '#040D14',
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      padding: '2px 6px',
                      borderRadius: '2px',
                      whiteSpace: 'nowrap'
                    }}>
                      #108 Bus / Truck {overlays.confidence ? '91%' : ''}
                    </div>
                  </div>
                )}

                {/* Trajectory History Vectors */}
                {overlays.trajectory && (
                  <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                    <path d="M 35% 80% Q 34% 60% 35.5% 44%" stroke="var(--accent-cyan)" strokeWidth="2" strokeDasharray="4 4" fill="none" />
                    <path d="M 70% 30% Q 62% 40% 58% 52%" stroke="var(--accent-emerald)" strokeWidth="2" strokeDasharray="4 4" fill="none" />
                  </svg>
                )}
              </>
            )}

            {/* Timestamp Watermark Overlay */}
            <div className="font-mono" style={{
              position: 'absolute',
              bottom: '12px',
              right: '16px',
              backgroundColor: 'rgba(0,0,0,0.85)',
              border: '1px solid var(--border-subtle)',
              padding: '6px 12px',
              borderRadius: '4px',
              color: 'var(--text-secondary)',
              fontSize: '0.68rem',
              textAlign: 'right'
            }}>
              <div>2023-10-26 14:30:15.45 UTC</div>
              <div style={{ color: 'var(--accent-cyan)' }}>CAM_004 FRAME_012890.jpg</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.6rem' }}>TRACKING PREVIEW</div>
            </div>
          </div>
        </div>

        {/* Video Scrubber & Playback Controls Bar */}
        <div className="glass-card" style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* Progress Timeline Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>00:00.00</span>
            <input
              type="range"
              min="1"
              max={totalFrames}
              value={currentFrame}
              onChange={(e) => handleScrubberChange(parseInt(e.target.value))}
              style={{ flex: 1, accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
            />
            <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>
              {formatTime(currentFrame)} (Frame {currentFrame.toLocaleString()} / {totalFrames.toLocaleString()})
            </span>
          </div>

          {/* Controls Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {/* Play/Pause & Step Buttons */}
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={handlePlayPause}
                className="btn btn-cyan btn-sm"
                style={{ padding: '6px 16px' }}
              >
                {isPlaying ? '⏸ Pause' : '▶ Play'}
              </button>
              <button onClick={() => handleFrameStep(-1)} className="btn btn-secondary btn-sm">
                ← 1 Frame
              </button>
              <button onClick={() => handleFrameStep(1)} className="btn btn-secondary btn-sm">
                1 Frame →
              </button>
            </div>

            {/* Speed Selector Buttons */}
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '4px' }}>SPEED:</span>
              {[0.5, 1.0, 2.0].map((spd) => (
                <button
                  key={spd}
                  onClick={() => handleSpeedChange(spd)}
                  className={`btn btn-sm ${playbackSpeed === spd ? 'btn-cyan' : 'btn-secondary'}`}
                  style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: Job Summary, Artifact Export & Active Target Inspector */}
      <div className="glass-card" style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        overflowY: 'auto'
      }}>
        {/* Job Summary Header */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              TRACKING SUMMARY
            </span>
            <span className="badge badge-emerald">• COMPLETED</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <div>
              <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                38
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>OBJECTS TRACKED</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                98.2%
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Accuracy</div>
            </div>
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Primary Export Artifacts Buttons */}
        <div>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.08em' }}>
            DOWNLOAD RESULTS
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              onClick={() => alert('Downloading Annotated Video MP4 artifact...')}
              className="btn btn-cyan"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '10px' }}
            >
              📥 Download Tracked Video
            </button>
            <button
              onClick={() => alert('Exporting MOT Results TXT file...')}
              className="btn btn-outline-cyan"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '8px' }}
            >
              📄 Download Tracking Data
            </button>
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Pipeline Hyperparameters */}
        <div>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.08em' }}>
            TRACKING SETTINGS USED
          </div>

          <div className="font-mono" style={{
            fontSize: '0.72rem',
            backgroundColor: 'var(--bg-elevated)',
            padding: '10px',
            borderRadius: '6px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            color: 'var(--text-secondary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Model:</span> <span style={{ color: 'var(--text-primary)' }}>yolov8m.pt</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Sensitivity:</span> <span style={{ color: 'var(--accent-cyan)' }}>0.50</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Match Strictness:</span> <span style={{ color: 'var(--accent-cyan)' }}>0.20</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Memory (frames):</span> <span style={{ color: 'var(--text-primary)' }}>30 frames</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Min Detections:</span> <span style={{ color: 'var(--text-primary)' }}>3 frames</span>
            </div>
          </div>
        </div>

        {/* Active Target Inspector */}
        <div style={{
          marginTop: 'auto',
          backgroundColor: 'rgba(0, 229, 255, 0.05)',
          border: '1px solid var(--border-cyan)',
          borderRadius: '8px',
          padding: '12px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>SELECTED OBJECT</span>
            <span className="badge badge-cyan">#104 • Confirmed</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.75rem' }}>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>TYPE</div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Person</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>CONFIDENCE</div>
              <div className="font-mono" style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>94.2%</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>DURATION</div>
              <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>142 frames (4.7s)</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>STATUS</div>
              <div style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>Tracking Active</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

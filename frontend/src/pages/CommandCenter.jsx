import React, { useState, useEffect } from 'react';

export default function CommandCenter({ setActivePage, setSelectedJobId }) {
  const [jobs, setJobs] = useState([
    {
      id: 'job-101',
      videoName: 'crossroad_traffic_cam_04.mp4',
      status: 'COMPLETED',
      progress: 100,
      totalTracks: 38,
      speed: '29.8 FPS',
      submitted: '12 mins ago',
    },
    {
      id: 'job-102',
      videoName: 'mot17_overhead_plaza.mp4',
      status: 'PROCESSING',
      progress: 68,
      totalTracks: 24,
      speed: '31.2 FPS',
      submitted: '2 mins ago',
    },
    {
      id: 'job-103',
      videoName: 'night_highway_junction.mp4',
      status: 'COMPLETED',
      progress: 100,
      totalTracks: 52,
      speed: '28.4 FPS',
      submitted: '1 hour ago',
    },
    {
      id: 'job-104',
      videoName: 'subway_entrance_concourse.avi',
      status: 'FAILED',
      progress: 14,
      totalTracks: '-',
      speed: '-',
      submitted: '3 hours ago',
      error: 'CUDA Out Of Memory during feature extraction',
    },
  ]);

  // Fetch real jobs from backend if server is running
  useEffect(() => {
    fetch('http://localhost:8000/api/v1/jobs')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          // Map backend jobs format if available
        }
      })
      .catch(() => {
        // Silently fallback to structured mock telemetry data
      });
  }, []);

  const handleActionClick = (job) => {
    if (setSelectedJobId) setSelectedJobId(job.id);
    if (job.status === 'COMPLETED' || job.status === 'PROCESSING') {
      setActivePage('workspace');
    } else {
      alert(`Error details for ${job.videoName}:\n\n${job.error || 'Pipeline execution halted prematurely.'}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between',
        paddingBottom: '8px',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Multi-Object Tracking Operations
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Manage DeepSORT pipeline jobs, inspect tracking fidelity, and evaluate MOT17 benchmark sequences.
          </p>
        </div>
        <button
          onClick={() => setActivePage('ingest')}
          className="btn btn-cyan"
          style={{ padding: '12px 24px', fontSize: '0.9rem' }}
        >
          <span style={{ fontSize: '1.1rem' }}>+</span>
          <span>New Tracking Job</span>
        </button>
      </div>

      {/* 4 Top Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px'
      }}>
        {/* Metric 1 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              VIDEOS UPLOADED
            </span>
            <span style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>🎬</span>
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.1, marginBottom: '8px' }}>
            14
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>3 active sequences</span>
            <span style={{ color: 'var(--accent-cyan)' }}>Uploaded</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              TRACKING RUNS
            </span>
            <span style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>🔀</span>
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.1, marginBottom: '8px' }}>
            27
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>Total Lifetime runs</span>
            <span style={{ color: 'var(--text-secondary)' }}>DeepSORT</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              COMPLETED
            </span>
            <span style={{ color: 'var(--accent-emerald)', fontSize: '1.1rem' }}>✓</span>
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--accent-emerald)', lineHeight: 1.1, marginBottom: '8px' }}>
            24
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>88.9% success rate</span>
            <span style={{ color: 'var(--accent-emerald)' }}>Good</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              FAILED
            </span>
            <span style={{ color: 'var(--accent-rose)', fontSize: '1.1rem' }}>⚠️</span>
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--accent-rose)', lineHeight: 1.1, marginBottom: '8px' }}>
            1
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>Memory error</span>
            <span style={{ color: 'var(--accent-rose)' }}>Memory Error</span>
          </div>
        </div>
      </div>

      {/* Recent Tracking Jobs Table Container */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.1rem', color: 'var(--accent-cyan)' }}>📑</span>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Recent Tracking Jobs
            </h2>
            <span className="badge badge-cyan">{jobs.length} runs</span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary btn-sm">⚙ Filter</button>
            <button className="btn btn-secondary btn-sm">↻ Refresh</button>
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000' }}>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>VIDEO NAME</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>STATUS</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>PROGRESS</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>OBJECTS FOUND</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>SPEED</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em' }}>STARTED</th>
                <th className="font-mono" style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.7rem', letterSpacing: '0.06em', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000', transition: 'background-color 0.15s ease' }}>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>📹</span>
                      <span className="font-mono" style={{ fontSize: '0.82rem' }}>{job.videoName}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span className={`badge badge-${job.status.toLowerCase()}`}>
                      • {job.status}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', minWidth: '140px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '6px', backgroundColor: '#141418', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${job.progress}%`,
                          backgroundColor: job.status === 'FAILED' ? 'var(--accent-rose)' : job.status === 'PROCESSING' ? 'var(--accent-amber)' : 'var(--accent-emerald)',
                          transition: 'width 0.3s ease'
                        }}></div>
                      </div>
                      <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', width: '32px' }}>
                        {job.progress}%
                      </span>
                    </div>
                  </td>
                  <td className="font-mono" style={{ padding: '14px 16px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {job.totalTracks !== '-' ? `${job.totalTracks} tracks` : '-'}
                  </td>
                  <td className="font-mono" style={{ padding: '14px 16px', color: 'var(--text-secondary)' }}>
                    {job.speed}
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {job.submitted}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleActionClick(job)}
                      className={job.status === 'COMPLETED' ? 'btn btn-cyan btn-sm' : job.status === 'PROCESSING' ? 'btn btn-outline-cyan btn-sm' : 'btn btn-secondary btn-sm'}
                      style={{ padding: '6px 14px' }}
                    >
                      {job.status === 'COMPLETED' ? 'View Results →' : job.status === 'PROCESSING' ? 'View Progress →' : 'View Error Log'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useMemo } from 'react';

export default function AnalyticsCharts({ jobs = [], jobStats = {} }) {
  const [hoveredLifespan, setHoveredLifespan] = useState(null);
  const [hoveredConfidence, setHoveredConfidence] = useState(null);
  const [hoveredRun, setHoveredRun] = useState(null);

  /* -------------------------------------------------------------------------
   * Data Aggregation across all loaded job statistics
   * ------------------------------------------------------------------------- */
  const aggregatedData = useMemo(() => {
    const allTracks = [];
    const runPerformance = [];

    // Sort jobs chronologically (oldest to newest for trend line)
    const sortedJobs = [...jobs]
      .filter((j) => j.status === 'COMPLETED' && jobStats[j.id])
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    sortedJobs.forEach((job) => {
      const stats = jobStats[job.id];
      if (!stats) return;

      if (stats.fps && stats.fps > 0) {
        runPerformance.push({
          id: job.id,
          shortId: job.id.slice(0, 8),
          fps: Number(stats.fps.toFixed(1)),
          tracks: stats.total_tracks || 0,
          date: new Date(job.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }),
        });
      }

      if (Array.isArray(stats.tracks)) {
        stats.tracks.forEach((t) => allTracks.push(t));
      }
    });

    // 1. Lifespan histogram bins (in frames)
    const lifespanBins = [
      { label: '1–15f', min: 1, max: 15, count: 0 },
      { label: '16–30f', min: 16, max: 30, count: 0 },
      { label: '31–60f', min: 31, max: 60, count: 0 },
      { label: '61–120f', min: 61, max: 120, count: 0 },
      { label: '121–240f', min: 121, max: 240, count: 0 },
      { label: '240f+', min: 241, max: Infinity, count: 0 },
    ];

    allTracks.forEach((track) => {
      const f = track.frames || 0;
      const bin = lifespanBins.find((b) => f >= b.min && f <= b.max);
      if (bin) bin.count += 1;
    });

    // 2. Confidence spread bins (0.0 to 1.0)
    const confidenceBins = [
      { label: '20–35%', min: 0.2, max: 0.35, count: 0 },
      { label: '36–50%', min: 0.351, max: 0.5, count: 0 },
      { label: '51–65%', min: 0.501, max: 0.65, count: 0 },
      { label: '66–80%', min: 0.651, max: 0.8, count: 0 },
      { label: '81–95%', min: 0.801, max: 0.95, count: 0 },
      { label: '96–100%', min: 0.951, max: 1.0, count: 0 },
    ];

    let totalConf = 0;
    allTracks.forEach((track) => {
      const c = track.avg_confidence || 0;
      totalConf += c;
      const bin = confidenceBins.find((b) => c >= b.min && c <= b.max);
      if (bin) bin.count += 1;
    });

    const avgConfidence = allTracks.length > 0 ? (totalConf / allTracks.length) * 100 : 0;
    const avgFps =
      runPerformance.length > 0
        ? runPerformance.reduce((s, r) => s + r.fps, 0) / runPerformance.length
        : 0;

    return {
      totalTracks: allTracks.length,
      lifespanBins,
      confidenceBins,
      avgConfidence,
      runPerformance,
      avgFps,
    };
  }, [jobs, jobStats]);

  const { lifespanBins, confidenceBins, avgConfidence, runPerformance, avgFps, totalTracks } =
    aggregatedData;

  const maxLifespanCount = Math.max(1, ...lifespanBins.map((b) => b.count));
  const maxConfCount = Math.max(1, ...confidenceBins.map((b) => b.count));
  const maxFps = Math.max(10, ...runPerformance.map((r) => r.fps));

  if (totalTracks === 0 && runPerformance.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
            TRACKING ANALYTICS & SYSTEM PERFORMANCE
          </h2>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            Real-time identity distribution, confidence spreads, and FPS throughput trends across runs
          </div>
        </div>
        <span className="badge badge-cyan font-mono" style={{ fontSize: '0.65rem' }}>
          {totalTracks.toLocaleString()} Total Identities Analyzed
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        {/* =========================================================================
         * Chart 1: Track Lifespan Histogram
         * ========================================================================= */}
        <div className="glass-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Track Lifespan Distribution
            </span>
            <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)' }}>
              Frame Persistence
            </span>
          </div>

          <div style={{ height: '140px', position: 'relative', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '22px' }}>
            {lifespanBins.map((bin, idx) => {
              const heightPct = Math.round((bin.count / maxLifespanCount) * 100);
              const isHovered = hoveredLifespan === idx;
              return (
                <div
                  key={bin.label}
                  style={{
                    flex: 1,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'flex-end',
                    alignItems: 'center',
                    cursor: 'pointer',
                    position: 'relative',
                  }}
                  onMouseEnter={() => setHoveredLifespan(idx)}
                  onMouseLeave={() => setHoveredLifespan(null)}
                >
                  {isHovered && (
                    <div
                      className="font-mono"
                      style={{
                        position: 'absolute',
                        top: '-24px',
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border-cyan)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '0.65rem',
                        color: 'var(--accent-cyan)',
                        whiteSpace: 'nowrap',
                        zIndex: 10,
                      }}
                    >
                      {bin.count} tracks ({totalTracks ? ((bin.count / totalTracks) * 100).toFixed(0) : 0}%)
                    </div>
                  )}

                  <div
                    style={{
                      width: '100%',
                      height: `${Math.max(4, heightPct)}%`,
                      backgroundColor: isHovered ? 'var(--accent-cyan)' : 'rgba(0, 229, 255, 0.45)',
                      borderRadius: '4px 4px 1px 1px',
                      transition: 'all 0.2s ease',
                      border: '1px solid rgba(0, 229, 255, 0.6)',
                      boxShadow: isHovered ? '0 0 12px rgba(0, 229, 255, 0.5)' : 'none',
                    }}
                  />

                  <div
                    className="font-mono"
                    style={{
                      position: 'absolute',
                      bottom: 0,
                      fontSize: '0.62rem',
                      color: isHovered ? 'var(--accent-cyan)' : 'var(--text-muted)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {bin.label}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
            <span>Lost early (&lt;30f): <strong style={{ color: 'var(--text-primary)' }}>{lifespanBins[0].count + lifespanBins[1].count}</strong></span>
            <span>Stable tracks (&gt;60f): <strong style={{ color: 'var(--accent-emerald)' }}>{lifespanBins.slice(3).reduce((s, b) => s + b.count, 0)}</strong></span>
          </div>
        </div>

        {/* =========================================================================
         * Chart 2: Detection Confidence Spread
         * ========================================================================= */}
        <div className="glass-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Detection Confidence Spread
            </span>
            <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--accent-emerald)' }}>
              Avg: {avgConfidence.toFixed(1)}%
            </span>
          </div>

          <div style={{ height: '140px', position: 'relative', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '22px' }}>
            {confidenceBins.map((bin, idx) => {
              const heightPct = Math.round((bin.count / maxConfCount) * 100);
              const isHovered = hoveredConfidence === idx;
              return (
                <div
                  key={bin.label}
                  style={{
                    flex: 1,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'flex-end',
                    alignItems: 'center',
                    cursor: 'pointer',
                    position: 'relative',
                  }}
                  onMouseEnter={() => setHoveredConfidence(idx)}
                  onMouseLeave={() => setHoveredConfidence(null)}
                >
                  {isHovered && (
                    <div
                      className="font-mono"
                      style={{
                        position: 'absolute',
                        top: '-24px',
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--accent-emerald)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '0.65rem',
                        color: 'var(--accent-emerald)',
                        whiteSpace: 'nowrap',
                        zIndex: 10,
                      }}
                    >
                      {bin.count} tracks
                    </div>
                  )}

                  <div
                    style={{
                      width: '100%',
                      height: `${Math.max(4, heightPct)}%`,
                      backgroundColor: isHovered ? 'var(--accent-emerald)' : 'rgba(16, 185, 129, 0.45)',
                      borderRadius: '4px 4px 1px 1px',
                      transition: 'all 0.2s ease',
                      border: '1px solid rgba(16, 185, 129, 0.6)',
                      boxShadow: isHovered ? '0 0 12px rgba(16, 185, 129, 0.5)' : 'none',
                    }}
                  />

                  <div
                    className="font-mono"
                    style={{
                      position: 'absolute',
                      bottom: 0,
                      fontSize: '0.60rem',
                      color: isHovered ? 'var(--accent-emerald)' : 'var(--text-muted)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {bin.label}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
            <span>High confidence (&gt;65%): <strong style={{ color: 'var(--accent-emerald)' }}>{confidenceBins.slice(3).reduce((s, b) => s + b.count, 0)}</strong></span>
            <span>Threshold: <strong style={{ color: 'var(--text-primary)' }}>&ge; 0.25</strong></span>
          </div>
        </div>

        {/* =========================================================================
         * Chart 3: FPS Throughput Over Runs
         * ========================================================================= */}
        <div className="glass-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              FPS Throughput Trend
            </span>
            <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--accent-violet)' }}>
              Mean: {avgFps.toFixed(1)} FPS
            </span>
          </div>

          <div style={{ height: '140px', position: 'relative', paddingBottom: '22px' }}>
            {runPerformance.length === 0 ? (
              <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'center', paddingTop: '40px' }}>
                Complete a tracking run to populate FPS telemetry.
              </div>
            ) : runPerformance.length === 1 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <span className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-violet)' }}>
                  {runPerformance[0].fps} FPS
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  Run #{runPerformance[0].shortId} ({runPerformance[0].date})
                </span>
              </div>
            ) : (
              <svg width="100%" height="100%" viewBox="0 0 300 118" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                {/* Average FPS reference line */}
                {(() => {
                  const avgY = 110 - (avgFps / (maxFps * 1.15)) * 100;
                  return (
                    <line
                      x1="0"
                      y1={avgY}
                      x2="300"
                      y2={avgY}
                      stroke="rgba(167, 139, 250, 0.3)"
                      strokeDasharray="4 4"
                      strokeWidth="1"
                    />
                  );
                })()}

                {/* Performance curve polyline */}
                {(() => {
                  const points = runPerformance.map((r, i) => {
                    const x = (i / (runPerformance.length - 1)) * 300;
                    const y = 110 - (r.fps / (maxFps * 1.15)) * 100;
                    return `${x},${y}`;
                  });

                  return (
                    <>
                      {/* Area gradient under line */}
                      <defs>
                        <linearGradient id="fpsGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="rgba(167, 139, 250, 0.4)" />
                          <stop offset="100%" stopColor="rgba(167, 139, 250, 0.0)" />
                        </linearGradient>
                      </defs>
                      <polygon
                        points={`0,110 ${points.join(' ')} 300,110`}
                        fill="url(#fpsGradient)"
                      />
                      <polyline
                        fill="none"
                        stroke="var(--accent-violet)"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={points.join(' ')}
                      />
                      {/* Interactive dots */}
                      {runPerformance.map((r, i) => {
                        const x = (i / (runPerformance.length - 1)) * 300;
                        const y = 110 - (r.fps / (maxFps * 1.15)) * 100;
                        const isHovered = hoveredRun === i;
                        return (
                          <g key={r.id}>
                            <circle
                              cx={x}
                              cy={y}
                              r={isHovered ? 5 : 3.5}
                              fill="var(--accent-violet)"
                              stroke="#040D14"
                              strokeWidth="1.5"
                              style={{ cursor: 'pointer', transition: 'all 0.15s ease' }}
                              onMouseEnter={() => setHoveredRun(i)}
                              onMouseLeave={() => setHoveredRun(null)}
                            />
                          </g>
                        );
                      })}
                    </>
                  );
                })()}
              </svg>
            )}

            {hoveredRun !== null && runPerformance[hoveredRun] && (
              <div
                className="font-mono"
                style={{
                  position: 'absolute',
                  top: '-20px',
                  right: '0',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--accent-violet)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.65rem',
                  color: 'var(--accent-violet)',
                  zIndex: 10,
                }}
              >
                Run #{runPerformance[hoveredRun].shortId}: {runPerformance[hoveredRun].fps} FPS
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '4px', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
            <span>Runs: <strong style={{ color: 'var(--text-primary)' }}>{runPerformance.length}</strong></span>
            <span>Peak: <strong style={{ color: 'var(--accent-violet)' }}>{Math.max(0, ...runPerformance.map((r) => r.fps)).toFixed(1)} FPS</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}


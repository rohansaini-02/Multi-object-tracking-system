import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Film,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Zap,
  FileText,
  Video,
  Copy,
  Trash2,
  Lightbulb,
  RotateCcw,
  RefreshCw,
} from 'lucide-react';
import { getJobsApi, getVideosApi, getJobResultsApi, deleteJobApi } from '../api/client';
import { formatRelativeTime } from '../utils/format';
import ConfirmModal from '../components/ConfirmModal';
import AnalyticsCharts from '../components/AnalyticsCharts';

export default function CommandCenter({ setActivePage, setSelectedJobId, onCloneJob }) {
  const [jobs, setJobs] = useState([]);
  const [videos, setVideos] = useState([]);
  const [jobStats, setJobStats] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [errorTarget, setErrorTarget] = useState(null);

  // Tracks which jobs already have statistics loaded (keyed by id + status) so
  // the polling loop does not re-request unchanged results.
  const statsKeyRef = useRef({});

  const loadTelemetry = useCallback(async () => {
    const [jobPayload, videoPayload] = await Promise.all([getJobsApi(), getVideosApi()]);

    const jobList = Array.isArray(jobPayload) ? jobPayload : [];
    const videoList = Array.isArray(videoPayload) ? videoPayload : [];

    setJobs(jobList);
    setVideos(videoList);

    // Only request results for jobs whose status changed since the last poll.
    const pending = jobList.filter((job) => {
      const key = `${job.id}:${job.status}`;
      return statsKeyRef.current[job.id] !== key;
    });

    if (pending.length > 0) {
      const results = await Promise.all(
        pending.map(async (job) => {
          const payload = await getJobResultsApi(job.id);
          return [job.id, payload];
        })
      );

      setJobStats((prev) => {
        const next = { ...prev };
        results.forEach(([jobId, payload]) => {
          if (payload) next[jobId] = payload;
        });
        return next;
      });

      pending.forEach((job) => {
        statsKeyRef.current[job.id] = `${job.id}:${job.status}`;
      });
    }

    setIsLoading(false);
    setIsLive(true);
  }, []);

  // Initial load + live polling of the job queue.
  useEffect(() => {
    let active = true;
    const poll = async () => {
      if (active) await loadTelemetry();
    };
    poll();
    const timer = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [loadTelemetry]);

  const videoNameById = useMemo(() => {
    const map = {};
    videos.forEach((video) => {
      map[video.id] = video.filename;
    });
    return map;
  }, [videos]);

  const rows = useMemo(
    () =>
      jobs.map((job) => {
        const stats = jobStats[job.id];
        return {
          id: job.id,
          rawJob: job,
          videoId: job.video_id,
          videoName: videoNameById[job.video_id] || job.video_id || 'Unknown source',
          status: job.status,
          progress: job.progress ?? 0,
          totalTracks: stats ? stats.total_tracks : '-',
          speed: stats && stats.fps ? `${stats.fps.toFixed(2)} FPS` : '-',
          submitted: formatRelativeTime(job.created_at),
          error: job.error_message,
        };
      }),
    [jobs, jobStats, videoNameById]
  );

  const completedCount = jobs.filter((job) => job.status === 'COMPLETED').length;
  const failedCount = jobs.filter((job) => job.status === 'FAILED').length;
  const activeCount = jobs.filter(
    (job) => job.status === 'PROCESSING' || job.status === 'QUEUED'
  ).length;
  const successRate = jobs.length > 0 ? (completedCount / jobs.length) * 100 : 0;
  const totalObjects = jobs.reduce(
    (sum, job) => sum + (jobStats[job.id]?.total_tracks || 0),
    0
  );
  const lastFailure = jobs.find((job) => job.status === 'FAILED')?.error_message;

  const handleActionClick = (job) => {
    if (setSelectedJobId) setSelectedJobId(job.id);
    if (job.status === 'COMPLETED' || job.status === 'PROCESSING') {
      setActivePage('workspace');
    } else {
      setErrorTarget(job);
    }
  };

  const handleCloneClick = (job) => {
    if (onCloneJob) {
      onCloneJob({
        videoId: job.videoId,
        videoName: job.videoName,
        confThreshold: job.rawJob?.config?.conf_threshold ?? 0.25,
        cosineDist: job.rawJob?.config?.max_cosine_distance ?? 0.20,
        maxAge: job.rawJob?.config?.max_age ?? 30,
        nInit: job.rawJob?.config?.n_init ?? 1,
        reidWeights: job.rawJob?.config?.reid_weights ?? 'base',
      });
    } else if (setActivePage) {
      setActivePage('ingest');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await deleteJobApi(deleteTarget.id);
      setJobs((prev) => prev.filter((j) => j.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setActionError(`Failed to delete run: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
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

      {actionError && (
        <div
          className="font-mono"
          style={{
            padding: '10px 14px',
            backgroundColor: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            borderRadius: '6px',
            color: 'var(--accent-rose)',
            fontSize: '0.75rem',
          }}
        >
          {actionError}
        </div>
      )}

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
            <Film size={18} color="var(--accent-cyan)" />
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.1, marginBottom: '8px' }}>
            {videos.length}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>{activeCount} active sequences</span>
            <span style={{ color: 'var(--accent-cyan)' }}>Uploaded</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              TRACKING RUNS
            </span>
            <Activity size={18} color="var(--accent-cyan)" />
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.1, marginBottom: '8px' }}>
            {jobs.length}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>{totalObjects} objects tracked</span>
            <span style={{ color: 'var(--text-secondary)' }}>DeepSORT</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              COMPLETED
            </span>
            <CheckCircle2 size={18} color="var(--accent-emerald)" />
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--accent-emerald)', lineHeight: 1.1, marginBottom: '8px' }}>
            {completedCount}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>{successRate.toFixed(1)}% success rate</span>
            <span style={{ color: 'var(--accent-emerald)' }}>Good</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.08em', fontWeight: 600 }}>
              FAILED
            </span>
            <AlertTriangle size={18} color="var(--accent-rose)" />
          </div>
          <div className="font-mono" style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--accent-rose)', lineHeight: 1.1, marginBottom: '8px' }}>
            {failedCount}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span>{lastFailure ? 'Pipeline error' : 'No errors'}</span>
            <span style={{ color: failedCount > 0 ? 'var(--accent-rose)' : 'var(--text-secondary)' }}>
              {failedCount > 0 ? 'Needs review' : 'Nominal'}
            </span>
          </div>
        </div>
      </div>

      {/* Option 2: Real-time Tracking Analytics & System Performance Charts */}
      <AnalyticsCharts jobs={jobs} jobStats={jobStats} />

      {/* Active Processing In-Progress Banner */}
      {activeCount > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          background: 'linear-gradient(90deg, rgba(0, 229, 255, 0.12) 0%, rgba(3, 7, 18, 0.95) 100%)',
          border: '1px solid rgba(0, 229, 255, 0.45)',
          borderRadius: '10px',
          boxShadow: '0 0 24px rgba(0, 229, 255, 0.15)',
          gap: '16px',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent-cyan)',
              boxShadow: '0 0 12px var(--accent-cyan)',
              animation: 'pulse 1.5s infinite'
            }} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 800, color: 'var(--text-primary)', fontSize: '0.92rem' }}>
                  Live Tracking Run Active
                </span>
                <span className="badge badge-processing font-mono" style={{ fontSize: '0.68rem' }}>
                  {activeCount} IN FLIGHT
                </span>
              </div>
              <div className="font-mono" style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                Tracking: {rows.find((r) => r.status === 'PROCESSING' || r.status === 'QUEUED')?.videoName || 'Video asset'}
              </div>
            </div>
          </div>
          <button
            className="btn btn-cyan btn-sm"
            style={{ fontWeight: 700, padding: '8px 16px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={() => {
              const active = rows.find((r) => r.status === 'PROCESSING' || r.status === 'QUEUED');
              if (active) handleActionClick(active);
            }}
          >
            <Zap size={14} />
            <span>View Live Processing Progress →</span>
          </button>
        </div>
      )}

      {/* Recent Tracking Jobs Table Container */}
      <div className="glass-card" style={{ padding: '24px', marginTop: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Recent Tracking Jobs
            </h2>
            <span className="badge badge-cyan">{rows.length} runs</span>
            {isLive && (
              <span className="badge badge-emerald font-mono" style={{ fontSize: '0.6rem' }}>● LIVE</span>
            )}
            {activeCount > 0 && (
              <span className="badge badge-processing font-mono" style={{ fontSize: '0.6rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Zap size={10} /> {activeCount} TRACKING
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={loadTelemetry}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={12} /> Refresh
            </button>
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
              {isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading tracking telemetry...
                  </td>
                </tr>
              )}
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No tracking jobs yet. Upload a video to dispatch your first run.
                  </td>
                </tr>
              )}
              {rows.map((job) => (
                <tr key={job.id} style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000', transition: 'background-color 0.15s ease' }}>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Video size={15} color="var(--text-muted)" />
                      <span className="font-mono" style={{ fontSize: '0.82rem' }}>{job.videoName}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span className={`badge badge-${job.status.toLowerCase()}`}>
                      • {job.status === 'PROCESSING' ? `PROCESSING (${job.progress}%)` : job.status}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', minWidth: '150px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '7px', backgroundColor: '#141418', borderRadius: '4px', overflow: 'hidden', border: job.status === 'PROCESSING' ? '1px solid rgba(0, 229, 255, 0.3)' : 'none' }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.max(job.status === 'PROCESSING' ? 5 : 0, job.progress)}%`,
                          background: job.status === 'FAILED'
                            ? 'var(--accent-rose)'
                            : job.status === 'PROCESSING'
                            ? 'linear-gradient(90deg, #00e5ff 0%, #38bdf8 50%, #00e5ff 100%)'
                            : 'var(--accent-emerald)',
                          boxShadow: job.status === 'PROCESSING' ? '0 0 10px rgba(0, 229, 255, 0.6)' : 'none',
                          transition: 'width 0.4s ease'
                        }}></div>
                      </div>
                      <span className="font-mono" style={{ fontSize: '0.75rem', color: job.status === 'PROCESSING' ? 'var(--accent-cyan)' : 'var(--text-secondary)', width: '36px', fontWeight: job.status === 'PROCESSING' ? 700 : 400 }}>
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
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', alignItems: 'center' }}>
                      <button
                        onClick={() => handleActionClick(job)}
                        className={job.status === 'COMPLETED' ? 'btn btn-cyan btn-sm' : job.status === 'PROCESSING' ? 'btn btn-outline-cyan btn-sm' : 'btn btn-secondary btn-sm'}
                        style={{ padding: '4px 10px', fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        {job.status === 'COMPLETED' ? (
                          'View Results →'
                        ) : job.status === 'PROCESSING' ? (
                          <>
                            <Zap size={12} />
                            <span>View Live →</span>
                          </>
                        ) : (
                          'Error Log'
                        )}
                      </button>
                      <button
                        onClick={() => handleCloneClick(job)}
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '4px 8px', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        title="Clone parameters to new run"
                      >
                        <Copy size={12} />
                        <span>Clone</span>
                      </button>
                      <button
                        onClick={() => setDeleteTarget(job)}
                        className="btn btn-sm"
                        style={{
                          padding: '4px 8px',
                          fontSize: '0.72rem',
                          backgroundColor: 'rgba(244, 63, 94, 0.1)',
                          borderColor: 'rgba(244, 63, 94, 0.3)',
                          color: 'var(--accent-rose)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                        title="Delete run and artifacts"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmModal
        isOpen={Boolean(deleteTarget)}
        title="Delete Tracking Run"
        message={`Are you sure you want to delete Run #${deleteTarget?.id?.slice(0, 8)}? All tracked video outputs and MOT data files will be permanently deleted from disk.`}
        confirmLabel="Delete Run"
        isDanger={true}
        isLoading={isDeleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
      />

      {/* Cyber Error Diagnostics Modal */}
      {errorTarget && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-card" style={{
            maxWidth: '560px',
            width: '100%',
            padding: '28px',
            borderRadius: '12px',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            boxShadow: '0 0 30px rgba(244, 63, 94, 0.2)',
            backgroundColor: '#070709',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={24} color="var(--accent-rose)" />
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Tracking Run Diagnostics
                </h3>
                <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-rose)' }}>
                  RUN ID: {errorTarget.id}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.82rem' }}>
              <div style={{ color: 'var(--text-secondary)' }}>
                Target Video: <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{errorTarget.videoName}</span>
              </div>
              <div style={{ color: 'var(--text-secondary)' }}>
                Started: <span style={{ color: 'var(--text-primary)' }}>{errorTarget.submitted}</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
                DETAILED PIPELINE ERROR LOG
              </div>
              <div className="font-mono" style={{
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '12px 14px',
                color: 'var(--accent-rose)',
                fontSize: '0.78rem',
                maxHeight: '160px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                lineHeight: 1.4
              }}>
                {errorTarget.error || errorTarget.rawJob?.error_message || 'Pipeline execution halted prematurely (server restart or unexpected termination).'}
              </div>
            </div>

            <div style={{
              backgroundColor: 'rgba(0, 229, 255, 0.05)',
              border: '1px solid rgba(0, 229, 255, 0.2)',
              borderRadius: '6px',
              padding: '10px 14px',
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.4,
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              <Lightbulb size={16} color="var(--accent-cyan)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ color: 'var(--accent-cyan)' }}>Tip:</strong> If using <code style={{ color: 'var(--accent-cyan)' }}>uvicorn --reload</code>, run with <code style={{ color: 'var(--accent-cyan)' }}>--reload-dir backend --reload-dir ml</code> to prevent upload events from restarting active jobs.
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setErrorTarget(null)}
              >
                Close
              </button>
              <button
                className="btn btn-cyan btn-sm"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                onClick={() => {
                  const target = errorTarget;
                  setErrorTarget(null);
                  handleCloneClick(target);
                }}
              >
                <RotateCcw size={13} />
                <span>Clone & Re-run Job</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

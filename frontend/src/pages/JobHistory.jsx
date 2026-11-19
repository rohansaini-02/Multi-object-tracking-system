import { useState, useEffect, useMemo, useCallback } from 'react';
import { getJobsApi, getVideosApi, getJobResultsApi, deleteJobApi } from '../api/client';
import { formatDateTime } from '../utils/format';
import ConfirmModal from '../components/ConfirmModal';
import { Copy, Trash2 } from 'lucide-react';

export default function JobHistory({ setActivePage, setSelectedJobId, onCloneJob }) {
  const [jobs, setJobs] = useState([]);
  const [videos, setVideos] = useState([]);
  const [jobStats, setJobStats] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState(null);

  const loadHistory = useCallback(async () => {
    const [jobPayload, videoPayload] = await Promise.all([getJobsApi(), getVideosApi()]);

    const jobList = Array.isArray(jobPayload) ? jobPayload : [];
    const videoList = Array.isArray(videoPayload) ? videoPayload : [];

    setJobs(jobList);
    setVideos(videoList);

    const results = await Promise.all(
      jobList.map(async (job) => {
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

    setIsLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    const fetchHistory = async () => {
      if (active) await loadHistory();
    };
    fetchHistory();
    return () => {
      active = false;
    };
  }, [loadHistory]);

  const videoNameById = useMemo(() => {
    const map = {};
    videos.forEach((video) => {
      map[video.id] = video.filename;
    });
    return map;
  }, [videos]);

  const historyList = useMemo(
    () =>
      jobs.map((job) => ({
        id: job.id,
        rawJob: job,
        videoId: job.video_id,
        name: videoNameById[job.video_id] || job.video_id || 'Unknown source',
        status: job.status,
        date: formatDateTime(job.created_at),
        tracks: jobStats[job.id] ? jobStats[job.id].total_tracks : '-',
        fps: jobStats[job.id]?.fps ? `${jobStats[job.id].fps.toFixed(2)} FPS` : '-',
      })),
    [jobs, jobStats, videoNameById]
  );

  const handleViewResults = (item) => {
    if (setSelectedJobId) setSelectedJobId(item.id);
    setActivePage('workspace');
  };

  const handleCloneClick = (item) => {
    if (onCloneJob) {
      onCloneJob({
        videoId: item.videoId,
        videoName: item.name,
        confThreshold: item.rawJob?.config?.conf_threshold ?? 0.25,
        cosineDist: item.rawJob?.config?.max_cosine_distance ?? 0.20,
        maxAge: item.rawJob?.config?.max_age ?? 30,
        nInit: item.rawJob?.config?.n_init ?? 1,
        reidWeights: item.rawJob?.config?.reid_weights ?? 'base',
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)' }}>
          Tracking History
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Historical record of all executed multi-object tracking inference runs.
        </p>
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

      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span className="badge badge-cyan">{historyList.length} RUNS</span>
          <button className="btn btn-secondary btn-sm" onClick={loadHistory}>↻ Refresh</button>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000' }}>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>JOB ID</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>VIDEO NAME</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>STATUS</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>EXECUTION DATE</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>OBJECTS FOUND</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && historyList.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Loading tracking history...
                </td>
              </tr>
            )}
            {!isLoading && historyList.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No tracking runs recorded yet.
                </td>
              </tr>
            )}
            {historyList.map((item) => (
              <tr key={item.id} style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000' }}>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-cyan)' }}>{item.id.slice(0, 8)}</td>
                <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</td>
                <td style={{ padding: '12px' }}>
                  <span className={`badge badge-${item.status.toLowerCase()}`}>• {item.status}</span>
                </td>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>{item.date}</td>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--text-primary)' }}>{item.tracks || '-'}</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', alignItems: 'center' }}>
                    <button
                      onClick={() => handleViewResults(item)}
                      className="btn btn-cyan btn-sm"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                    >
                      View Results →
                    </button>
                    <button
                      onClick={() => handleCloneClick(item)}
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '4px 8px', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      title="Clone parameters to new run"
                    >
                      <Copy size={12} /> Clone
                    </button>
                    <button
                      onClick={() => setDeleteTarget(item)}
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
    </div>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Tag,
  TrendingUp,
  Flame,
  CheckSquare,
  Square,
  Zap,
  AlertTriangle,
  RotateCcw,
  Copy,
  Play,
  Pause,
  Download,
  FileText,
  Trash2,
  Loader2,
  Check,
} from 'lucide-react';
import {
  API_BASE_URL,
  BACKEND_BASE_URL,
  authHeaders,
  getJobApi,
  getJobResultsApi,
  getJobFramesApi,
  getJobsApi,
  getVideosApi,
  downloadJobArtifactApi,
  deleteJobApi,
} from '../api/client';
import { formatDateTime } from '../utils/format';
import ConfirmModal from '../components/ConfirmModal';

/* Palette used to colour-code the tracked identities on the canvas overlay. */
const TRACK_PALETTE = [
  '#00e5ff', '#10b981', '#f59e0b', '#f43f5e', '#a78bfa',
  '#38bdf8', '#fb923c', '#4ade80', '#e879f9', '#facc15',
];

const trackColor = (trackId) =>
  TRACK_PALETTE[Math.abs(Number(trackId) || 0) % TRACK_PALETTE.length];

const STATUS_BADGE = {
  COMPLETED: 'badge badge-completed',
  PROCESSING: 'badge badge-processing',
  QUEUED: 'badge badge-cyan',
  FAILED: 'badge badge-failed',
};

export default function DetectionWorkspace({ selectedJobId, uploadedVideoUrl, onCloneJob, setActivePage }) {
  /* ----------------------------- server state ---------------------------- */
  const [job, setJob] = useState(null);
  const [results, setResults] = useState(null);
  const [frameData, setFrameData] = useState(null);
  const [videoMeta, setVideoMeta] = useState(null);
  const [sourceVideoUrl, setSourceVideoUrl] = useState(null);
  const [resolvedJobId, setResolvedJobId] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  /* ---------------------------- playback state ---------------------------- */
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(1);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  /* ---------------------------- view mode state ---------------------------- */
  const [viewMode, setViewMode] = useState('interactive');

  /* ---------------------------- overlay state ----------------------------- */
  const [overlays, setOverlays] = useState({
    boundingBoxes: true,
    trackIds: true,
    confidence: true,
    trajectory: false,
    heatmap: false,
  });
  const [hiddenTracks, setHiddenTracks] = useState(() => new Set());
  const [selectedTrackId, setSelectedTrackId] = useState(null);

  /* --------------------------- download state ---------------------------- */
  const [downloadState, setDownloadState] = useState({});
  const [downloadMessage, setDownloadMessage] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(null);

  /* ======================= job / artifact data loading ==================== */

  /* When the viewer is opened directly from the sidebar there is no explicit
     job selection, so the most recent run of the account is resolved. */
  useEffect(() => {
    if (selectedJobId) {
      return undefined;
    }

    let cancelled = false;

    const resolveLatestJob = async () => {
      const jobs = await getJobsApi();
      if (cancelled || !Array.isArray(jobs) || jobs.length === 0) return;
      const latest = [...jobs].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];
      if (latest && !cancelled) setResolvedJobId(latest.id);
    };

    resolveLatestJob();

    return () => {
      cancelled = true;
    };
  }, [selectedJobId]);

  const jobId = selectedJobId || resolvedJobId;

  useEffect(() => {
    if (!jobId) {
      return undefined;
    }

    let cancelled = false;
    let stopped = false;
    let timer = null;

    const loadArtifacts = async () => {
      const [resultPayload, framePayload] = await Promise.all([
        getJobResultsApi(jobId),
        getJobFramesApi(jobId),
      ]);
      if (cancelled) return;
      if (resultPayload) setResults(resultPayload);
      if (framePayload) setFrameData(framePayload);
    };

    const loadVideoMeta = async (jobPayload) => {
      const videoPayload = await getVideosApi();
      if (cancelled || !Array.isArray(videoPayload)) return;
      const match = videoPayload.find((video) => video.id === jobPayload?.video_id);
      if (match) setVideoMeta(match);
    };

    const poll = async () => {
      if (stopped || cancelled) return;
      const jobPayload = await getJobApi(jobId);
      if (cancelled) return;

      if (!jobPayload) {
        setLoadError('This tracking job could not be loaded from the backend.');
        stopped = true;
        if (timer) clearInterval(timer);
        return;
      }

      setJob(jobPayload);
      setLoadError(null);
      loadVideoMeta(jobPayload);

      // Stop polling once the pipeline reached a terminal state.
      if (jobPayload.status === 'COMPLETED' || jobPayload.status === 'FAILED') {
        stopped = true;
        if (timer) clearInterval(timer);
        loadArtifacts();
      }
    };

    loadArtifacts();
    poll();

    // Poll the job endpoint every 2 seconds while the job is in flight.
    timer = setInterval(() => {
      if (stopped) {
        clearInterval(timer);
        return;
      }
      poll();
    }, 2000);

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [jobId]);

  /* The source clip is only reachable through an authenticated endpoint, so it
     is fetched as a blob and handed to the <video> element as an object URL. */
  useEffect(() => {
    if (!jobId) return undefined;

    let cancelled = false;
    let objectUrl = null;

    const loadSourceVideo = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/source-video`, {
          headers: authHeaders(),
        });
        if (!res.ok) return;
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = window.URL.createObjectURL(blob);
        setSourceVideoUrl(objectUrl);
      } catch {
        /* the annotated artifact is used instead when the source is unavailable */
      }
    };

    loadSourceVideo();

    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [jobId]);

  /* ============================ derived values ============================ */
  const cleanSourceUrl =
    sourceVideoUrl ||
    (results?.source_video_url ? `${BACKEND_BASE_URL}${results.source_video_url}` : null) ||
    uploadedVideoUrl ||
    null;

  const annotatedVideoUrl =
    results && results.annotated_video_available && results.annotated_video_url
      ? `${BACKEND_BASE_URL}${results.annotated_video_url}`
      : null;

  const isPreRendered = viewMode === 'rendered' && Boolean(annotatedVideoUrl);
  const activeVideoSrc = isPreRendered ? annotatedVideoUrl : (cleanSourceUrl || annotatedVideoUrl || null);

  const frameMap = useMemo(() => {
    const frames = frameData?.frames;
    if (!frames) return {};
    const map = {};
    Object.entries(frames).forEach(([key, value]) => {
      map[Number(key)] = value;
    });
    return map;
  }, [frameData]);

  const sourceFps = Number(frameData?.fps) || Number(videoMeta?.fps) || 0;

  const totalFrames =
    Number(frameData?.total_frames) ||
    Number(results?.total_frames) ||
    Number(videoMeta?.frame_count) ||
    0;

  /* Full per-identity statistics derived from the real MOT frame payload. */
  const trackList = useMemo(() => {
    const frameKeys = Object.keys(frameMap);
    if (frameKeys.length > 0) {
      const map = new Map();
      frameKeys.forEach((key) => {
        const frame = Number(key);
        (frameMap[frame] || []).forEach((det) => {
          let entry = map.get(det.track_id);
          if (!entry) {
            entry = { track_id: det.track_id, frames: 0, confSum: 0, first: frame, last: frame };
            map.set(det.track_id, entry);
          }
          entry.frames += 1;
          entry.confSum += det.confidence;
          entry.first = Math.min(entry.first, frame);
          entry.last = Math.max(entry.last, frame);
        });
      });
      return Array.from(map.values())
        .map((entry) => ({
          track_id: entry.track_id,
          frames: entry.frames,
          avg_confidence: entry.frames ? entry.confSum / entry.frames : 0,
          first: entry.first,
          last: entry.last,
        }))
        .sort((a, b) => b.frames - a.frames);
    }

    return (results?.tracks || []).map((track) => ({
      track_id: track.track_id,
      frames: track.frames,
      avg_confidence: track.avg_confidence,
      first: track.first_frame,
      last: track.last_frame,
    }));
  }, [frameMap, results]);

  useEffect(() => {
    let active = true;
    if (selectedTrackId === null && trackList.length > 0) {
      Promise.resolve().then(() => {
        if (active) setSelectedTrackId(trackList[0].track_id);
      });
    }
    return () => {
      active = false;
    };
  }, [trackList, selectedTrackId]);

  const currentDetections = useMemo(
    () => frameMap[currentFrame] || [],
    [frameMap, currentFrame]
  );

  const statusCounts = useMemo(() => {
    let active = currentDetections.length;
    let fresh = 0;
    let lost = 0;
    trackList.forEach((track) => {
      if (track.first === currentFrame) fresh += 1;
      if (track.last < currentFrame) lost += 1;
    });
    if (active === 0) active = 0;
    return { active, fresh, lost };
  }, [currentDetections, trackList, currentFrame]);

  const selectedTrack = trackList.find((track) => track.track_id === selectedTrackId) || null;

  /* ============================= canvas overlay =========================== */
  const drawOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bounds = canvas.getBoundingClientRect();
    if (bounds.width === 0 || bounds.height === 0) return;

    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(bounds.width * dpr);
    const pixelHeight = Math.round(bounds.height * dpr);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, bounds.width, bounds.height);

    const videoWidth = video.videoWidth;
    const videoHeight = video.videoHeight;
    if (!videoWidth || !videoHeight) return;

    // The video uses object-fit: contain, so the rendered content is letterboxed.
    const scale = Math.min(bounds.width / videoWidth, bounds.height / videoHeight);
    const offsetX = (bounds.width - videoWidth * scale) / 2;
    const offsetY = (bounds.height - videoHeight * scale) / 2;

    // MOT frame ids are 1-based: the frame displayed at video time t is
    // floor(t * fps) + 1. Rounding instead of flooring shifts the overlay up
    // to half a frame forward, so every box is drawn on the wrong frame.
    const frameNumber = sourceFps
      ? Math.floor(video.currentTime * sourceFps) + 1
      : currentFrame;
    const detections = frameMap[frameNumber] || [];

    // Pre-rendered video already has annotations permanently baked into the frames.
    if (isPreRendered) return;

    // Motion path of the selected identity.
    if (overlays.trajectory && selectedTrackId !== null) {
      const points = [];
      for (let frame = frameNumber - 1; frame >= Math.max(1, frameNumber - 60); frame -= 1) {
        const list = frameMap[frame];
        if (!list) continue;
        const det = list.find((item) => item.track_id === selectedTrackId);
        if (det) {
          points.push([
            offsetX + (det.x1 + det.w / 2) * scale,
            offsetY + (det.y1 + det.h / 2) * scale,
          ]);
        }
      }
      points.reverse();
      if (points.length > 1) {
        ctx.save();
        ctx.strokeStyle = trackColor(selectedTrackId);
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(points[0][0], points[0][1]);
        points.slice(1).forEach((point) => ctx.lineTo(point[0], point[1]));
        ctx.stroke();
        ctx.restore();
      }
    }

    // Motion Density / Activity Heatmap overlay
    if (overlays.heatmap && frameMap) {
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      const allFrames = Object.keys(frameMap);
      const step = allFrames.length > 250 ? 3 : 1;

      for (let i = 0; i < allFrames.length; i += step) {
        const fKey = allFrames[i];
        const fNum = Number(fKey);
        // During active video playback, accumulate heat up to the current frame
        if (isPlaying && fNum > currentFrame) continue;

        const list = frameMap[fKey];
        if (!list) continue;

        for (let j = 0; j < list.length; j += 1) {
          const det = list[j];
          if (hiddenTracks.has(det.track_id)) continue;

          const cx = offsetX + (det.x1 + det.w / 2) * scale;
          const cy = offsetY + (det.y1 + det.h / 2) * scale;
          const radius = Math.max(18, Math.min(60, (det.w + det.h) * 0.22 * scale));

          const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
          grad.addColorStop(0, 'rgba(255, 68, 68, 0.20)');
          grad.addColorStop(0.35, 'rgba(255, 170, 0, 0.14)');
          grad.addColorStop(0.7, 'rgba(0, 229, 255, 0.08)');
          grad.addColorStop(1, 'rgba(0, 229, 255, 0)');

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(cx, cy, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();
    }

    const shouldDrawBoxes = overlays.boundingBoxes;
    const shouldDrawLabels = overlays.trackIds || overlays.confidence;

    if (!shouldDrawBoxes && !shouldDrawLabels) return;

    detections.forEach((det) => {
      if (hiddenTracks.has(det.track_id)) return;

      const x = offsetX + det.x1 * scale;
      const y = offsetY + det.y1 * scale;
      const width = Math.max(2, det.w * scale);
      const height = Math.max(2, det.h * scale);
      const color = trackColor(det.track_id);
      const isSelected = det.track_id === selectedTrackId;

      if (shouldDrawBoxes) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.shadowColor = color;
        ctx.shadowBlur = isSelected ? 14 : 6;
        ctx.strokeRect(x, y, width, height);
        ctx.restore();
      }

      if (shouldDrawLabels) {
        const parts = [];
        if (overlays.trackIds) parts.push(`#${det.track_id}`);
        if (overlays.confidence) parts.push(`${Math.round(det.confidence * 100)}%`);
        const label = parts.join(' ');
        if (label) {
          ctx.save();
          ctx.font = '600 11px "JetBrains Mono", monospace';
          const textWidth = ctx.measureText(label).width;
          const textHeight = 15;
          const labelY = y - textHeight - 2 < 0 ? y : y - textHeight - 2;
          ctx.fillStyle = color;
          ctx.fillRect(x, labelY, textWidth + 8, textHeight);
          ctx.fillStyle = '#040D14';
          ctx.fillText(label, x + 4, labelY + textHeight - 4);
          ctx.restore();
        }
      }
    });
  }, [frameMap, sourceFps, currentFrame, overlays, hiddenTracks, selectedTrackId, isPreRendered, isPlaying]);

  /* Animation loop: keeps the overlay aligned with the playing video. */
  useEffect(() => {
    let running = true;

    const loop = () => {
      if (!running) return;

      const video = videoRef.current;
      if (video && !video.paused && sourceFps > 0 && video.duration) {
        const frameNumber = Math.max(
          1,
          Math.min(totalFrames || Number.MAX_SAFE_INTEGER, Math.floor(video.currentTime * sourceFps) + 1)
        );
        setCurrentFrame((prev) => (prev === frameNumber ? prev : frameNumber));
      }

      drawOverlay();
      rafRef.current = window.requestAnimationFrame(loop);
    };

    rafRef.current = window.requestAnimationFrame(loop);

    return () => {
      running = false;
      if (rafRef.current) window.cancelAnimationFrame(rafRef.current);
    };
  }, [drawOverlay, sourceFps, totalFrames]);

  /* =========================== playback controls ========================== */
  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const handleSpeedChange = (spd) => {
    setPlaybackSpeed(spd);
    if (videoRef.current) videoRef.current.playbackRate = spd;
  };

  const handleFrameStep = (delta) => {
    const video = videoRef.current;
    const fps = sourceFps || 30;
    const nextFrame = Math.min(totalFrames || 1, Math.max(1, currentFrame + delta));

    setCurrentFrame(nextFrame);
    if (video) {
      video.pause();
      setIsPlaying(false);
      video.currentTime = (nextFrame - 1) / fps;
    }
  };

  const handleScrubberChange = (val) => {
    const fps = sourceFps || 30;
    setCurrentFrame(val);
    const video = videoRef.current;
    if (video) video.currentTime = (val - 1) / fps;
  };

  const formatTime = (frame) => {
    const fps = sourceFps || 30;
    const totalSeconds = (frame - 1) / fps;
    const mins = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const secs = String(Math.floor(totalSeconds % 60)).padStart(2, '0');
    const ms = String(Math.floor((totalSeconds % 1) * 100)).padStart(2, '0');
    return `${mins}:${secs}.${ms}`;
  };

  /* ============================== downloads =============================== */
  const handleDownload = async (kind) => {
    if (!jobId) return;
    setDownloadState((prev) => ({ ...prev, [kind]: 'loading' }));
    setDownloadMessage(null);
    try {
      await downloadJobArtifactApi(jobId, kind);
      setDownloadState((prev) => ({ ...prev, [kind]: 'done' }));
      window.setTimeout(
        () => setDownloadState((prev) => ({ ...prev, [kind]: null })),
        2500
      );
    } catch (err) {
      setDownloadState((prev) => ({ ...prev, [kind]: 'error' }));
      setDownloadMessage(err.message);
    }
  };

  /* ================================ helpers =============================== */
  const toggleOverlay = (key) => {
    if (viewMode === 'rendered') {
      setViewMode('interactive');
    }
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleTrackVisibility = (trackId) => {
    setHiddenTracks((prev) => {
      const next = new Set(prev);
      if (next.has(trackId)) next.delete(trackId);
      else next.add(trackId);
      return next;
    });
  };

  const selectTrack = (trackId) => {
    setSelectedTrackId(trackId);
  };

  const overlayCount = Object.values(overlays).filter(Boolean).length;
  const status = job?.status || (results?.status ?? 'PROCESSING');
  const jobConfig = job?.config || {};
  const visibleTracks = trackList.slice(0, 8);

  /* ============================== empty state ============================= */
  if (!jobId) {
    return (
      <div className="glass-card" style={{ padding: '48px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
          No tracking job selected
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Pick a run from the command centre or the tracking history to inspect its results.
        </p>
      </div>
    );
  }

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
          <div className="font-mono" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', wordBreak: 'break-all' }}>
            {videoMeta?.filename || job?.video_id || 'Loading...'}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            {videoMeta?.width && videoMeta?.height
              ? `${videoMeta.width}x${videoMeta.height} • ${sourceFps ? sourceFps.toFixed(1) : '—'} FPS`
              : 'Awaiting video metadata'}
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Display Overlays Section */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              SHOW ON VIDEO
            </span>
            <span className="badge badge-cyan font-mono" style={{ fontSize: '0.62rem' }}>{overlayCount} Active</span>
          </div>

          {viewMode === 'rendered' && (
            <div
              className="font-mono"
              style={{
                fontSize: '0.68rem',
                color: 'var(--accent-amber)',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                borderRadius: '4px',
                padding: '6px 8px',
                marginBottom: '8px',
                lineHeight: 1.3,
              }}
            >
              <Zap size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: '-2px' }} />
              Viewing pre-rendered video. Clicking any overlay below switches back to live interactive mode.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { id: 'boundingBoxes', label: 'Bounding Boxes', icon: '⊡' },
              { id: 'trackIds', label: 'Object ID Labels', icon: <Tag size={13} /> },
              { id: 'confidence', label: 'Confidence Scores', icon: '%' },
              { id: 'trajectory', label: 'Motion Path', icon: <TrendingUp size={13} /> },
              { id: 'heatmap', label: 'Activity Heatmap', icon: <Flame size={13} /> },
            ].map((item) => (
              <label
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  backgroundColor: overlays[item.id] ? 'rgba(0, 229, 255, 0.06)' : '#000000',
                  border: overlays[item.id] ? '1px solid var(--border-cyan)' : '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                  color: overlays[item.id] ? 'var(--text-primary)' : 'var(--text-muted)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{item.icon}</span>
                  <span style={{ fontWeight: overlays[item.id] ? 600 : 400 }}>{item.label}</span>
                </div>
                <input
                  type="checkbox"
                  checked={overlays[item.id]}
                  onChange={() => toggleOverlay(item.id)}
                  style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer', width: '16px', height: '16px' }}
                />
              </label>
            ))}
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Tracked Identities */}
        <div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '10px' }}>
            TRACKED IDENTITIES
          </div>

          {visibleTracks.length === 0 && (
            <div className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '8px 0' }}>
              No identity data yet.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {visibleTracks.map((track) => {
              const active = !hiddenTracks.has(track.track_id);
              const isSelected = track.track_id === selectedTrackId;
              return (
                <div
                  key={track.track_id}
                  onClick={() => selectTrack(track.track_id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: isSelected ? '1px solid var(--border-cyan)' : active ? '1px solid var(--border-subtle)' : '1px solid var(--border-subtle)',
                    backgroundColor: isSelected ? 'rgba(0, 229, 255, 0.12)' : active ? '#000000' : 'rgba(255,255,255,0.03)',
                    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: isSelected ? 700 : 400,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleTrackVisibility(track.track_id);
                      }}
                      style={{ color: trackColor(track.track_id), display: 'inline-flex', alignItems: 'center' }}
                    >
                      {active ? <CheckSquare size={13} /> : <Square size={13} />}
                    </span>
                    <span className="font-mono" style={{ fontSize: '0.75rem' }}>
                      #{track.track_id}
                    </span>
                  </div>
                  <span className="badge badge-cyan font-mono" style={{ fontSize: '0.65rem' }}>
                    {track.frames}f
                  </span>
                </div>
              );
            })}
          </div>

          {trackList.length > visibleTracks.length && (
            <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '8px' }}>
              + {trackList.length - visibleTracks.length} more identities tracked
            </div>
          )}
        </div>

        {/* Track States Footer */}
        <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
            TRACKING STATUS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', textAlign: 'center' }}>
            <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>{statusCounts.active}</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-emerald)' }}>ACTIVE</div>
            </div>
            <div style={{ backgroundColor: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-amber)' }}>{statusCounts.fresh}</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-amber)' }}>NEW</div>
            </div>
            <div style={{ backgroundColor: 'rgba(244, 63, 94, 0.12)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '4px', padding: '6px' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-rose)' }}>{statusCounts.lost}</div>
              <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-rose)' }}>LOST</div>
            </div>
          </div>
        </div>
      </div>

      {/* CENTER PANEL: Video Canvas & Interactive Scrubber Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
        {/* Telemetry Bar */}
        <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {videoMeta?.filename || job?.video_id || 'Loading source...'}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* View Mode Toggle: Interactive vs Pre-Rendered */}
            <div style={{ display: 'flex', background: 'rgba(0,0,0,0.6)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                onClick={() => setViewMode('interactive')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  border: 'none',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  backgroundColor: viewMode === 'interactive' ? 'var(--accent-cyan)' : 'transparent',
                  color: viewMode === 'interactive' ? '#000' : 'var(--text-secondary)',
                  transition: 'all 0.2s',
                }}
              >
                Interactive Filters ({overlayCount})
              </button>
              <button
                type="button"
                onClick={() => setViewMode('rendered')}
                disabled={!annotatedVideoUrl}
                title={annotatedVideoUrl ? 'View exported video with baked-in annotations' : 'Annotated video not ready'}
                style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  border: 'none',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  cursor: annotatedVideoUrl ? 'pointer' : 'not-allowed',
                  backgroundColor: viewMode === 'rendered' ? 'var(--accent-cyan)' : 'transparent',
                  color: viewMode === 'rendered' ? '#000' : 'var(--text-secondary)',
                  opacity: annotatedVideoUrl ? 1 : 0.5,
                  transition: 'all 0.2s',
                }}
              >
                Pre-Rendered MP4
              </button>
            </div>

            <div className="font-mono" style={{ display: 'flex', gap: '12px', fontSize: '0.72rem', color: 'var(--text-secondary)', alignItems: 'center' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Zap size={12} color="var(--accent-cyan)" />
                {sourceFps ? `${sourceFps.toFixed(1)} FPS` : '—'}
              </span>
              {videoMeta?.width ? <span>{videoMeta.width}x{videoMeta.height}</span> : null}
              <span style={{ color: 'var(--accent-cyan)' }}>YOLOv8 + DeepSORT</span>
            </div>
          </div>
        </div>

        {/* Video Canvas Container */}
        {loadError && (
          <div
            className="font-mono"
            style={{
              fontSize: '0.72rem',
              color: 'var(--accent-rose)',
              backgroundColor: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid rgba(244, 63, 94, 0.35)',
              borderRadius: '6px',
              padding: '8px 12px',
            }}
          >
            {loadError}
          </div>
        )}

        <div style={{
          flex: 1,
          backgroundColor: '#000',
          borderRadius: '10px',
          border: '1px solid var(--border-strong)',
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {(status === 'PROCESSING' || status === 'QUEUED') ? (
            <div style={{
              width: '100%',
              height: '100%',
              background: 'radial-gradient(ellipse at center, rgba(0, 229, 255, 0.05) 0%, rgba(3, 7, 18, 0.98) 75%), #030712',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '32px',
              textAlign: 'center',
              position: 'relative',
              overflow: 'hidden'
            }}>
              {/* Glowing Hex/Radar Core */}
              <div style={{
                position: 'relative',
                width: '84px',
                height: '84px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: '50%',
                  border: '2px dashed rgba(0, 229, 255, 0.4)',
                  animation: 'spin 10s linear infinite'
                }} />
                <div style={{
                  position: 'absolute',
                  inset: '8px',
                  borderRadius: '50%',
                  border: '2px solid rgba(0, 229, 255, 0.6)',
                  borderTopColor: 'transparent',
                  animation: 'spin 2s linear infinite reverse'
                }} />
                <Zap size={32} color="var(--accent-cyan)" style={{ filter: 'drop-shadow(0 0 10px rgba(0, 229, 255, 0.8))' }} />
              </div>

              {/* Title & Status */}
              <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', letterSpacing: '0.15em', fontWeight: 700, marginBottom: '6px' }}>
                DEEPSORT TRACKING PIPELINE ACTIVE
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
                {videoMeta?.filename || 'Processing Video Frames...'}
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', maxWidth: '460px', marginBottom: '22px', lineHeight: 1.5 }}>
                {(job?.progress ?? 5) < 20
                  ? 'Initializing YOLOv8 object detector weights & preparing tensor frames...'
                  : (job?.progress ?? 5) < 85
                  ? 'Extracting 512-d Re-ID feature embeddings & updating Kalman spatial filters...'
                  : 'Synthesizing tracked bounding boxes & encoding high-compatibility H.264 artifact...'}
              </p>

              {/* Main Progress Bar Container */}
              <div style={{ width: '100%', maxWidth: '420px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.75rem' }}>
                  <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                    PIPELINE EXECUTION
                  </span>
                  <span className="font-mono" style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: '0.9rem' }}>
                    {job?.progress ?? 5}%
                  </span>
                </div>
                <div style={{
                  width: '100%',
                  height: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: '6px',
                  border: '1px solid rgba(0, 229, 255, 0.25)',
                  padding: '1px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.max(5, job?.progress ?? 5)}%`,
                    background: 'linear-gradient(90deg, #00e5ff 0%, #38bdf8 50%, #00e5ff 100%)',
                    borderRadius: '4px',
                    boxShadow: '0 0 12px rgba(0, 229, 255, 0.6)',
                    transition: 'width 0.4s ease'
                  }} />
                </div>
              </div>

              {/* Live Status Badges */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <span className="badge badge-cyan font-mono" style={{ fontSize: '0.68rem' }}>
                  • Detector: YOLOv8 (480p Fast CPU)
                </span>
                <span className="badge badge-processing font-mono" style={{ fontSize: '0.68rem' }}>
                  • Associator: DeepSORT + Cosine
                </span>
                <span className="badge badge-emerald font-mono" style={{ fontSize: '0.68rem' }}>
                  • Live Polling (2s)
                </span>
              </div>
            </div>
          ) : status === 'FAILED' ? (
            <div style={{
              width: '100%',
              height: '100%',
              background: 'radial-gradient(ellipse at center, rgba(244, 63, 94, 0.08) 0%, rgba(0, 0, 0, 0.95) 75%), #050505',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '32px',
              textAlign: 'center'
            }}>
              <AlertTriangle size={36} color="var(--accent-rose)" style={{ marginBottom: '12px' }} />
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-rose)', marginBottom: '8px' }}>
                Tracking Pipeline Execution Failed
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', maxWidth: '480px', marginBottom: '16px' }}>
                {job?.error_message || 'Pipeline execution halted prematurely.'}
              </p>
              {onCloneJob && (
                <button
                  className="btn btn-cyan btn-sm"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  onClick={() => onCloneJob({
                    videoId: job?.video_id,
                    videoName: videoMeta?.filename,
                    confThreshold: jobConfig?.conf_threshold ?? 0.25,
                    cosineDist: jobConfig?.max_cosine_distance ?? 0.20,
                    maxAge: jobConfig?.max_age ?? 30,
                    nInit: jobConfig?.n_init ?? 1,
                  })}
                >
                  <RotateCcw size={13} />
                  <span>Retry Run with Adjusted Parameters</span>
                </button>
              )}
            </div>
          ) : activeVideoSrc ? (
            <video
              key={activeVideoSrc}
              ref={videoRef}
              src={activeVideoSrc}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
              controls
              autoPlay
              loop
              muted
              playsInline
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              background: 'linear-gradient(180deg, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.95) 100%), #050505',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem'
            }}>
              No playable artifact for this job.
            </div>
          )}

          {/* OVERLAY LAYER */}
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
            <canvas
              ref={canvasRef}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
            />

            {/* Processing Banner if job is running */}
            {(status === 'PROCESSING' || status === 'QUEUED') && (
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
                zIndex: 10,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <Zap size={13} />
                <span>YOLOv8 + DeepSORT Processing video...Drawing Bounding Boxes & Tracking IDs</span>
              </div>
            )}

            {/* Dark contrast vignette overlay */}
            <div style={{ position: 'absolute', inset: 0, background: 'rgba(0, 0, 0, 0.12)' }} />

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
              <div>{job?.created_at ? `${formatDateTime(job.created_at)} UTC` : '—'}</div>
              <div style={{ color: 'var(--accent-cyan)' }}>FRAME_{String(currentFrame).padStart(6, '0')}</div>
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
              max={Math.max(1, totalFrames)}
              value={Math.min(currentFrame, Math.max(1, totalFrames))}
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
                style={{ padding: '6px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                disabled={!activeVideoSrc}
              >
                {isPlaying ? (
                  <>
                    <Pause size={13} />
                    <span>Pause</span>
                  </>
                ) : (
                  <>
                    <Play size={13} />
                    <span>Play</span>
                  </>
                )}
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
            <span className={STATUS_BADGE[status] || 'badge badge-cyan'}>• {status}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <div>
              <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                {results ? results.total_tracks : '-'}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>OBJECTS TRACKED</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                {results ? results.total_detections.toLocaleString() : '-'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Detections</div>
            </div>
          </div>

          {results?.error_message && (
            <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--accent-rose)', marginTop: '8px' }}>
              {results.error_message}
            </div>
          )}
        </div>

        <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)' }} />

        {/* Primary Export Artifacts Buttons */}
        <div>
          <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.08em' }}>
            DOWNLOAD RESULTS
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              onClick={() => handleDownload('video')}
              disabled={downloadState.video === 'loading'}
              className="btn btn-cyan"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '10px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              {downloadState.video === 'loading' ? (
                <>
                  <Loader2 size={13} className="spin" />
                  <span>Preparing video...</span>
                </>
              ) : downloadState.video === 'done' ? (
                <>
                  <Check size={13} />
                  <span>Video downloaded</span>
                </>
              ) : (
                <>
                  <Download size={13} />
                  <span>Download Tracked Video</span>
                </>
              )}
            </button>
            <button
              onClick={() => handleDownload('mot')}
              disabled={downloadState.mot === 'loading'}
              className="btn btn-outline-cyan"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '8px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              {downloadState.mot === 'loading' ? (
                <>
                  <Loader2 size={13} className="spin" />
                  <span>Preparing data...</span>
                </>
              ) : downloadState.mot === 'done' ? (
                <>
                  <Check size={13} />
                  <span>Tracking data downloaded</span>
                </>
              ) : (
                <>
                  <FileText size={13} />
                  <span>Download Tracking Data</span>
                </>
              )}
            </button>
          </div>

          {downloadMessage && (
            <div
              className="font-mono"
              style={{
                fontSize: '0.68rem',
                color: 'var(--accent-rose)',
                marginTop: '8px',
                backgroundColor: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '4px',
                padding: '6px 8px',
              }}
            >
              {downloadMessage}
            </div>
          )}
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
              <span>Sensitivity:</span> <span style={{ color: 'var(--accent-cyan)' }}>{jobConfig.conf_threshold ?? '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Match Strictness:</span> <span style={{ color: 'var(--accent-cyan)' }}>{jobConfig.max_cosine_distance ?? '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Memory (frames):</span> <span style={{ color: 'var(--text-primary)' }}>{jobConfig.max_age ?? '—'} frames</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Min Detections:</span> <span style={{ color: 'var(--text-primary)' }}>{jobConfig.n_init ?? '—'} frames</span>
            </div>
          </div>

          {/* Job Management: Clone & Delete */}
          {job && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '10px' }}>
              <button
                type="button"
                className="btn btn-outline-cyan"
                style={{ fontSize: '0.72rem', padding: '6px 8px', justifyContent: 'center', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                title="Clone tracking parameters into a new run"
                onClick={() => {
                  if (onCloneJob) {
                    onCloneJob({
                      videoId: job.video_id,
                      videoName: videoMeta?.filename || 'Current Video',
                      confThreshold: jobConfig.conf_threshold,
                      cosineDist: jobConfig.max_cosine_distance,
                      maxAge: jobConfig.max_age,
                      nInit: jobConfig.n_init,
                      reidWeights: jobConfig.reid_weights || 'base',
                    });
                  } else if (setActivePage) {
                    setActivePage('ingest');
                  }
                }}
              >
                <Copy size={12} />
                <span>Clone Run</span>
              </button>
              <button
                type="button"
                className="btn"
                style={{
                  fontSize: '0.72rem',
                  padding: '6px 8px',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(244, 63, 94, 0.1)',
                  borderColor: 'rgba(244, 63, 94, 0.4)',
                  color: 'var(--accent-rose)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
                title="Delete this tracking run and its files"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 size={12} />
                <span>Delete Run</span>
              </button>
            </div>
          )}
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
            <span className="badge badge-cyan">
              {selectedTrack ? `#${selectedTrack.track_id} • ${selectedTrack.last >= currentFrame ? 'Confirmed' : 'Archived'}` : '—'}
            </span>
          </div>

          {selectedTrack ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.75rem' }}>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>TRACK ID</div>
                <div style={{ fontWeight: 700, color: trackColor(selectedTrack.track_id) }}>
                  #{selectedTrack.track_id}
                </div>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>CONFIDENCE</div>
                <div className="font-mono" style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>
                  {(selectedTrack.avg_confidence * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>DURATION</div>
                <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                  {selectedTrack.frames} frames{sourceFps ? ` (${(selectedTrack.frames / sourceFps).toFixed(1)}s)` : ''}
                </div>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>STATUS</div>
                <div style={{ color: selectedTrack.last >= currentFrame ? 'var(--accent-emerald)' : 'var(--text-secondary)', fontWeight: 600 }}>
                  {selectedTrack.last >= currentFrame ? 'Tracking Active' : 'Track Complete'}
                </div>
              </div>
            </div>
          ) : (
            <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Select an identity to inspect it.
            </div>
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={showDeleteConfirm}
        title="Delete Tracking Run"
        message={`Are you sure you want to delete Run #${job?.id?.slice(0, 8)}? All tracked video outputs and MOT tracking data will be permanently removed from disk.`}
        confirmLabel="Delete Run"
        isDanger={true}
        isLoading={isDeleting}
        onCancel={() => setShowDeleteConfirm(false)}
        onConfirm={async () => {
          if (!job) return;
          setIsDeleting(true);
          try {
            await deleteJobApi(job.id);
            setShowDeleteConfirm(false);
            if (setActivePage) {
              setActivePage('dashboard');
            }
          } catch (err) {
            console.error('Failed to delete job:', err);
            alert(err.message || 'Failed to delete tracking run');
          } finally {
            setIsDeleting(false);
          }
        }}
      />
    </div>
  );
}

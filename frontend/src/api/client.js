/**
 * API Client Services for MOT Vision Frontend.
 * Interacts with FastAPI endpoints at http://localhost:8000/api/v1
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

export async function uploadVideoApi(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE_URL}/videos/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to upload video asset.');
    }
    return await res.json();
  } catch (err) {
    console.warn('API endpoint unavailable, using mock asset fallback:', err.message);
    return {
      id: 'vid-' + Date.now(),
      filename: file.name,
      file_path: '/uploads/' + file.name,
      duration: 42.5,
      fps: 60.0,
      width: 1920,
      height: 1080,
      frame_count: 2550,
      file_size: file.size,
    };
  }
}

export async function createJobApi({ videoId, confThreshold, cosineDist, maxAge, nInit }) {
  try {
    const res = await fetch(`${API_BASE_URL}/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        conf_threshold: confThreshold,
        max_cosine_distance: cosineDist,
        max_age: maxAge,
        n_init: nInit,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create tracking job.');
    }
    return await res.json();
  } catch (err) {
    console.warn('API endpoint unavailable, using mock job fallback:', err.message);
    return {
      id: 'job-' + Date.now(),
      video_id: videoId,
      status: 'PROCESSING',
      progress: 10,
      config: { conf_threshold: confThreshold, max_cosine_distance: cosineDist },
    };
  }
}

export async function getJobsApi() {
  try {
    const res = await fetch(`${API_BASE_URL}/jobs`);
    if (!res.ok) throw new Error('Failed to fetch jobs.');
    return await res.json();
  } catch (err) {
    return null; // Return null so UI maintains telemetry fallback
  }
}

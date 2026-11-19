/**
 * API Client Services for MOT Vision Frontend.
 * Interacts with FastAPI endpoints at http://localhost:8000/api/v1
 */

export const BACKEND_BASE_URL =
  import.meta.env?.VITE_BACKEND_BASE_URL || 'http://localhost:8000';

export const API_BASE_URL = `${BACKEND_BASE_URL}/api/v1`;

const TOKEN_STORAGE_KEY = 'mot_auth_token';

/**
 * Health check & hardware info endpoint
 */
export async function getHealthApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/health`, {}, 5000);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Deadline for requests that gate the UI. The tracking backend warms up
 * torch/ultralytics for ~45s on boot and an idle socket can hang for minutes,
 * so anything the first paint waits on must carry its own timeout.
 */
const REQUEST_TIMEOUT_MS = 15000;

/**
 * `fetch` with a bounded wait.
 * Network failures are re-thrown with an actionable message; callers decide
 * whether that means "fall back to mock data" or "show the login screen".
 *
 * The deadline is enforced with `Promise.race`, not only via the abort signal,
 * so a `fetch` implementation that ignores the signal can still never wedge the
 * caller (that is exactly how "Restoring session..." used to hang forever).
 */
export async function fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const seconds = Math.round(timeoutMs / 1000);

  let timer;
  const deadline = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      const err = new Error(
        `Backend did not respond within ${seconds}s (${BACKEND_BASE_URL}).`
      );
      err.name = 'TimeoutError';
      reject(err);
    }, timeoutMs);
  });

  try {
    const res = await Promise.race([
      fetch(url, { ...options, signal: controller.signal }),
      deadline,
    ]);
    if (
      res.status === 401 &&
      !url.includes('/auth/login') &&
      !url.includes('/auth/register') &&
      !url.includes('/auth/google')
    ) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('mot:unauthorized'));
      }
    }
    return res;
  } catch (err) {
    if (err?.name === 'TimeoutError') throw err;
    if (err?.name === 'AbortError') {
      throw new Error(`Request to ${BACKEND_BASE_URL} timed out after ${seconds}s.`);
    }
    throw new Error(`Cannot reach the backend at ${BACKEND_BASE_URL}. Is it running?`);
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ *
 * Token storage helpers
 * ------------------------------------------------------------------ */

/** Read the persisted JWT access token from localStorage (null when absent). */
export function getToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.warn('Unable to read auth token from localStorage:', err.message);
    return null;
  }
}

/** Persist the JWT access token in localStorage. */
export function setToken(token) {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (err) {
    console.warn('Unable to persist auth token to localStorage:', err.message);
  }
}

/** Remove the persisted JWT access token from localStorage. */
export function clearToken() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.warn('Unable to clear auth token from localStorage:', err.message);
  }
}

/**
 * Build the Authorization header for an authenticated request.
 * Returns an empty object when no token is stored (public endpoints).
 */
export function authHeaders(extraHeaders = {}) {
  const token = getToken();
  const headers = { ...extraHeaders };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/** Parse a FastAPI error payload into a human readable message. */
async function readError(res, fallback) {
  try {
    const body = await res.json();
    if (typeof body?.detail === 'string') return body.detail;
    if (Array.isArray(body?.detail) && body.detail.length > 0) {
      const first = body.detail[0];
      return first?.msg || fallback;
    }
    if (body?.message) return body.message;
  } catch {
    /* fall through to generic message */
  }
  return fallback;
}

/* ------------------------------------------------------------------ *
 * Authentication
 * ------------------------------------------------------------------ */

/**
 * Authenticate with email + password and persist the returned JWT.
 * Uses the OAuth2 password grant (form encoded, not JSON).
 */
export async function loginApi(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const res = await fetchWithTimeout(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });

  if (!res.ok) {
    throw new Error(await readError(res, 'Invalid email or password.'));
  }

  const data = await res.json();
  const token = data.access_token || data.token || null;
  if (token) setToken(token);

  return { token, tokenType: data.token_type || 'bearer' };
}

/**
 * Authenticate using a verified Google ID Token and persist the returned application JWT.
 */
export async function loginWithGoogleApi(credential) {
  const res = await fetchWithTimeout(`${API_BASE_URL}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential }),
  });

  if (!res.ok) {
    throw new Error(await readError(res, 'Google authentication failed.'));
  }

  const data = await res.json();
  const token = data.access_token || data.token || null;
  if (token) setToken(token);

  return { token, tokenType: data.token_type || 'bearer' };
}

/** Register a new account. Returns the created user profile. */
export async function registerApi(email, password, name) {
  const res = await fetchWithTimeout(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      full_name: name || null,
    }),
  });

  if (!res.ok) {
    throw new Error(await readError(res, 'Failed to register account.'));
  }

  return await res.json();
}

/**
 * Resolve the currently authenticated user profile from the stored token.
 *
 * Returns `null` only when the backend explicitly rejected the token
 * (expired / revoked). Network failures and 5xx responses throw instead, so
 * the caller can keep the token and show "backend unreachable" rather than
 * silently logging the user out.
 */
export async function getCurrentUserApi() {
  const token = getToken();
  if (!token) return null;

  const res = await fetchWithTimeout(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(),
  });

  if (res.status === 401 || res.status === 403) return null;
  if (!res.ok) {
    throw new Error(await readError(res, 'Backend rejected the session restore request.'));
  }

  return await res.json();
}

/** Clear the local session (token removed from localStorage). */
export async function logoutApi() {
  clearToken();
  return true;
}

/* ------------------------------------------------------------------ *
 * Videos
 * ------------------------------------------------------------------ */

export async function uploadVideoApi(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE_URL}/videos/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await readError(res, 'Failed to upload video asset.');
      throw new Error(err);
    }
    return await res.json();
  } catch (err) {
    console.error('Video upload failed:', err.message);
    throw err;
  }
}

/** List the video assets owned by the authenticated user. */
export async function getVideosApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/videos`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch videos.');
    return await res.json();
  } catch (err) {
    console.warn('Unable to list videos:', err.message);
    return null;
  }
}

/* ------------------------------------------------------------------ *
 * Tracking jobs
 * ------------------------------------------------------------------ */

export async function createJobApi({ videoId, confThreshold, cosineDist, maxAge, nInit }) {
  try {
    const res = await fetch(`${API_BASE_URL}/jobs`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        video_id: videoId,
        conf_threshold: confThreshold,
        max_cosine_distance: cosineDist,
        max_age: maxAge,
        n_init: nInit,
      }),
    });
    if (!res.ok) {
      const err = await readError(res, 'Failed to create tracking job.');
      throw new Error(err);
    }
    return await res.json();
  } catch (err) {
    console.error('Tracking job dispatch failed:', err.message);
    throw err;
  }
}

export async function getJobsApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/jobs`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch jobs.');
    return await res.json();
  } catch {
    return null; // Return null so UI maintains telemetry fallback
  }
}

/** Fetch a single tracking job by id. */
export async function getJobApi(jobId) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/jobs/${jobId}`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch job.');
    return await res.json();
  } catch {
    return null;
  }
}

/** Fetch the aggregated tracking statistics for a job. */
export async function getJobResultsApi(jobId) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/jobs/${jobId}/results`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch job results.');
    return await res.json();
  } catch {
    return null;
  }
}

/** Fetch the per-frame bounding box overlay payload for a job. */
export async function getJobFramesApi(jobId) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/jobs/${jobId}/frames`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch frame data.');
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Download a job artifact through the authenticated API and trigger a browser save.
 * `kind` is either 'video' (annotated MP4) or 'mot' (tracking data text file).
 */
export async function downloadJobArtifactApi(jobId, kind) {
  const path = kind === 'mot' ? 'mot' : 'video';
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/download/${path}`, {
    headers: authHeaders(),
  });

  if (!res.ok) {
    throw new Error(
      await readError(res, 'Artifact is not available for this job yet.')
    );
  }

  const blob = await res.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = `${jobId}_${kind === 'mot' ? 'mot.txt' : 'annotated.mp4'}`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(objectUrl);

  return true;
}

/* ------------------------------------------------------------------ *
 * MOT17 benchmark
 * ------------------------------------------------------------------ */

/** Discover the MOT17 sequences available for evaluation. */
export async function getBenchmarkSequencesApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/benchmark/sequences`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch benchmark sequences.');
    return await res.json();
  } catch (err) {
    console.warn('Unable to list benchmark sequences:', err.message);
    return null;
  }
}

/** Read the persisted benchmark evaluation history. */
export async function getBenchmarkResultsApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/benchmark/results`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch benchmark results.');
    return await res.json();
  } catch (err) {
    console.warn('Unable to list benchmark results:', err.message);
    return null;
  }
}

/** Trigger a MOT17 CLEAR-MOT evaluation for a single sequence. */
export async function runBenchmarkApi({ sequenceName, resultsFile, jobId }) {
  const res = await fetch(`${API_BASE_URL}/benchmark/evaluate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      sequence_name: sequenceName,
      results_file: resultsFile || null,
      job_id: jobId || null,
    }),
  });

  if (!res.ok) {
    throw new Error(await readError(res, 'Benchmark evaluation failed.'));
  }

  return await res.json();
}

/* ------------------------------------------------------------------ *
 * Job & Video Deletion (CRUD Completeness)
 * ------------------------------------------------------------------ */

/** Delete a tracking run and its output artifacts from the backend and database. */
export async function deleteJobApi(jobId) {
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(await readError(res, 'Failed to delete tracking run.'));
  }
  return await res.json();
}

/** Delete a video and all associated jobs from the backend. */
export async function deleteVideoApi(videoId) {
  const res = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(await readError(res, 'Failed to delete video.'));
  }
  return await res.json();
}

/* ------------------------------------------------------------------ *
 * Model Training & Fine-Tuning
 * ------------------------------------------------------------------ */

/** Fetch previous Re-ID model training runs / checkpoints. */
export async function getTrainingRunsApi() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/models/training-runs`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch training runs.');
    return await res.json();
  } catch (err) {
    console.warn('Unable to list training runs:', err.message);
    return null;
  }
}

/** Start a fine-tuning run for Re-ID appearance embeddings. */
export async function startReidTrainingApi({ epochs, learning_rate, batch_size, model_type }) {
  const res = await fetch(`${API_BASE_URL}/models/train`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      epochs: Number(epochs) || 10,
      learning_rate: Number(learning_rate) || 0.0003,
      batch_size: Number(batch_size) || 32,
      model_type: model_type || 'reid_osnet',
    }),
  });
  if (!res.ok) {
    throw new Error(await readError(res, 'Failed to start Re-ID model training.'));
  }
  return await res.json();
}



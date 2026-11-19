/**
 * Shared display formatters for the MOT Vision frontend.
 */

/**
 * Parse an ISO-like timestamp safely, treating naive datetime strings from SQLite as UTC.
 */
export function parseUtcDate(isoString) {
  if (!isoString) return null;
  let str = String(isoString).trim();
  // If string lacks a timezone offset (e.g. "2026-11-16 18:02:00.546065" or "2026-11-16T18:02:00"),
  // treat it as UTC to avoid local timezone interpretation offsets (e.g. 5.5 hour IST shift).
  if (!str.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(str)) {
    str = str.replace(' ', 'T') + 'Z';
  }
  const date = new Date(str);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Format an ISO timestamp as a short relative string ("12 mins ago"). */
export function formatRelativeTime(isoString) {
  const then = parseUtcDate(isoString);
  if (!then) return '-';

  const deltaSeconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (deltaSeconds < 5) return 'just now';
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;

  const minutes = Math.floor(deltaSeconds / 60);
  if (minutes < 60) return `${minutes} mins ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

/** Format an ISO timestamp as "YYYY-MM-DD HH:MM". */
export function formatDateTime(isoString) {
  const date = parseUtcDate(isoString);
  if (!date) return '-';

  const pad = (value) => String(value).padStart(2, '0');
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** Format a byte count as a human readable string. */
export function formatBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return '-';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

/** Format a duration in seconds as "mm:ss". */
export function formatDuration(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return '-';

  const mins = Math.floor(value / 60);
  const secs = Math.floor(value % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/** Format a percentage ratio (0..1) as a display string. */
export function formatPercent(ratio, digits = 1) {
  const value = Number(ratio);
  if (!Number.isFinite(value)) return '-';
  return `${(value * 100).toFixed(digits)}%`;
}

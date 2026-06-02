import { APP_TIMEZONE } from '../config'

export function prevMonth(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (m === 1) return `${y - 1}-12`
  return `${y}-${String(m - 1).padStart(2, '0')}`
}

export function nextMonth(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  if (m === 12) return `${y + 1}-01`
  return `${y}-${String(m + 1).padStart(2, '0')}`
}

export function formatMonthYear(ym: string): string {
  const [y, m] = ym.split('-').map(Number)
  const month = new Date(y, m - 1, 1).toLocaleString('ru-RU', { month: 'long' })
  return `${month.charAt(0).toUpperCase()}${month.slice(1)} ${y}`
}

export function monthDateRange(ym: string): { start_date: string; end_date: string } {
  const [y, m] = ym.split('-').map(Number)
  const lastDay = new Date(y, m, 0).getDate()
  return {
    start_date: `${ym}-01T00:00:00`,
    end_date: `${ym}-${String(lastDay).padStart(2, '0')}T23:59:59`,
  }
}

/** Format a UTC ISO string for display in the app timezone. Returns "—" for null/undefined. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', {
    timeZone: APP_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Format a UTC ISO string with time for display in the app timezone. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', {
    timeZone: APP_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Current "YYYY-MM" in the app timezone.
 * Use instead of new Date().toISOString().slice(0,7) which gives UTC month.
 */
export function currentYearMonth(): string {
  return new Date().toLocaleString('sv-SE', { timeZone: APP_TIMEZONE }).slice(0, 7)
}

/**
 * Convert a UTC ISO string to a datetime-local input value (wall-clock in APP_TIMEZONE).
 * Returns the format "YYYY-MM-DDTHH:MM" expected by <input type="datetime-local">.
 */
export function utcIsoToLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso)
    .toLocaleString('sv-SE', { timeZone: APP_TIMEZONE })
    .slice(0, 16)
    .replace(' ', 'T')
}

/**
 * Convert a datetime-local input value (wall-clock in APP_TIMEZONE) to a UTC ISO string.
 *
 * The datetime-local HTML input returns "YYYY-MM-DDTHH:MM" with no timezone.
 * We treat that time as being in APP_TIMEZONE and return the equivalent UTC instant.
 */
export function localInputToUtcIso(localStr: string): string {
  // Treat the string as UTC to get a reference point
  const asUtcMs = new Date(`${localStr}:00Z`).getTime()
  // Find what that UTC instant looks like in APP_TIMEZONE
  const displayedInTz = new Date(asUtcMs)
    .toLocaleString('sv-SE', { timeZone: APP_TIMEZONE })
    .slice(0, 16)
  // tzOffsetMs is positive for UTC+ zones (e.g., +10_800_000 for UTC+3)
  const tzOffsetMs = new Date(`${displayedInTz.replace(' ', 'T')}:00Z`).getTime() - asUtcMs
  // Subtract the offset to get the UTC equivalent of the user's wall-clock input
  return new Date(asUtcMs - tzOffsetMs).toISOString()
}

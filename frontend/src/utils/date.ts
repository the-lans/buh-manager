import { APP_TIMEZONE } from '../config'

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

/** Return "YYYY-MM" for the previous month. */
export function prevMonth(ym: string): string {
  const [year, month] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(year, month - 2, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/** Return "YYYY-MM" for the next month. */
export function nextMonth(ym: string): string {
  const [year, month] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(year, month, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/**
 * Return UTC ISO start/end bounds for a calendar month.
 * start_date = first moment of the month (UTC midnight on day 1)
 * end_date   = first moment of the next month (exclusive upper bound)
 */
export function monthBoundsUtc(ym: string): { start_date: string; end_date: string } {
  const [year, month] = ym.split('-').map(Number)
  return {
    start_date: new Date(Date.UTC(year, month - 1, 1)).toISOString(),
    end_date: new Date(Date.UTC(year, month, 1)).toISOString(),
  }
}

const MONTH_NAMES_RU = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
]

/** "YYYY-MM" → "Май 2026" */
export function formatMonthLabel(ym: string): string {
  const [year, month] = ym.split('-').map(Number)
  return `${MONTH_NAMES_RU[month - 1]} ${year}`
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

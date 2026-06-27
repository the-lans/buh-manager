import { describe, it, expect } from 'vitest'
import {
  prevMonth,
  nextMonth,
  formatMonthYear,
  monthDateRange,
  localDayBoundaryToUtcIso,
  localInputToUtcIso,
  localInputToUtcIsoPreservingSeconds,
  utcIsoToLocalInput,
  formatDate,
  formatDateTime,
} from '../date'

describe('prevMonth', () => {
  it('returns previous month for mid-year', () => {
    expect(prevMonth('2026-06')).toBe('2026-05')
  })

  it('rolls back to December of previous year when month is January', () => {
    expect(prevMonth('2026-01')).toBe('2025-12')
  })

  it('pads single-digit month with leading zero', () => {
    expect(prevMonth('2026-10')).toBe('2026-09')
  })
})

describe('nextMonth', () => {
  it('returns next month for mid-year', () => {
    expect(nextMonth('2026-06')).toBe('2026-07')
  })

  it('rolls forward to January of next year when month is December', () => {
    expect(nextMonth('2026-12')).toBe('2027-01')
  })

  it('pads single-digit month with leading zero', () => {
    expect(nextMonth('2026-08')).toBe('2026-09')
  })
})

describe('formatMonthYear', () => {
  it('returns capitalized Russian month name with year', () => {
    const result = formatMonthYear('2026-06')
    expect(result).toMatch(/2026/)
    // Russian month starts with capital letter
    expect(result[0]).toBe(result[0].toUpperCase())
  })

  it('contains the year', () => {
    expect(formatMonthYear('2025-12')).toMatch(/2025/)
  })

  it('differs between months', () => {
    expect(formatMonthYear('2026-01')).not.toBe(formatMonthYear('2026-06'))
  })
})

describe('localDayBoundaryToUtcIso', () => {
  // APP_TIMEZONE = Europe/Moscow = UTC+3
  it('start boundary converts local midnight to UTC', () => {
    // 2026-06-01 00:00:00 Moscow = 2026-05-31 21:00:00 UTC
    expect(localDayBoundaryToUtcIso('2026-06-01', 'start')).toBe('2026-05-31T21:00:00.000Z')
  })

  it('end boundary converts local 23:59:59 to UTC', () => {
    // 2026-06-30 23:59:59 Moscow = 2026-06-30 20:59:59 UTC
    expect(localDayBoundaryToUtcIso('2026-06-30', 'end')).toBe('2026-06-30T20:59:59.000Z')
  })
})

describe('localInputToUtcIsoPreservingSeconds', () => {
  it('keeps seconds and milliseconds from the original ISO value', () => {
    expect(
      localInputToUtcIsoPreservingSeconds(
        '2026-04-02T14:05',
        '2026-04-01T10:00:37.250Z',
      ),
    ).toBe('2026-04-02T11:05:37.250Z')
  })
})

describe('monthDateRange', () => {
  // APP_TIMEZONE = Europe/Moscow = UTC+3; all assertions use UTC ISO strings

  it('returns start_date as UTC ISO for first moment of month in app timezone', () => {
    // June 1 00:00:00 Moscow = May 31 21:00:00 UTC
    const { start_date } = monthDateRange('2026-06')
    expect(start_date).toBe('2026-05-31T21:00:00.000Z')
  })

  it('returns end_date as UTC ISO for last moment of June in app timezone', () => {
    // June 30 23:59:59 Moscow = June 30 20:59:59 UTC
    const { end_date } = monthDateRange('2026-06')
    expect(end_date).toBe('2026-06-30T20:59:59.000Z')
  })

  it('returns correct last day for February in non-leap year', () => {
    // Feb 28 23:59:59 Moscow = Feb 28 20:59:59 UTC
    const { end_date } = monthDateRange('2025-02')
    expect(end_date).toBe('2025-02-28T20:59:59.000Z')
  })

  it('returns correct last day for February in leap year', () => {
    // Feb 29 23:59:59 Moscow = Feb 29 20:59:59 UTC
    const { end_date } = monthDateRange('2024-02')
    expect(end_date).toBe('2024-02-29T20:59:59.000Z')
  })

  it('returns correct last day for January (31 days)', () => {
    // Jan 31 23:59:59 Moscow = Jan 31 20:59:59 UTC
    const { end_date } = monthDateRange('2026-01')
    expect(end_date).toBe('2026-01-31T20:59:59.000Z')
  })
})

// ── localInputToUtcIso — Moscow wall-clock → UTC ISO ─────────────────────────
//
// APP_TIMEZONE = Europe/Moscow = UTC+3 (no DST).
// These tests verify the -3h offset for various calendar-boundary cases.
// Run with TZ=Europe/Moscow to also catch browser-local-time regressions.

describe('localInputToUtcIso — Moscow (UTC+3) to UTC', () => {
  it.each([
    // Moscow midnight crosses the calendar day boundary
    ['2026-06-01T00:00', '2026-05-31T21:00:00.000Z'],
    // Moscow 3am = UTC midnight (same calendar day)
    ['2026-06-01T03:00', '2026-06-01T00:00:00.000Z'],
    // Last minute of Moscow-June
    ['2026-06-30T23:59', '2026-06-30T20:59:00.000Z'],
    // Year boundary: Moscow midnight Jan 1 → Dec 31 21:00 UTC
    ['2026-01-01T00:00', '2025-12-31T21:00:00.000Z'],
    // Last minute of Moscow year
    ['2026-12-31T23:59', '2026-12-31T20:59:00.000Z'],
    // Midday — no boundary crossing
    ['2026-06-15T12:00', '2026-06-15T09:00:00.000Z'],
  ])('converts Moscow %s to UTC %s', (moscowInput, expectedUtc) => {
    expect(localInputToUtcIso(moscowInput)).toBe(expectedUtc)
  })
})

// ── utcIsoToLocalInput — UTC → Moscow wall-clock for <input type="datetime-local"> ──
//
// Backend returns naive UTC strings (no Z).  After our asUtc() fix, both
// naive strings and Z-suffix strings must produce identical Moscow wall-clock output.
// Key case: UTC 21:00 May 31 is Moscow midnight June 1 — the date changes!

describe('utcIsoToLocalInput — UTC to Moscow wall-clock', () => {
  it.each([
    // UTC 07:00 = Moscow 10:00 — same calendar day
    ['2026-06-01T07:00:00',       '2026-06-01T10:00'],
    // UTC 21:00 May 31 = Moscow midnight June 1 — date crosses to next day
    ['2026-05-31T21:00:00',       '2026-06-01T00:00'],
    // Same instant with explicit Z suffix — must give the same result
    ['2026-05-31T21:00:00.000Z',  '2026-06-01T00:00'],
    // UTC 20:59:59 May 31 = Moscow 23:59:59 May 31 — still May
    ['2026-05-31T20:59:59',       '2026-05-31T23:59'],
    // Year boundary: UTC 21:00 Dec 31 = Moscow midnight Jan 1 next year
    ['2025-12-31T21:00:00',       '2026-01-01T00:00'],
    // Z-suffix variant of year boundary
    ['2025-12-31T21:00:00.000Z',  '2026-01-01T00:00'],
    // UTC midnight = Moscow 03:00 (same calendar day)
    ['2026-06-01T00:00:00',       '2026-06-01T03:00'],
  ])('converts UTC %s to Moscow local %s', (utcIso, expectedLocal) => {
    expect(utcIsoToLocalInput(utcIso)).toBe(expectedLocal)
  })

  it.each([null, undefined, ''])('returns empty string for %s', (falsy) => {
    expect(utcIsoToLocalInput(falsy)).toBe('')
  })
})

// ── formatDate — UTC ISO → Moscow date string ─────────────────────────────────
//
// Critical: UTC 21:00 May 31 is Moscow midnight June 1 → must display as 01.06.2026.
// Without the asUtc() fix, a Moscow-timezone browser would display 31.05.2026 instead.

describe('formatDate — displays UTC time in Moscow timezone', () => {
  it.each([
    // Midday UTC — no boundary crossing, same date
    ['2026-06-01T07:00:00',       '01.06.2026'],
    // UTC 21:00 May 31 = Moscow midnight June 1 → shows June 1, NOT May 31
    ['2026-05-31T21:00:00',       '01.06.2026'],
    // Same with explicit Z — must give the same result as naive
    ['2026-05-31T21:00:00.000Z',  '01.06.2026'],
    // UTC 21:00 June 30 = Moscow midnight July 1 → shows July 1 (month boundary)
    ['2026-06-30T21:00:00',       '01.07.2026'],
    // Year boundary: UTC 21:00 Dec 31 = Moscow midnight Jan 1 → shows Jan 1
    ['2025-12-31T21:00:00',       '01.01.2026'],
    // UTC 20:59:59 May 31 = Moscow 23:59:59 May 31 → still shows May 31
    ['2026-05-31T20:59:59',       '31.05.2026'],
  ])('displays %s as %s in Moscow', (utcIso, expectedDate) => {
    expect(formatDate(utcIso)).toBe(expectedDate)
  })

  it.each([null, undefined])('returns "—" for %s', (falsy) => {
    expect(formatDate(falsy)).toBe('—')
  })
})

// ── formatDateTime — UTC ISO → Moscow date+time string ───────────────────────

describe('formatDateTime — displays UTC time in Moscow timezone', () => {
  it.each([
    // UTC 07:00 = Moscow 10:00
    ['2026-06-01T07:00:00',      '01.06.2026, 10:00'],
    // UTC 21:00 May 31 = Moscow midnight June 1 — both date and time change
    ['2026-05-31T21:00:00',      '01.06.2026, 00:00'],
    // Same with explicit Z
    ['2026-05-31T21:00:00.000Z', '01.06.2026, 00:00'],
    // UTC 00:00 June 1 = Moscow 03:00 June 1
    ['2026-06-01T00:00:00',      '01.06.2026, 03:00'],
    // Year boundary: UTC 21:00 Dec 31 = Moscow midnight Jan 1 2026
    ['2025-12-31T21:00:00',      '01.01.2026, 00:00'],
  ])('displays %s as %s in Moscow', (utcIso, expectedDateTime) => {
    expect(formatDateTime(utcIso)).toBe(expectedDateTime)
  })

  it.each([null, undefined])('returns "—" for %s', (falsy) => {
    expect(formatDateTime(falsy)).toBe('—')
  })
})

// ── Round-trip: Moscow input → UTC → Moscow display ──────────────────────────
//
// localInputToUtcIso(input) → utcIsoToLocalInput(result) must recover the original input.
// This validates the full client→server→client timezone pipeline.

describe('round-trip: localInputToUtcIso → utcIsoToLocalInput', () => {
  it.each([
    '2026-06-01T00:00',   // Moscow midnight
    '2026-06-01T03:00',   // Moscow 3am = UTC midnight
    '2026-06-30T23:59',   // last minute of Moscow-June
    '2026-01-01T00:00',   // year boundary
    '2026-06-15T12:00',   // midday
  ])('recovers original input for %s', (moscowInput) => {
    const utc = localInputToUtcIso(moscowInput)
    const recovered = utcIsoToLocalInput(utc)
    expect(recovered).toBe(moscowInput)
  })
})

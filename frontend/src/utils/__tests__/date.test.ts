import { describe, it, expect } from 'vitest'
import { prevMonth, nextMonth, formatMonthYear, monthDateRange, localDayBoundaryToUtcIso } from '../date'

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

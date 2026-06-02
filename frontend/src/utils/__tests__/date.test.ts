import { describe, it, expect } from 'vitest'
import { prevMonth, nextMonth, formatMonthYear, monthDateRange } from '../date'

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

describe('monthDateRange', () => {
  it('returns date_from as first day of month', () => {
    const { date_from } = monthDateRange('2026-06')
    expect(date_from).toBe('2026-06-01T00:00:00')
  })

  it('returns date_to as last day of June', () => {
    const { date_to } = monthDateRange('2026-06')
    expect(date_to).toBe('2026-06-30T23:59:59')
  })

  it('returns correct last day for February in non-leap year', () => {
    const { date_to } = monthDateRange('2025-02')
    expect(date_to).toBe('2025-02-28T23:59:59')
  })

  it('returns correct last day for February in leap year', () => {
    const { date_to } = monthDateRange('2024-02')
    expect(date_to).toBe('2024-02-29T23:59:59')
  })

  it('returns correct last day for January (31 days)', () => {
    const { date_to } = monthDateRange('2026-01')
    expect(date_to).toBe('2026-01-31T23:59:59')
  })
})

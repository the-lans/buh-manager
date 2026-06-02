import { describe, it, expect } from 'vitest'
import { prevMonth, nextMonth, monthBoundsUtc, formatMonthLabel } from '../date'

describe('prevMonth', () => {
  it('returns previous month in same year', () => {
    expect(prevMonth('2026-05')).toBe('2026-04')
  })

  it('wraps back to December of previous year', () => {
    expect(prevMonth('2026-01')).toBe('2025-12')
  })

  it('handles mid-year correctly', () => {
    expect(prevMonth('2026-07')).toBe('2026-06')
  })
})

describe('nextMonth', () => {
  it('returns next month in same year', () => {
    expect(nextMonth('2026-05')).toBe('2026-06')
  })

  it('wraps forward to January of next year', () => {
    expect(nextMonth('2026-12')).toBe('2027-01')
  })

  it('handles mid-year correctly', () => {
    expect(nextMonth('2026-03')).toBe('2026-04')
  })
})

describe('monthBoundsUtc', () => {
  it('returns first day of month as start_date', () => {
    const { start_date } = monthBoundsUtc('2026-05')
    expect(start_date).toBe('2026-05-01T00:00:00.000Z')
  })

  it('returns first day of next month as end_date', () => {
    const { end_date } = monthBoundsUtc('2026-05')
    expect(end_date).toBe('2026-06-01T00:00:00.000Z')
  })

  it('handles December correctly (end_date wraps to next year)', () => {
    const { start_date, end_date } = monthBoundsUtc('2026-12')
    expect(start_date).toBe('2026-12-01T00:00:00.000Z')
    expect(end_date).toBe('2027-01-01T00:00:00.000Z')
  })

  it('handles January correctly', () => {
    const { start_date, end_date } = monthBoundsUtc('2026-01')
    expect(start_date).toBe('2026-01-01T00:00:00.000Z')
    expect(end_date).toBe('2026-02-01T00:00:00.000Z')
  })

  it('end_date is strictly greater than start_date', () => {
    const { start_date, end_date } = monthBoundsUtc('2026-06')
    expect(new Date(end_date) > new Date(start_date)).toBe(true)
  })
})

describe('formatMonthLabel', () => {
  it('formats January correctly', () => {
    expect(formatMonthLabel('2026-01')).toBe('Январь 2026')
  })

  it('formats May correctly', () => {
    expect(formatMonthLabel('2026-05')).toBe('Май 2026')
  })

  it('formats December correctly', () => {
    expect(formatMonthLabel('2025-12')).toBe('Декабрь 2025')
  })

  it('formats all 12 months without throwing', () => {
    const months = ['01','02','03','04','05','06','07','08','09','10','11','12']
    for (const m of months) {
      expect(() => formatMonthLabel(`2026-${m}`)).not.toThrow()
    }
  })
})

describe('prevMonth + nextMonth round-trip', () => {
  it('next(prev(m)) === m for any month', () => {
    const months = ['2026-01', '2026-06', '2026-12', '2025-01']
    for (const m of months) {
      expect(nextMonth(prevMonth(m))).toBe(m)
    }
  })

  it('prev(next(m)) === m for any month', () => {
    const months = ['2026-01', '2026-06', '2026-12', '2025-12']
    for (const m of months) {
      expect(prevMonth(nextMonth(m))).toBe(m)
    }
  })
})

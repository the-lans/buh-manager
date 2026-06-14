import type { MissingReceiptItem, UnmatchedReceiptItem } from '../types'

const MS_PER_HOUR = 3_600_000
const HOURS_PER_DAY = 24
const KOPECKS_PER_RUBLE = 100

export interface ReceiptOption {
  id: string
  paid_at: string
  total_amount: string
}

export interface TransactionOption {
  id: string
  occurred_at: string
  amount: string
}

/** Convert a decimal money string to an integer number of kopecks to avoid IEEE 754 drift. */
export function toKopecks(value: string): number {
  return Math.round(Math.abs(Number(value)) * KOPECKS_PER_RUBLE)
}

export function amountWithinTolerance(a: string, b: string, tol: number): boolean {
  return Math.abs(toKopecks(a) - toKopecks(b)) <= Math.round(tol * KOPECKS_PER_RUBLE)
}

export function filterReceiptsForTx(
  item: MissingReceiptItem,
  options: ReceiptOption[],
  tol: number,
  preHours: number,
  postDays: number,
): ReceiptOption[] {
  const txMs = Date.parse(item.occurred_at)
  return options.filter((r) => {
    const diffH = (txMs - Date.parse(r.paid_at)) / MS_PER_HOUR
    return (
      diffH >= -preHours &&
      diffH <= postDays * HOURS_PER_DAY &&
      amountWithinTolerance(item.amount, r.total_amount, tol)
    )
  })
}

export function filterTxsForReceipt(
  item: UnmatchedReceiptItem,
  options: TransactionOption[],
  tol: number,
  preHours: number,
  postDays: number,
): TransactionOption[] {
  const rMs = Date.parse(item.paid_at)
  return options.filter((tx) => {
    const diffH = (Date.parse(tx.occurred_at) - rMs) / MS_PER_HOUR
    return (
      diffH >= -preHours &&
      diffH <= postDays * HOURS_PER_DAY &&
      amountWithinTolerance(tx.amount, item.total_amount, tol)
    )
  })
}

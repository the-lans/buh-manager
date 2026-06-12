import { useState } from 'react'

import {
  useIgnoreTransaction,
  useManualMatch,
  useReconciliationReport,
  useRunReconciliation,
} from '../hooks/useReconciliation'
import { useReceipts } from '../hooks/useReceipts'
import { useTransactions } from '../hooks/useTransactions'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import { useCounterpartyMap } from '../hooks/useCounterparties'
import { formatDate } from '../utils/date'
import { extractApiError } from '../utils/errors'
import { DataTable } from '../components/DataTable'

const RECON_PAGE = 20

export default function Reconciliation() {
  const { data: report } = useReconciliationReport()
  const runRecon = useRunReconciliation()
  const ignoreTx = useIgnoreTransaction()
  const manualMatch = useManualMatch()

  const { data: availableReceipts = [] } = useReceipts({ unmatched: true, max_age_days: 60 })
  const { data: availableTxs = [] } = useTransactions({ reconciled_status: 'UNMATCHED', limit: 200 })
  const { data: expenseTypes = [] } = useExpenseTypes()
  const counterpartyMap = useCounterpartyMap()

  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))

  const [ignoreError, setIgnoreError] = useState<string | null>(null)
  const [matchError, setMatchError] = useState<string | null>(null)

  const [missingSkip, setMissingSkip] = useState(0)
  const [unmatchedSkip, setUnmatchedSkip] = useState(0)

  // Per-row selection state: transaction_id → receipt_id
  const [receiptForTx, setReceiptForTx] = useState<Record<string, string>>({})
  // Per-row selection state: receipt_id → transaction_id
  const [txForReceipt, setTxForReceipt] = useState<Record<string, string>>({})

  const missingPage = report?.missing_receipts.slice(missingSkip, missingSkip + RECON_PAGE) ?? []
  const unmatchedPage = report?.unmatched_receipts.slice(unmatchedSkip, unmatchedSkip + RECON_PAGE) ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Сверка</h1>
        <button
          onClick={() => runRecon.mutate()}
          disabled={runRecon.isPending}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {runRecon.isPending ? 'Выполняется...' : 'Запустить сверку'}
        </button>
      </div>

      {report && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Kpi label="Автосовпадений" value={report.summary.auto_matched_count} />
            <Kpi label="Без чека" value={report.summary.missing_receipts_count} warning />
            <Kpi label="Нематчед чеки" value={report.summary.unmatched_receipts_count} />
            <Kpi label="Коллизии" value={report.summary.collisions_count} warning />
          </div>

          {report.missing_receipts.length > 0 && (
            <section>
              <h2 className="text-base font-medium text-gray-700 mb-2">Транзакции без чека</h2>
              <DataTable
                columns={[
                  { label: 'Дата' },
                  { label: 'Вид расхода' },
                  { label: 'Сумма', align: 'right' },
                  { label: 'Чек' },
                  { label: '' },
                ]}
              >
                {missingPage.map((item) => (
                  <tr key={item.transaction_id}>
                    <td className="px-4 py-2 text-gray-600">{formatDate(item.occurred_at)}</td>
                    <td className="px-4 py-2 text-gray-700 text-sm">
                      {item.expense_type_id
                        ? (expenseTypeMap.get(item.expense_type_id) ?? item.expense_type_id)
                        : '—'}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-red-600 font-medium">
                      {Number(item.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={receiptForTx[item.transaction_id] ?? ''}
                        onChange={(e) =>
                          setReceiptForTx((s) => ({ ...s, [item.transaction_id]: e.target.value }))
                        }
                        className="border border-gray-300 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 max-w-[200px]"
                      >
                        <option value="">— выбрать —</option>
                        {availableReceipts.map((r) => (
                          <option key={r.id} value={r.id}>
                            {formatDate(r.paid_at)} —{' '}
                            {Number(r.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() =>
                            manualMatch
                              .mutateAsync({
                                transactionId: item.transaction_id,
                                receiptId: receiptForTx[item.transaction_id],
                              })
                              .then(() =>
                                setReceiptForTx((s) => { const n = { ...s }; delete n[item.transaction_id]; return n })
                              )
                              .catch((e: unknown) =>
                                setMatchError(extractApiError(e, 'Не удалось сопоставить.'))
                              )
                          }
                          disabled={!receiptForTx[item.transaction_id] || manualMatch.isPending}
                          className="text-xs text-indigo-600 hover:underline disabled:opacity-40"
                        >
                          Сопоставить
                        </button>
                        <button
                          onClick={() =>
                            ignoreTx
                              .mutateAsync(item.transaction_id)
                              .catch((e: unknown) =>
                                setIgnoreError(extractApiError(e, 'Не удалось игнорировать транзакцию.'))
                              )
                          }
                          disabled={ignoreTx.isPending}
                          className="text-xs text-gray-500 hover:underline disabled:opacity-50"
                        >
                          Игнорировать
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </DataTable>
              {report.missing_receipts.length > RECON_PAGE && (
                <div className="flex items-center gap-3 mt-2">
                  <button
                    onClick={() => setMissingSkip((s) => Math.max(0, s - RECON_PAGE))}
                    disabled={missingSkip === 0}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                  >
                    ← Назад
                  </button>
                  <button
                    onClick={() => setMissingSkip((s) => s + RECON_PAGE)}
                    disabled={missingPage.length < RECON_PAGE}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                  >
                    Вперёд →
                  </button>
                </div>
              )}
            </section>
          )}

          {report.unmatched_receipts.length > 0 && (
            <section>
              <h2 className="text-base font-medium text-gray-700 mb-2">Чеки без транзакции</h2>
              <DataTable
                columns={[
                  { label: 'Дата' },
                  { label: 'Контрагент' },
                  { label: 'Сумма', align: 'right' },
                  { label: 'Транзакция' },
                  { label: '' },
                ]}
              >
                {unmatchedPage.map((item) => (
                  <tr key={item.receipt_id}>
                    <td className="px-4 py-2 text-gray-600">{formatDate(item.paid_at)}</td>
                    <td className="px-4 py-2 text-gray-700 text-sm">
                      {item.counterparty_id
                        ? (counterpartyMap.get(item.counterparty_id) ?? item.counterparty_id)
                        : '—'}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-gray-900 font-medium">
                      {Number(item.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={txForReceipt[item.receipt_id] ?? ''}
                        onChange={(e) =>
                          setTxForReceipt((s) => ({ ...s, [item.receipt_id]: e.target.value }))
                        }
                        className="border border-gray-300 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 max-w-[200px]"
                      >
                        <option value="">— выбрать —</option>
                        {availableTxs.map((tx) => (
                          <option key={tx.id} value={tx.id}>
                            {formatDate(tx.occurred_at)} —{' '}
                            {Number(tx.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() =>
                          manualMatch
                            .mutateAsync({
                              transactionId: txForReceipt[item.receipt_id],
                              receiptId: item.receipt_id,
                            })
                            .then(() =>
                              setTxForReceipt((s) => { const n = { ...s }; delete n[item.receipt_id]; return n })
                            )
                            .catch((e: unknown) =>
                              setMatchError(extractApiError(e, 'Не удалось сопоставить.'))
                            )
                        }
                        disabled={!txForReceipt[item.receipt_id] || manualMatch.isPending}
                        className="text-xs text-indigo-600 hover:underline disabled:opacity-40"
                      >
                        Сопоставить
                      </button>
                    </td>
                  </tr>
                ))}
              </DataTable>
              {report.unmatched_receipts.length > RECON_PAGE && (
                <div className="flex items-center gap-3 mt-2">
                  <button
                    onClick={() => setUnmatchedSkip((s) => Math.max(0, s - RECON_PAGE))}
                    disabled={unmatchedSkip === 0}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                  >
                    ← Назад
                  </button>
                  <button
                    onClick={() => setUnmatchedSkip((s) => s + RECON_PAGE)}
                    disabled={unmatchedPage.length < RECON_PAGE}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                  >
                    Вперёд →
                  </button>
                </div>
              )}
            </section>
          )}

          {report.collisions.length > 0 && (
            <section>
              <h2 className="text-base font-medium text-gray-700 mb-2">Коллизии</h2>
              <div className="space-y-3">
                {report.collisions.map((c) => (
                  <div key={c.collision_id} className="bg-white border border-orange-200 rounded-xl p-4">
                    <p className="text-sm text-orange-700 mb-2">{c.message}</p>
                    <div className="text-xs text-gray-500">
                      {c.involved_transactions.length} транзакций · {c.involved_receipts.length} чеков
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {ignoreError && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 flex items-center justify-between text-sm text-red-700">
          {ignoreError}
          <button onClick={() => setIgnoreError(null)} className="ml-3 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {matchError && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 flex items-center justify-between text-sm text-red-700">
          {matchError}
          <button onClick={() => setMatchError(null)} className="ml-3 text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {!report && !runRecon.isPending && (
        <div className="text-center py-12 text-gray-400">
          Запустите сверку для получения отчёта
        </div>
      )}
    </div>
  )
}

function Kpi({ label, value, warning }: { label: string; value: number; warning?: boolean }) {
  return (
    <div className={`bg-white rounded-xl border p-4 ${warning && value > 0 ? 'border-yellow-300' : 'border-gray-200'}`}>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums mt-1 ${warning && value > 0 ? 'text-yellow-600' : 'text-gray-900'}`}>
        {value}
      </div>
    </div>
  )
}

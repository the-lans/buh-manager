import { useState } from 'react'

import {
  useIgnoreTransaction,
  useReconciliationReport,
  useRunReconciliation,
} from '../hooks/useReconciliation'
import { formatDate } from '../utils/date'
import { DataTable } from '../components/DataTable'

export default function Reconciliation() {
  const { data: report } = useReconciliationReport()
  const runRecon = useRunReconciliation()
  const ignoreTx = useIgnoreTransaction()
  const [ignoreError, setIgnoreError] = useState<string | null>(null)

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
                  { label: 'Сумма', align: 'right' },
                  { label: '' },
                ]}
              >
                {report.missing_receipts.map((item) => (
                  <tr key={item.transaction_id}>
                    <td className="px-4 py-2 text-gray-600">{formatDate(item.occurred_at)}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-red-600 font-medium">
                      {Number(item.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() =>
                          ignoreTx.mutateAsync(item.transaction_id).catch((e: unknown) => {
                            const detail =
                              (e as { response?: { data?: { detail?: string } } })?.response?.data
                                ?.detail
                            setIgnoreError(detail ?? 'Не удалось игнорировать транзакцию.')
                          })
                        }
                        disabled={ignoreTx.isPending}
                        className="text-xs text-gray-500 hover:underline disabled:opacity-50"
                      >
                        Игнорировать
                      </button>
                    </td>
                  </tr>
                ))}
              </DataTable>
            </section>
          )}

          {report.unmatched_receipts.length > 0 && (
            <section>
              <h2 className="text-base font-medium text-gray-700 mb-2">Чеки без транзакции</h2>
              <DataTable
                columns={[
                  { label: 'Дата' },
                  { label: 'Сумма', align: 'right' },
                ]}
              >
                {report.unmatched_receipts.map((item) => (
                  <tr key={item.receipt_id}>
                    <td className="px-4 py-2 text-gray-600">{formatDate(item.paid_at)}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-gray-900 font-medium">
                      {Number(item.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                  </tr>
                ))}
              </DataTable>
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

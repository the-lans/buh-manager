import { useTransactions } from '../hooks/useTransactions'
import { useAccounts } from '../hooks/useAccounts'
import { useReconciliationReport } from '../hooks/useReconciliation'
import { currentYearMonth, formatDate } from '../utils/date'

export default function Dashboard() {
  const { data: transactions = [] } = useTransactions({ limit: 100 })
  const { data: accounts = [] } = useAccounts()
  const { data: report } = useReconciliationReport()

  const unmatched = transactions.filter((t) => t.reconciled_status === 'UNMATCHED').length
  const conflicts = report?.summary.collisions_count ?? 0

  const currentMonth = currentYearMonth()
  const monthlyExpenses = transactions
    .filter((t) => t.type === 'EXPENSE' && t.occurred_at.startsWith(currentMonth))
    .reduce((sum, t) => sum + Math.abs(Number(t.amount)), 0)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Дашборд</h1>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Расходы за месяц" value={`${monthlyExpenses.toLocaleString('ru')} ₽`} />
        <KpiCard label="Счета" value={`${accounts.filter((a) => a.is_active).length} активных`} />
        <KpiCard label="Несверено" value={String(unmatched)} warning={unmatched > 0} />
        <KpiCard label="Конфликты" value={String(conflicts)} warning={conflicts > 0} />
      </div>
      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">Последние транзакции</h2>
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Дата</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Контрагент</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600 tabular-nums">Сумма</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.slice(0, 10).map((tx) => (
                <tr key={tx.id}>
                  <td className="px-4 py-2 text-gray-600">{formatDate(tx.occurred_at)}</td>
                  <td className="px-4 py-2 text-gray-800">{tx.counterparty_id ?? '—'}</td>
                  <td className={`px-4 py-2 text-right tabular-nums font-medium ${Number(tx.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {Number(tx.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={tx.reconciled_status} />
                  </td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    Нет транзакций
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function KpiCard({ label, value, warning }: { label: string; value: string; warning?: boolean }) {
  return (
    <div className={`bg-white rounded-xl border p-4 ${warning ? 'border-yellow-300' : 'border-gray-200'}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums ${warning ? 'text-yellow-600' : 'text-gray-900'}`}>
        {value}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    UNMATCHED: 'bg-yellow-100 text-yellow-700',
    MATCHED: 'bg-green-100 text-green-700',
    NOT_REQUIRED: 'bg-gray-100 text-gray-500',
    IGNORED_BY_USER: 'bg-gray-100 text-gray-400',
  }
  const labels: Record<string, string> = {
    UNMATCHED: 'Не сверено',
    MATCHED: 'Сверено',
    NOT_REQUIRED: 'Не требуется',
    IGNORED_BY_USER: 'Игнорируется',
  }
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${map[status] ?? ''}`}>
      {labels[status] ?? status}
    </span>
  )
}

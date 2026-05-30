import { useTransactions } from '../hooks/useTransactions'
import { useAccounts } from '../hooks/useAccounts'
import { useReconciliationReport } from '../hooks/useReconciliation'
import { currentYearMonth, formatDate } from '../utils/date'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

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
        <DataTable
          columns={[
            { label: 'Дата' },
            { label: 'Контрагент' },
            { label: 'Сумма', align: 'right' },
            { label: 'Статус' },
          ]}
          isEmpty={transactions.length === 0}
          emptyMessage="Нет транзакций"
        >
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
        </DataTable>
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

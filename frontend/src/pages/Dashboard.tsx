import { useAccounts } from '../hooks/useAccounts'
import { useBalances } from '../hooks/useBalances'
import { useTransactions } from '../hooks/useTransactions'
import { useReconciliationReport } from '../hooks/useReconciliation'
import { currentYearMonth, formatDate } from '../utils/date'
import { DataTable } from '../components/DataTable'
import type { Balance } from '../types'

const SOURCE_LABELS: Record<string, string> = {
  OPENING: 'Входящий',
  CLOSING: 'Исходящий',
  MANUAL: 'Ручной',
}

export default function Dashboard() {
  const { data: transactions = [] } = useTransactions({ limit: 100 })
  const { data: accounts = [] } = useAccounts()
  const { data: report } = useReconciliationReport()
  const { data: balances = [] } = useBalances({ limit: 200 })

  const unmatched = transactions.filter((t) => t.reconciled_status === 'UNMATCHED').length
  const conflicts = report?.summary.collisions_count ?? 0

  const currentMonth = currentYearMonth()
  const monthlyExpenses = transactions
    .filter((t) => t.type === 'EXPENSE' && t.occurred_at.startsWith(currentMonth))
    .reduce((sum, t) => sum + Math.abs(Number(t.amount)), 0)

  // Latest balance per account (balances are sorted by recorded_at DESC from API)
  const latestByAccount = new Map<string, Balance>()
  for (const b of balances) {
    if (!latestByAccount.has(b.account_id)) {
      latestByAccount.set(b.account_id, b)
    }
  }
  const latestBalances = Array.from(latestByAccount.values())

  const accountMap = new Map(accounts.map((a) => [a.id, a]))

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
        <h2 className="text-base font-medium text-gray-700 mb-3">Остатки на счетах</h2>
        <DataTable
          columns={[
            { label: 'Счёт' },
            { label: 'Дата' },
            { label: 'Сумма', align: 'right' },
            { label: 'Тип' },
          ]}
          isEmpty={latestBalances.length === 0}
          emptyMessage="Нет данных об остатках"
        >
          {latestBalances.map((b) => {
            const acc = accountMap.get(b.account_id)
            const accLabel = acc ? `${acc.bank} ···${acc.account_number.slice(-4)}` : b.account_id
            return (
              <tr key={b.id}>
                <td className="px-4 py-2 text-gray-800">{accLabel}</td>
                <td className="px-4 py-2 text-gray-600">{formatDate(b.recorded_at)}</td>
                <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
                  {Number(b.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                </td>
                <td className="px-4 py-2 text-gray-600 text-sm">
                  {SOURCE_LABELS[b.source] ?? b.source}
                </td>
              </tr>
            )
          })}
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

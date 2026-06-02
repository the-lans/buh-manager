import { useMemo, useState } from 'react'

import { DataTable } from '../components/DataTable'
import { useAccounts } from '../hooks/useAccounts'
import { useBalances } from '../hooks/useBalances'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import { useReconciliationReport } from '../hooks/useReconciliation'
import { useTransactions } from '../hooks/useTransactions'
import {
  currentYearMonth,
  formatDate,
  formatMonthLabel,
  monthBoundsUtc,
  nextMonth,
  prevMonth,
} from '../utils/date'
import type { Balance } from '../types'

const SOURCE_LABELS: Record<string, string> = {
  OPENING: 'Входящий',
  CLOSING: 'Исходящий',
  MANUAL: 'Ручной',
}

export default function Dashboard() {
  const [selectedMonth, setSelectedMonth] = useState(currentYearMonth)
  const isCurrentMonth = selectedMonth === currentYearMonth()

  const { start_date, end_date } = monthBoundsUtc(selectedMonth)
  const { data: transactions = [] } = useTransactions({ start_date, end_date, limit: 500 })
  const { data: accounts = [] } = useAccounts()
  const { data: report } = useReconciliationReport()
  const { data: allBalances = [] } = useBalances({ limit: 500 })
  const { data: expenseTypes = [] } = useExpenseTypes()

  const unmatched = transactions.filter((t) => t.reconciled_status === 'UNMATCHED').length
  const conflicts = report?.summary.collisions_count ?? 0

  const monthlyExpenses = transactions
    .filter((t) => t.type === 'EXPENSE')
    .reduce((sum, t) => sum + Math.abs(Number(t.amount)), 0)

  // Balances for selected month
  const monthBalances = allBalances.filter((b) => b.recorded_at.startsWith(selectedMonth))
  const latestByAccount = new Map<string, Balance>()
  for (const b of monthBalances) {
    const existing = latestByAccount.get(b.account_id)
    if (!existing || b.recorded_at > existing.recorded_at) {
      latestByAccount.set(b.account_id, b)
    }
  }
  const latestBalances = Array.from(latestByAccount.values())
  const accountMap = new Map(accounts.map((a) => [a.id, a]))

  // Expense type breakdown
  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))
  const expenseByType = useMemo(() => {
    const totals = new Map<string | null, number>()
    for (const tx of transactions) {
      if (tx.type !== 'EXPENSE') continue
      const key = tx.expense_type_id ?? null
      totals.set(key, (totals.get(key) ?? 0) + Math.abs(Number(tx.amount)))
    }
    return Array.from(totals.entries())
      .map(([id, total]) => ({
        id,
        name: id ? (expenseTypeMap.get(id) ?? id) : 'Без категории',
        total,
      }))
      .sort((a, b) => b.total - a.total)
  }, [transactions, expenseTypeMap])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Дашборд</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedMonth((m) => prevMonth(m))}
            className="p-1.5 rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-900"
            aria-label="Предыдущий месяц"
          >
            ←
          </button>
          <span className="text-sm font-medium text-gray-700 min-w-28 text-center">
            {formatMonthLabel(selectedMonth)}
          </span>
          <button
            onClick={() => setSelectedMonth((m) => nextMonth(m))}
            disabled={isCurrentMonth}
            className="p-1.5 rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Следующий месяц"
          >
            →
          </button>
        </div>
      </div>

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
          emptyMessage="Нет данных об остатках за этот месяц"
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

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">Расходы по типам</h2>
        <DataTable
          columns={[
            { label: 'Тип трат' },
            { label: 'Сумма', align: 'right' },
          ]}
          isEmpty={expenseByType.length === 0}
          emptyMessage="Нет расходов за этот месяц"
        >
          {expenseByType.map(({ id, name, total }) => (
            <tr key={id ?? '__none__'}>
              <td className="px-4 py-2 text-gray-800">{name}</td>
              <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
                {total.toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
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

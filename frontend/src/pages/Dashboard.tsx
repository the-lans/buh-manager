import { useState } from 'react'

import { useAccounts } from '../hooks/useAccounts'
import { useBalances } from '../hooks/useBalances'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import { useReconciliationReport } from '../hooks/useReconciliation'
import { useTransactions } from '../hooks/useTransactions'
import {
  currentYearMonth,
  formatDate,
  formatMonthYear,
  monthDateRange,
  nextMonth,
  prevMonth,
} from '../utils/date'
import { DataTable } from '../components/DataTable'
import type { Balance } from '../types'

const SOURCE_LABELS: Record<string, string> = {
  OPENING: 'Входящий',
  CLOSING: 'Исходящий',
  MANUAL: 'Ручной',
}

export default function Dashboard() {
  const [selectedMonth, setSelectedMonth] = useState(currentYearMonth)
  const { start_date, end_date } = monthDateRange(selectedMonth)

  const { data: transactions = [] } = useTransactions({ start_date, end_date, limit: 500 })
  const { data: accounts = [] } = useAccounts()
  const { data: report } = useReconciliationReport()
  const { data: balances = [] } = useBalances({ limit: 200 })
  const { data: expenseTypes = [] } = useExpenseTypes()

  const unmatched = transactions.filter((t) => t.reconciled_status === 'UNMATCHED').length
  const conflicts = report?.summary.collisions_count ?? 0

  const monthlyExpenses = transactions
    .filter((t) => t.type === 'EXPENSE')
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

  // Expense types table: group EXPENSE transactions by expense_type_id
  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))
  const expenseByType = new Map<string | null, { count: number; total: number }>()
  for (const t of transactions) {
    if (t.type !== 'EXPENSE') continue
    const key = t.expense_type_id ?? null
    const cur = expenseByType.get(key) ?? { count: 0, total: 0 }
    expenseByType.set(key, { count: cur.count + 1, total: cur.total + Math.abs(Number(t.amount)) })
  }
  const expenseTypeRows = Array.from(expenseByType.entries())
    .map(([id, { count, total }]) => ({ id, name: id ? (expenseTypeMap.get(id) ?? id) : 'Не задан', count, total }))
    .sort((a, b) => b.total - a.total)

  const canGoNext = selectedMonth < currentYearMonth()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setSelectedMonth((m) => prevMonth(m))}
          className="p-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 text-sm leading-none shrink-0"
          aria-label="Предыдущий месяц"
        >
          ←
        </button>
        <h1 className="text-xl font-semibold text-gray-900 flex-1 text-center whitespace-nowrap">
          {formatMonthYear(selectedMonth)}
        </h1>
        <button
          onClick={() => setSelectedMonth((m) => nextMonth(m))}
          disabled={!canGoNext}
          className="p-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 text-sm leading-none disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
          aria-label="Следующий месяц"
        >
          →
        </button>
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

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">Типы расходов</h2>
        <DataTable
          columns={[
            { label: 'Вид расхода' },
            { label: 'Операций', align: 'right' },
            { label: 'Сумма', align: 'right' },
          ]}
          isEmpty={expenseTypeRows.length === 0}
          emptyMessage="Нет расходов за период"
        >
          {expenseTypeRows.map((row) => (
            <tr key={row.id ?? '__none__'}>
              <td className="px-4 py-2 text-gray-800">{row.name}</td>
              <td className="px-4 py-2 text-right tabular-nums text-gray-600">{row.count}</td>
              <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
                {row.total.toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
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

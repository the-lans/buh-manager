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

  // Latest balance per account as of end of selected month
  // Balances are sorted by recorded_at DESC from API, so first match per account is the latest
  const latestByAccount = new Map<string, Balance>()
  for (const b of balances) {
    if (b.recorded_at <= end_date && !latestByAccount.has(b.account_id)) {
      latestByAccount.set(b.account_id, b)
    }
  }
  const latestBalances = Array.from(latestByAccount.values())

  const accountMap = new Map(accounts.map((a) => [a.id, a]))

  // Expense types table: group EXPENSE transactions by expense_type_id
  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))
  const expenseByType = new Map<string, { count: number; total: number }>()
  for (const t of transactions) {
    if (t.type !== 'EXPENSE' || !t.expense_type_id) continue
    const cur = expenseByType.get(t.expense_type_id) ?? { count: 0, total: 0 }
    expenseByType.set(t.expense_type_id, { count: cur.count + 1, total: cur.total + Math.abs(Number(t.amount)) })
  }
  const expenseTypeRows = Array.from(expenseByType.entries())
    .map(([id, { count, total }]) => ({ id, name: expenseTypeMap.get(id) ?? id, count, total }))
    .sort((a, b) => b.total - a.total)

  const canGoNext = selectedMonth < currentYearMonth()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Дашборд</h1>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setSelectedMonth((m) => prevMonth(m))}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-lg font-medium leading-none shrink-0"
            aria-label="Предыдущий месяц"
          >
            ‹
          </button>
          <span className="px-3 text-base font-semibold text-gray-900 whitespace-nowrap select-none min-w-[140px] text-center">
            {formatMonthYear(selectedMonth)}
          </span>
          <button
            onClick={() => setSelectedMonth((m) => nextMonth(m))}
            disabled={!canGoNext}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-lg font-medium leading-none disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
            aria-label="Следующий месяц"
          >
            ›
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
            <tr key={row.id}>
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

import { useState } from 'react'

import { DataTable } from '../components/DataTable'
import { useAccounts } from '../hooks/useAccounts'
import { useBalances } from '../hooks/useBalances'
import { formatDate } from '../utils/date'

const PAGE_SIZE = 20

const SOURCE_LABELS: Record<string, string> = {
  OPENING: 'Начальный',
  CLOSING: 'Конечный',
  MANUAL: 'Ручной',
}

export default function Balances() {
  const [accountId, setAccountId] = useState('')
  const [skip, setSkip] = useState(0)

  const { data: accounts = [] } = useAccounts()
  const { data: balances = [], isLoading } = useBalances({
    account_id: accountId || undefined,
    skip,
    limit: PAGE_SIZE,
  })

  const accountMap = new Map(accounts.map((a) => [a.id, `${a.bank} ···${a.account_number.slice(-4)}`]))

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Остатки по счетам</h1>

      <div className="flex gap-3 flex-wrap">
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={accountId}
          onChange={(e) => { setAccountId(e.target.value); setSkip(0) }}
        >
          <option value="">Все счета</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.bank} ···{a.account_number.slice(-4)}
            </option>
          ))}
        </select>
      </div>

      <DataTable
        columns={[
          { label: 'Счёт' },
          { label: 'Дата' },
          { label: 'Сумма', align: 'right' },
          { label: 'Тип' },
        ]}
        isEmpty={balances.length === 0}
        emptyMessage="Нет остатков"
        isLoading={isLoading}
      >
        {balances.map((b) => (
          <tr key={b.id} className="hover:bg-gray-50">
            <td className="px-4 py-2 text-gray-800">
              {accountMap.get(b.account_id) ?? b.account_id}
            </td>
            <td className="px-4 py-2 text-gray-600">{formatDate(b.recorded_at)}</td>
            <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
              {Number(b.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
            </td>
            <td className="px-4 py-2 text-gray-600 text-sm">
              {SOURCE_LABELS[b.source] ?? b.source}
            </td>
          </tr>
        ))}
      </DataTable>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
          disabled={skip === 0}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
        >
          ← Назад
        </button>
        <button
          onClick={() => setSkip((s) => s + PAGE_SIZE)}
          disabled={balances.length < PAGE_SIZE}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
        >
          Вперёд →
        </button>
      </div>
    </div>
  )
}

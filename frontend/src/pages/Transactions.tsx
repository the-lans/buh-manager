import { useState } from 'react'
import { useTransactions, useCreateTransaction, useDeleteTransaction } from '../hooks/useTransactions'
import { useAccounts } from '../hooks/useAccounts'
import type { TransactionFilters } from '../api/transactions'
import { formatDate, localInputToUtcIso } from '../utils/date'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'

export default function Transactions() {
  const [filters, setFilters] = useState<TransactionFilters>({ limit: 50 })
  const { data: transactions = [], isLoading } = useTransactions(filters)
  const { data: accounts = [] } = useAccounts()
  const createTx = useCreateTransaction()
  const deleteTx = useDeleteTransaction()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ account_id: '', occurred_at: '', amount: '', type: 'EXPENSE' })

  const handleCreate = async () => {
    await createTx.mutateAsync({
      account_id: form.account_id,
      occurred_at: localInputToUtcIso(form.occurred_at),
      amount: form.amount as unknown as string,
      type: form.type as 'INCOME' | 'EXPENSE',
    })
    setShowForm(false)
    setForm({ account_id: '', occurred_at: '', amount: '', type: 'EXPENSE' })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Транзакции</h1>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          + Добавить
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filters.type ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value || undefined }))}
        >
          <option value="">Все типы</option>
          <option value="INCOME">Доход</option>
          <option value="EXPENSE">Расход</option>
        </select>
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filters.reconciled_status ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, reconciled_status: e.target.value || undefined }))}
        >
          <option value="">Все статусы</option>
          <option value="UNMATCHED">Не сверено</option>
          <option value="MATCHED">Сверено</option>
          <option value="IGNORED_BY_USER">Игнорируется</option>
        </select>
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filters.account_id ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, account_id: e.target.value || undefined }))}
        >
          <option value="">Все счета</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.bank} {a.account_number.slice(-4)}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3 max-w-md">
          <h2 className="font-medium text-gray-900">Новая транзакция</h2>
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.account_id}
            onChange={(e) => setForm((f) => ({ ...f, account_id: e.target.value }))}
          >
            <option value="">Выберите счёт</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.bank} {a.account_number.slice(-4)}</option>
            ))}
          </select>
          <input
            type="datetime-local"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.occurred_at}
            onChange={(e) => setForm((f) => ({ ...f, occurred_at: e.target.value }))}
          />
          <input
            type="number"
            placeholder="Сумма"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.amount}
            onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
          />
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.type}
            onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
          >
            <option value="EXPENSE">Расход</option>
            <option value="INCOME">Доход</option>
          </select>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createTx.isPending}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              Создать
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      <DataTable
        columns={[
          { label: 'Дата' },
          { label: 'Контрагент' },
          { label: 'Сумма', align: 'right' },
          { label: 'Тип' },
          { label: 'Статус' },
          { label: '' },
        ]}
        isEmpty={transactions.length === 0}
        emptyMessage="Нет транзакций"
        isLoading={isLoading}
      >
        {transactions.map((tx) => (
          <tr key={tx.id}>
            <td className="px-4 py-2 text-gray-600">{formatDate(tx.occurred_at)}</td>
            <td className="px-4 py-2 text-gray-800">{tx.counterparty_id ?? '—'}</td>
            <td className={`px-4 py-2 text-right tabular-nums font-medium ${Number(tx.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {Number(tx.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
            </td>
            <td className="px-4 py-2 text-gray-600">{tx.type}</td>
            <td className="px-4 py-2">
              <StatusBadge status={tx.reconciled_status} />
            </td>
            <td className="px-4 py-2">
              <button
                onClick={() => deleteTx.mutate(tx.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Удалить
              </button>
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}

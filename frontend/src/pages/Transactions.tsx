import { useState } from 'react'
import { useTransactions, useCreateTransaction, useDeleteTransaction } from '../hooks/useTransactions'
import { useAccounts } from '../hooks/useAccounts'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import type { TransactionFilters } from '../api/transactions'
import type { Transaction } from '../types'
import { formatDate, localInputToUtcIso } from '../utils/date'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import TransactionEditModal from '../components/TransactionEditModal'

export default function Transactions() {
  const [filters, setFilters] = useState<TransactionFilters>({ limit: 50 })
  const { data: transactions = [], isLoading } = useTransactions(filters)
  const { data: accounts = [] } = useAccounts()
  const { data: expenseTypes = [] } = useExpenseTypes()
  const createTx = useCreateTransaction()
  const deleteTx = useDeleteTransaction()

  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ account_id: '', occurred_at: '', amount: '', type: 'EXPENSE', expense_type_id: '', description: '' })
  const [editTx, setEditTx] = useState<Transaction | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async () => {
    if (!form.account_id) { setCreateError('Выберите счёт'); return }
    if (!form.occurred_at) { setCreateError('Укажите дату'); return }
    if (!form.amount) { setCreateError('Укажите сумму'); return }
    if (!form.expense_type_id) { setCreateError('Выберите вид расхода'); return }
    setCreateError(null)
    try {
      await createTx.mutateAsync({
        account_id: form.account_id,
        occurred_at: localInputToUtcIso(form.occurred_at),
        amount: form.amount,
        type: form.type,
        expense_type_id: form.expense_type_id,
        description: form.description || null,
      })
      setShowForm(false)
      setForm({ account_id: '', occurred_at: '', amount: '', type: 'EXPENSE', expense_type_id: '', description: '' })
    } catch {
      setCreateError('Ошибка создания транзакции')
    }
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
          <select
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.expense_type_id}
            onChange={(e) => setForm((f) => ({ ...f, expense_type_id: e.target.value }))}
          >
            <option value="">— Вид расхода —</option>
            {expenseTypes.map((et) => (
              <option key={et.id} value={et.id}>{et.name}</option>
            ))}
          </select>
          <textarea
            rows={2}
            placeholder="Описание (необязательно)"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
          {createError && <p className="text-sm text-red-500">{createError}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createTx.isPending}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              Создать
            </button>
            <button
              onClick={() => { setShowForm(false); setCreateError(null) }}
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
          { label: 'Категория банка' },
          { label: 'Вид расхода' },
          { label: 'Описание' },
          { label: 'Сумма', align: 'right' },
          { label: 'Тип' },
          { label: 'Статус' },
          { label: 'Чек' },
          { label: 'Документ' },
          { label: '' },
        ]}
        isEmpty={transactions.length === 0}
        emptyMessage="Нет транзакций"
        isLoading={isLoading}
      >
        {transactions.map((tx) => (
          <tr key={tx.id} className="hover:bg-gray-50">
            <td className="px-4 py-2 text-gray-600">{formatDate(tx.occurred_at)}</td>
            <td className="px-4 py-2 text-gray-800">{tx.bank_category ?? '—'}</td>
            <td className="px-4 py-2 text-gray-800">{tx.expense_type_id ? (expenseTypeMap.get(tx.expense_type_id) ?? tx.expense_type_id) : '—'}</td>
            <td className="px-4 py-2 text-gray-500 text-sm max-w-[200px] truncate">{tx.description ?? '—'}</td>
            <td className={`px-4 py-2 text-right tabular-nums font-medium ${Number(tx.amount) < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {Number(tx.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
            </td>
            <td className="px-4 py-2 text-gray-600">{tx.type}</td>
            <td className="px-4 py-2">
              <StatusBadge status={tx.reconciled_status} />
            </td>
            <td className="px-4 py-2 text-center">
              {tx.receipt_id
                ? <span className="text-green-600 font-medium">✓</span>
                : <span className="text-gray-300">—</span>}
            </td>
            <td className="px-4 py-2 text-center">
              {tx.document_id
                ? <span className="text-green-600 font-medium">✓</span>
                : <span className="text-gray-300">—</span>}
            </td>
            <td className="px-4 py-2">
              {confirmDeleteId === tx.id ? (
                <span className="inline-flex items-center gap-2 text-xs">
                  <span className="text-gray-600">Удалить?</span>
                  <button
                    onClick={() => { deleteTx.mutate(tx.id); setConfirmDeleteId(null) }}
                    disabled={deleteTx.isPending}
                    className="text-red-500 hover:underline"
                  >
                    Да
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    className="text-gray-500 hover:underline"
                  >
                    Нет
                  </button>
                </span>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditTx(tx)}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Изменить
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(tx.id)}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Удалить
                  </button>
                </div>
              )}
            </td>
          </tr>
        ))}
      </DataTable>

      <TransactionEditModal key={editTx?.id ?? ''} transaction={editTx} onClose={() => setEditTx(null)} />
    </div>
  )
}

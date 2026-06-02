import { useState } from 'react'

import { useAccounts } from '../hooks/useAccounts'
import { useCounterpartyMap } from '../hooks/useCounterparties'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import { useUpdateTransaction } from '../hooks/useTransactions'
import { localInputToUtcIso, utcIsoToLocalInput } from '../utils/date'
import type { Transaction } from '../types'

interface Props {
  transaction: Transaction | null
  onClose: () => void
}

const TYPE_LABELS: Record<string, string> = {
  EXPENSE: 'Расход',
  INCOME: 'Доход',
  TRANSFER: 'Перевод',
}

const STATUS_LABELS: Record<string, string> = {
  UNMATCHED: 'Не сверено',
  MATCHED: 'Сверено',
  NOT_REQUIRED: 'Не требуется',
  IGNORED_BY_USER: 'Игнорируется',
}

export default function TransactionEditModal({ transaction, onClose }: Props) {
  const update = useUpdateTransaction()
  const { data: expenseTypes = [] } = useExpenseTypes()
  const { data: accounts = [] } = useAccounts()
  const counterpartyMap = useCounterpartyMap()

  const [form, setForm] = useState(() =>
    transaction
      ? {
          occurred_at: utcIsoToLocalInput(transaction.occurred_at),
          amount: String(transaction.amount),
          type: transaction.type,
          bank_category: transaction.bank_category ?? '',
          expense_type_id: transaction.expense_type_id ?? '',
          description: transaction.description ?? '',
          reconciled_status: transaction.reconciled_status,
        }
      : {
          occurred_at: '',
          amount: '',
          type: 'EXPENSE',
          bank_category: '',
          expense_type_id: '',
          description: '',
          reconciled_status: 'UNMATCHED',
        },
  )
  const [error, setError] = useState<string | null>(null)

  if (!transaction) return null

  const account = accounts.find((a) => a.id === transaction.account_id)
  const accountLabel = account
    ? `${account.bank} ···${account.account_number.slice(-4)}`
    : transaction.account_id

  async function handleSave() {
    if (!transaction) return
    setError(null)
    try {
      await update.mutateAsync({
        id: transaction.id,
        data: {
          occurred_at: localInputToUtcIso(form.occurred_at) as unknown as string,
          amount: Number(form.amount) as unknown as string,
          type: form.type as 'INCOME' | 'EXPENSE',
          bank_category: form.bank_category || null,
          expense_type_id: form.expense_type_id || null,
          description: form.description || null,
          reconciled_status: form.reconciled_status as Transaction['reconciled_status'],
        },
      })
      onClose()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } }
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') setError(detail)
      else setError('Ошибка сохранения')
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl p-6 w-full max-w-lg mx-4 overflow-y-auto max-h-[90vh] space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Изменить транзакцию</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            ✕
          </button>
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-2">
          <dt className="text-gray-500">Счёт</dt>
          <dd className="text-gray-700">{accountLabel}</dd>
          <dt className="text-gray-500">Контрагент</dt>
          <dd className="text-gray-700">
            {transaction.counterparty_id
              ? (counterpartyMap.get(transaction.counterparty_id) ?? transaction.counterparty_id)
              : '—'}
          </dd>
          <dt className="text-gray-500">Статус импорта</dt>
          <dd className="text-gray-700">{transaction.import_status}</dd>
        </dl>

        <div className="space-y-3">
          <Field label="Дата и время">
            <input
              type="datetime-local"
              value={form.occurred_at}
              onChange={(e) => setForm((f) => ({ ...f, occurred_at: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </Field>

          <Field label="Сумма">
            <input
              type="number"
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </Field>

          <Field label="Тип">
            <select
              value={form.type}
              onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {Object.entries(TYPE_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </Field>

          <Field label="Статус сверки">
            <select
              value={form.reconciled_status}
              onChange={(e) => setForm((f) => ({ ...f, reconciled_status: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {Object.entries(STATUS_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </Field>

          <Field label="Вид расхода">
            <select
              value={form.expense_type_id}
              onChange={(e) => setForm((f) => ({ ...f, expense_type_id: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">— не задан —</option>
              {expenseTypes.map((et) => (
                <option key={et.id} value={et.id}>{et.name}</option>
              ))}
            </select>
          </Field>

          <Field label="Категория банка">
            <input
              type="text"
              value={form.bank_category}
              onChange={(e) => setForm((f) => ({ ...f, bank_category: e.target.value }))}
              placeholder="Необязательно"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </Field>

          <Field label="Описание">
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Необязательно"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </Field>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={update.isPending}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {update.isPending ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
    </div>
  )
}

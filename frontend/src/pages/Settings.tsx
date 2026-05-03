import { useState } from 'react'
import { useAccounts, useCreateAccount, useDeleteAccount } from '../hooks/useAccounts'
import { useExpenseTypes, useCreateExpenseType, useUpdateExpenseType, useDeleteExpenseType } from '../hooks/useExpenseTypes'
import { accountsApi } from '../api/accounts'
import { useQueryClient } from '@tanstack/react-query'

type Tab = 'accounts' | 'expense-types'

export default function Settings() {
  const [tab, setTab] = useState<Tab>('accounts')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Настройки</h1>
      <div className="border-b border-gray-200 flex gap-6">
        {(['accounts', 'expense-types'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium transition-colors ${
              tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'accounts' ? 'Счета' : 'Типы расходов'}
          </button>
        ))}
      </div>
      {tab === 'accounts' && <AccountsTab />}
      {tab === 'expense-types' && <ExpenseTypesTab />}
    </div>
  )
}

function AccountsTab() {
  const { data: accounts = [] } = useAccounts()
  const createAccount = useCreateAccount()
  const deleteAccount = useDeleteAccount()
  const qc = useQueryClient()
  const [form, setForm] = useState({ bank: '', account_number: '', currency: 'RUB' })
  const [initForm, setInitForm] = useState<{ id: string; amount: string; recorded_at: string; source: 'OPENING' | 'CLOSING' } | null>(null)

  const handleCreate = async () => {
    await createAccount.mutateAsync(form)
    setForm({ bank: '', account_number: '', currency: 'RUB' })
  }

  const handleInitBalance = async () => {
    if (!initForm) return
    await accountsApi.initBalance(initForm.id, Number(initForm.amount), initForm.recorded_at, initForm.source)
    await qc.invalidateQueries({ queryKey: ['accounts'] })
    setInitForm(null)
  }

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3 max-w-md">
        <h2 className="font-medium text-gray-900">Добавить счёт</h2>
        <input
          placeholder="Банк"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.bank}
          onChange={(e) => setForm((f) => ({ ...f, bank: e.target.value }))}
        />
        <input
          placeholder="Номер счёта"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.account_number}
          onChange={(e) => setForm((f) => ({ ...f, account_number: e.target.value }))}
        />
        <input
          placeholder="Валюта (RUB)"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.currency}
          onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}
        />
        <button
          onClick={handleCreate}
          disabled={createAccount.isPending}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          Создать
        </button>
      </div>

      <div className="space-y-2">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium text-sm text-gray-900">{acc.bank}</div>
              <div className="text-xs text-gray-500">{acc.account_number} · {acc.currency}</div>
            </div>
            <div className="flex items-center gap-3">
              {!acc.has_balances && (
                <button
                  onClick={() => setInitForm({ id: acc.id, amount: '', recorded_at: '', source: 'OPENING' })}
                  className="text-xs text-yellow-600 border border-yellow-300 rounded px-2 py-1 hover:bg-yellow-50"
                >
                  ⚠ Задать баланс
                </button>
              )}
              <button
                onClick={() => deleteAccount.mutate(acc.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>

      {initForm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 space-y-3 w-80">
            <h2 className="font-medium text-gray-900">Начальный баланс</h2>
            <input
              type="number"
              placeholder="Сумма"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={initForm.amount}
              onChange={(e) => setInitForm((f) => f && { ...f, amount: e.target.value })}
            />
            <input
              type="datetime-local"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={initForm.recorded_at}
              onChange={(e) => setInitForm((f) => f && { ...f, recorded_at: e.target.value })}
            />
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={initForm.source}
              onChange={(e) => setInitForm((f) => f && { ...f, source: e.target.value as 'OPENING' | 'CLOSING' })}
            >
              <option value="OPENING">Входящий</option>
              <option value="CLOSING">Исходящий</option>
            </select>
            <div className="flex gap-2">
              <button onClick={handleInitBalance} className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg">Сохранить</button>
              <button onClick={() => setInitForm(null)} className="px-4 py-2 border border-gray-300 text-sm rounded-lg">Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ExpenseTypesTab() {
  const { data: types = [] } = useExpenseTypes()
  const createType = useCreateExpenseType()
  const updateType = useUpdateExpenseType()
  const deleteType = useDeleteExpenseType()
  const [form, setForm] = useState({ id: '', name: '', receipt_required: true })

  const handleCreate = async () => {
    await createType.mutateAsync(form)
    setForm({ id: '', name: '', receipt_required: true })
  }

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3 max-w-md">
        <h2 className="font-medium text-gray-900">Добавить тип</h2>
        <input
          placeholder="ID (slug, напр. groceries)"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.id}
          onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
        />
        <input
          placeholder="Название"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        />
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={form.receipt_required}
            onChange={(e) => setForm((f) => ({ ...f, receipt_required: e.target.checked }))}
          />
          Требуется чек
        </label>
        <button
          onClick={handleCreate}
          disabled={createType.isPending}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          Создать
        </button>
      </div>

      <div className="space-y-2">
        {types.map((t) => (
          <div key={t.id} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium text-sm text-gray-900">{t.name}</div>
              <div className="text-xs text-gray-400">{t.id}</div>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={t.receipt_required}
                  onChange={(e) => updateType.mutate({ id: t.id, data: { receipt_required: e.target.checked } })}
                />
                Чек
              </label>
              <button
                onClick={() => deleteType.mutate(t.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

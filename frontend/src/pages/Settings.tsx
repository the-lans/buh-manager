import { useState } from 'react'
import { useAccounts, useCreateAccount, useDeleteAccount, useUpdateAccount } from '../hooks/useAccounts'
import { useExpenseTypes, useCreateExpenseType, useUpdateExpenseType, useDeleteExpenseType } from '../hooks/useExpenseTypes'
import { useApiKeys, useCreateApiKey, useUpdateApiKey, useDeleteApiKey } from '../hooks/useApiKeys'
import { accountsApi } from '../api/accounts'
import { useQueryClient } from '@tanstack/react-query'
import type { Account, ApiKeyCreated, ExpenseType } from '../types'
import { formatDate, localInputToUtcIso } from '../utils/date'

type Tab = 'accounts' | 'expense-types' | 'api-keys'

const ALL_SCOPES: { scope: string; label: string; group: string }[] = [
  { scope: 'read:documents', label: 'Чтение документов', group: 'Документы' },
  { scope: 'write:documents', label: 'Загрузка документов', group: 'Документы' },
  { scope: 'read:receipts', label: 'Чтение чеков', group: 'Чеки' },
  { scope: 'write:receipts', label: 'Запись чеков', group: 'Чеки' },
  { scope: 'write:bank_statements', label: 'Импорт банковской выписки', group: 'Банк' },
  { scope: 'read:transactions', label: 'Чтение транзакций', group: 'Транзакции' },
  { scope: 'write:transactions', label: 'Запись транзакций', group: 'Транзакции' },
  { scope: 'read:reconciliation', label: 'Чтение сверки', group: 'Сверка' },
  { scope: 'write:reconciliation', label: 'Работа со сверкой', group: 'Сверка' },
  { scope: 'read:accounts', label: 'Чтение счетов', group: 'Счета' },
  { scope: 'write:accounts', label: 'Запись счетов', group: 'Счета' },
  { scope: 'read:expense_types', label: 'Чтение типов затрат', group: 'Типы затрат' },
  { scope: 'write:expense_types', label: 'Запись типов затрат', group: 'Типы затрат' },
  { scope: 'read:counterparties', label: 'Чтение контрагентов', group: 'Контрагенты' },
  { scope: 'write:counterparties', label: 'Запись контрагентов', group: 'Контрагенты' },
  { scope: 'read:exchange_rates', label: 'Чтение курсов валют', group: 'Курсы валют' },
  { scope: 'write:exchange_rates', label: 'Запись курсов валют', group: 'Курсы валют' },
]

export default function Settings() {
  const [tab, setTab] = useState<Tab>('accounts')

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Настройки</h1>
      <div className="border-b border-gray-200 flex gap-6">
        {(['accounts', 'expense-types', 'api-keys'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium transition-colors ${
              tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'accounts' ? 'Счета' : t === 'expense-types' ? 'Типы расходов' : 'API ключи'}
          </button>
        ))}
      </div>
      {tab === 'accounts' && <AccountsTab />}
      {tab === 'expense-types' && <ExpenseTypesTab />}
      {tab === 'api-keys' && <ApiKeysTab />}
    </div>
  )
}

function AccountsTab() {
  const { data: accounts = [] } = useAccounts()
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const deleteAccount = useDeleteAccount()
  const qc = useQueryClient()
  const [form, setForm] = useState({ bank: '', account_number: '', currency: 'RUB' })
  const [initForm, setInitForm] = useState<{ id: string; amount: string; recorded_at: string; source: 'OPENING' | 'CLOSING' } | null>(null)
  const [initError, setInitError] = useState<string | null>(null)
  const [initPending, setInitPending] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [editAccount, setEditAccount] = useState<Account | null>(null)
  const [editForm, setEditForm] = useState({ bank: '', account_number: '', currency: '', is_active: true })
  const [editError, setEditError] = useState<string | null>(null)

  const handleCreate = async () => {
    await createAccount.mutateAsync(form)
    setForm({ bank: '', account_number: '', currency: 'RUB' })
  }

  const handleInitBalance = async () => {
    if (!initForm) return
    setInitError(null)
    setInitPending(true)
    try {
      await accountsApi.initBalance(
        initForm.id,
        Number(initForm.amount),
        localInputToUtcIso(initForm.recorded_at),
        initForm.source,
      )
      await qc.invalidateQueries({ queryKey: ['accounts'] })
      setInitForm(null)
    } catch {
      setInitError('Не удалось сохранить баланс. Проверьте введённые данные.')
    } finally {
      setInitPending(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!confirmDeleteId) return
    setDeleteError(null)
    try {
      await deleteAccount.mutateAsync(confirmDeleteId)
      setConfirmDeleteId(null)
    } catch {
      setDeleteError('Не удалось удалить счёт. Возможно, он используется в транзакциях.')
    }
  }

  const openEdit = (acc: Account) => {
    setEditAccount(acc)
    setEditForm({ bank: acc.bank, account_number: acc.account_number, currency: acc.currency, is_active: acc.is_active })
    setEditError(null)
  }

  const handleEditSave = async () => {
    if (!editAccount) return
    setEditError(null)
    try {
      await updateAccount.mutateAsync({ id: editAccount.id, data: editForm })
      setEditAccount(null)
    } catch {
      setEditError('Не удалось сохранить изменения.')
    }
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
                  onClick={() => { setInitForm({ id: acc.id, amount: '', recorded_at: '', source: 'OPENING' }); setInitError(null) }}
                  className="text-xs text-yellow-600 border border-yellow-300 rounded px-2 py-1 hover:bg-yellow-50"
                >
                  ⚠ Задать баланс
                </button>
              )}
              <button
                onClick={() => openEdit(acc)}
                className="text-xs text-indigo-600 hover:underline"
              >
                Изменить
              </button>
              {confirmDeleteId === acc.id ? (
                <span className="inline-flex items-center gap-2 text-xs">
                  <span className="text-gray-600">Удалить?</span>
                  <button onClick={handleDeleteConfirm} className="text-red-500 hover:underline">Да</button>
                  <button onClick={() => setConfirmDeleteId(null)} className="text-gray-500 hover:underline">Нет</button>
                </span>
              ) : (
                <button
                  onClick={() => { setDeleteError(null); setConfirmDeleteId(acc.id) }}
                  className="text-xs text-red-500 hover:underline"
                >
                  Удалить
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {deleteError && <p className="text-sm text-red-500">{deleteError}</p>}

      {editAccount && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setEditAccount(null)}
        >
          <div className="bg-white rounded-xl p-6 space-y-3 w-96" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <h2 className="font-medium text-gray-900">Изменить счёт</h2>
              <button onClick={() => setEditAccount(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
            </div>
            <input
              placeholder="Банк"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={editForm.bank}
              onChange={(e) => setEditForm((f) => ({ ...f, bank: e.target.value }))}
            />
            <input
              placeholder="Номер счёта"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={editForm.account_number}
              onChange={(e) => setEditForm((f) => ({ ...f, account_number: e.target.value }))}
            />
            <input
              placeholder="Валюта"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={editForm.currency}
              onChange={(e) => setEditForm((f) => ({ ...f, currency: e.target.value }))}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              Активен
            </label>
            {editError && <p className="text-sm text-red-500">{editError}</p>}
            <div className="flex gap-2">
              <button
                onClick={handleEditSave}
                disabled={updateAccount.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg disabled:opacity-50"
              >
                {updateAccount.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button onClick={() => setEditAccount(null)} className="px-4 py-2 border border-gray-300 text-sm rounded-lg">Отмена</button>
            </div>
          </div>
        </div>
      )}

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
            {initError && <p className="text-sm text-red-500">{initError}</p>}
            <div className="flex gap-2">
              <button
                onClick={handleInitBalance}
                disabled={initPending || !initForm.amount || !initForm.recorded_at}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg disabled:opacity-50"
              >
                {initPending ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button onClick={() => setInitForm(null)} className="px-4 py-2 border border-gray-300 text-sm rounded-lg">Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ApiKeysTab() {
  const { data: keys = [] } = useApiKeys()
  const createKey = useCreateApiKey()
  const updateKey = useUpdateApiKey()
  const deleteKey = useDeleteApiKey()
  const [form, setForm] = useState({ name: '', scopes: [] as string[], expires_at: '' })
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null)
  const [copied, setCopied] = useState(false)

  const groups = Array.from(new Set(ALL_SCOPES.map((s) => s.group)))

  const toggleScope = (scope: string) => {
    setForm((f) => ({
      ...f,
      scopes: f.scopes.includes(scope) ? f.scopes.filter((s) => s !== scope) : [...f.scopes, scope],
    }))
  }

  const handleCreate = async () => {
    if (!form.name.trim() || form.scopes.length === 0) return
    const result = await createKey.mutateAsync({
      name: form.name,
      scopes: form.scopes,
      expires_at: form.expires_at ? localInputToUtcIso(form.expires_at) : null,
    })
    setCreatedKey(result)
    setForm({ name: '', scopes: [], expires_at: '' })
  }

  const handleCopy = async () => {
    if (!createdKey) return
    await navigator.clipboard.writeText(createdKey.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3 max-w-lg">
        <h2 className="font-medium text-gray-900">Создать ключ</h2>
        <input
          placeholder="Название ключа"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        />

        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-700">Права доступа</p>
          {groups.map((group) => (
            <div key={group}>
              <p className="text-xs text-gray-400 mb-1">{group}</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {ALL_SCOPES.filter((s) => s.group === group).map(({ scope, label }) => (
                  <label key={scope} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.scopes.includes(scope)}
                      onChange={() => toggleScope(scope)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Действует до (опционально)</label>
          <input
            type="datetime-local"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={form.expires_at}
            onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))}
          />
        </div>

        <button
          onClick={handleCreate}
          disabled={createKey.isPending || !form.name.trim() || form.scopes.length === 0}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          Создать
        </button>
      </div>

      <div className="space-y-2">
        {keys.map((k) => (
          <div key={k.id} className="bg-white border border-gray-200 rounded-xl px-4 py-3">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 min-w-0">
                <div className="font-medium text-sm text-gray-900">{k.name}</div>
                <div className="text-xs font-mono text-gray-400">bm_{k.key_prefix}...</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {k.scopes.map((s) => (
                    <span key={s} className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
                      {s}
                    </span>
                  ))}
                </div>
                <div className="text-xs text-gray-400">
                  Создан: {formatDate(k.created_at)}
                  {k.last_used_at && ` · Последнее использование: ${formatDate(k.last_used_at)}`}
                  {k.expires_at && ` · Истекает: ${formatDate(k.expires_at)}`}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => updateKey.mutate({ id: k.id, data: { is_active: !k.is_active } })}
                  className={`text-xs px-2 py-1 rounded border ${
                    k.is_active
                      ? 'text-yellow-600 border-yellow-300 hover:bg-yellow-50'
                      : 'text-green-600 border-green-300 hover:bg-green-50'
                  }`}
                >
                  {k.is_active ? 'Деактивировать' : 'Активировать'}
                </button>
                <button
                  onClick={() => deleteKey.mutate(k.id)}
                  className="text-xs text-red-500 hover:underline"
                >
                  Удалить
                </button>
              </div>
            </div>
            {!k.is_active && (
              <div className="mt-1 text-xs text-red-400">Деактивирован</div>
            )}
          </div>
        ))}
        {keys.length === 0 && (
          <p className="text-sm text-gray-400">Нет API ключей. Создайте первый.</p>
        )}
      </div>

      {createdKey && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 space-y-3 w-full max-w-md mx-4">
            <h2 className="font-medium text-gray-900">Ключ создан</h2>
            <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">
              Сохраните ключ сейчас — он больше не будет показан.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs bg-gray-100 rounded px-3 py-2 break-all select-all">
                {createdKey.key}
              </code>
              <button
                onClick={handleCopy}
                className="shrink-0 px-3 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
              >
                {copied ? 'Скопировано!' : 'Копировать'}
              </button>
            </div>
            <button
              onClick={() => { setCreatedKey(null); setCopied(false) }}
              className="w-full px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
            >
              Готово
            </button>
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
  const updateTypeInline = useUpdateExpenseType()
  const deleteType = useDeleteExpenseType()
  const [form, setForm] = useState({ id: '', name: '', description: '', receipt_required: true })
  const [editType, setEditType] = useState<ExpenseType | null>(null)
  const [editTypeForm, setEditTypeForm] = useState({ name: '', description: '', receipt_required: true })
  const [editTypeError, setEditTypeError] = useState<string | null>(null)

  const openEditType = (t: ExpenseType) => {
    setEditType(t)
    setEditTypeForm({ name: t.name, description: t.description ?? '', receipt_required: t.receipt_required })
    setEditTypeError(null)
  }

  const handleEditTypeSave = async () => {
    if (!editType) return
    setEditTypeError(null)
    try {
      await updateType.mutateAsync({
        id: editType.id,
        data: { name: editTypeForm.name, description: editTypeForm.description.trim() || null, receipt_required: editTypeForm.receipt_required },
      })
      setEditType(null)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } }
      const detail = err?.response?.data?.detail
      if (typeof detail === 'string') setEditTypeError(detail)
      else setEditTypeError('Не удалось сохранить изменения.')
    }
  }

  const handleCreate = async () => {
    await createType.mutateAsync({
      ...form,
      description: form.description.trim() || null,
    })
    setForm({ id: '', name: '', description: '', receipt_required: true })
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
        <textarea
          placeholder="Описание (необязательно)"
          rows={2}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
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
              {t.description && (
                <div className="text-xs text-gray-500 mt-0.5">{t.description}</div>
              )}
              <div className="text-xs text-gray-400">{t.id}</div>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={t.receipt_required}
                  onChange={(e) => updateTypeInline.mutate({ id: t.id, data: { receipt_required: e.target.checked } })}
                />
                Чек
              </label>
              <button
                onClick={() => openEditType(t)}
                className="text-xs text-indigo-600 hover:underline"
              >
                Изменить
              </button>
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

      {editType && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setEditType(null)}
        >
          <div className="bg-white rounded-xl p-6 space-y-3 w-96" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <h2 className="font-medium text-gray-900">Изменить тип расходов</h2>
              <button onClick={() => setEditType(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
            </div>
            <p className="text-xs text-gray-400">ID: <span className="font-mono">{editType.id}</span></p>
            <input
              placeholder="Название"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={editTypeForm.name}
              onChange={(e) => setEditTypeForm((f) => ({ ...f, name: e.target.value }))}
            />
            <textarea
              placeholder="Описание (необязательно)"
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
              value={editTypeForm.description}
              onChange={(e) => setEditTypeForm((f) => ({ ...f, description: e.target.value }))}
            />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={editTypeForm.receipt_required}
                onChange={(e) => setEditTypeForm((f) => ({ ...f, receipt_required: e.target.checked }))}
              />
              Требуется чек
            </label>
            {editTypeError && <p className="text-sm text-red-500">{editTypeError}</p>}
            <div className="flex gap-2">
              <button
                onClick={handleEditTypeSave}
                disabled={updateType.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg disabled:opacity-50"
              >
                {updateType.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button onClick={() => setEditType(null)} className="px-4 py-2 border border-gray-300 text-sm rounded-lg">Отмена</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

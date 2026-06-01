import { useState } from 'react'

import { DataTable } from '../components/DataTable'
import {
  useCounterparties,
  useCreateCounterparty,
  useDeleteCounterparty,
  useUpdateCounterparty,
} from '../hooks/useCounterparties'
import { Counterparty } from '../types'

interface FormState {
  name: string
  type: string
  inn: string
  kpp: string
}

const EMPTY_FORM: FormState = { name: '', type: 'STORE', inn: '', kpp: '' }

const TYPES = [
  { value: 'STORE', label: 'Магазин' },
  { value: 'COMPANY', label: 'Компания' },
  { value: 'PERSON', label: 'Физлицо' },
]

export default function Counterparties() {
  const { data: counterparties = [], isLoading } = useCounterparties()
  const create = useCreateCounterparty()
  const update = useUpdateCounterparty()
  const remove = useDeleteCounterparty()

  const [modal, setModal] = useState<{ mode: 'create' | 'edit'; cp?: Counterparty } | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)

  function openCreate() {
    setForm(EMPTY_FORM)
    setError(null)
    setModal({ mode: 'create' })
  }

  function openEdit(cp: Counterparty) {
    setForm({
      name: cp.name,
      type: cp.type,
      inn: cp.inn ?? '',
      kpp: cp.kpp ?? '',
    })
    setError(null)
    setModal({ mode: 'edit', cp })
  }

  function closeModal() {
    setModal(null)
    setError(null)
  }

  async function handleSubmit() {
    setError(null)
    const payload = {
      name: form.name.trim(),
      type: form.type,
      inn: form.inn.trim() || null,
      kpp: form.kpp.trim() || null,
    }
    try {
      if (modal?.mode === 'create') {
        await create.mutateAsync(payload)
      } else if (modal?.mode === 'edit' && modal.cp) {
        await update.mutateAsync({ id: modal.cp.id, data: payload })
      }
      closeModal()
    } catch (e: unknown) {
      const msg = extractErrorMessage(e)
      setError(msg)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Контрагенты</h1>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          Добавить
        </button>
      </div>

      <DataTable
        columns={[
          { label: 'Название' },
          { label: 'Тип' },
          { label: 'ИНН' },
          { label: 'КПП' },
          { label: '' },
        ]}
        isEmpty={counterparties.length === 0}
        emptyMessage="Нет контрагентов"
        isLoading={isLoading}
      >
        {counterparties.map((cp) => (
          <tr key={cp.id} className="hover:bg-gray-50">
            <td className="px-4 py-2 text-gray-900">{cp.name}</td>
            <td className="px-4 py-2 text-gray-600">{typeLabel(cp.type)}</td>
            <td className="px-4 py-2 font-mono text-sm text-gray-600">{cp.inn ?? '—'}</td>
            <td className="px-4 py-2 font-mono text-sm text-gray-600">{cp.kpp ?? '—'}</td>
            <td className="px-4 py-2 space-x-3">
              <button
                onClick={() => openEdit(cp)}
                className="text-xs text-indigo-600 hover:underline"
              >
                Изменить
              </button>
              <button
                onClick={() => remove.mutate(cp.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Удалить
              </button>
            </td>
          </tr>
        ))}
      </DataTable>

      {modal && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={closeModal}
        >
          <div
            className="bg-white rounded-xl p-6 space-y-4 w-full max-w-md mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-semibold text-gray-900">
              {modal.mode === 'create' ? 'Добавить контрагента' : 'Изменить контрагента'}
            </h2>

            <div className="space-y-3">
              <Field label="Название">
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </Field>

              <Field label="Тип">
                <select
                  value={form.type}
                  onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="ИНН (10 или 12 цифр)">
                <input
                  value={form.inn}
                  onChange={(e) => setForm((f) => ({ ...f, inn: e.target.value }))}
                  placeholder="Необязательно"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </Field>

              <Field label="КПП (9 цифр, для юрлиц)">
                <input
                  value={form.kpp}
                  onChange={(e) => setForm((f) => ({ ...f, kpp: e.target.value }))}
                  placeholder="Необязательно"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </Field>
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <div className="flex justify-end gap-3">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Отмена
              </button>
              <button
                onClick={handleSubmit}
                disabled={!form.name.trim() || create.isPending || update.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {modal.mode === 'create' ? 'Добавить' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
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

function typeLabel(type: string): string {
  const map: Record<string, string> = { STORE: 'Магазин', COMPANY: 'Компания', PERSON: 'Физлицо' }
  return map[type] ?? type
}

function extractErrorMessage(e: unknown): string {
  if (e && typeof e === 'object' && 'response' in e) {
    const resp = (e as { response?: { data?: { detail?: unknown } } }).response
    const detail = resp?.data?.detail
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
    }
    if (typeof detail === 'string') return detail
  }
  return 'Произошла ошибка'
}

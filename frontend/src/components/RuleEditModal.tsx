import { useState } from 'react'

import { useAccounts } from '../hooks/useAccounts'
import { useCreateClassifierRule, useUpdateClassifierRule } from '../hooks/useClassifierRules'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import type { ClassifierRule } from '../types'

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const OP_OPTIONS = [
  { value: 'eq', label: '=' },
  { value: 'lt', label: '<' },
  { value: 'gt', label: '>' },
  { value: 'lte', label: '≤' },
  { value: 'gte', label: '≥' },
]
const TYPE_OPTIONS = [
  { value: 'EXPENSE', label: 'Расход' },
  { value: 'INCOME', label: 'Доход' },
  { value: 'TRANSFER', label: 'Перевод' },
]

interface Props {
  rule: ClassifierRule | null
  mode: 'create' | 'edit'
  onClose: () => void
}

interface CondState {
  account: boolean
  account_id: string
  day_month: boolean
  day_month_val: string
  day_month_op: string
  day_week: boolean
  day_week_days: boolean[]
  amount: boolean
  amount_val: string
  amount_op: string
  type: boolean
  type_val: string
  bank_category: boolean
  bank_category_val: string
  description: boolean
  description_val: string
}

function parseWeekDays(json: string | null): boolean[] {
  const arr = Array(7).fill(false)
  if (!json) return arr
  try {
    const days: number[] = JSON.parse(json)
    days.forEach((d) => { if (d >= 0 && d < 7) arr[d] = true })
  } catch { /* ignore */ }
  return arr
}

function initCond(rule: ClassifierRule | null): CondState {
  if (!rule) {
    return {
      account: false, account_id: '',
      day_month: false, day_month_val: '', day_month_op: 'eq',
      day_week: false, day_week_days: Array(7).fill(false),
      amount: false, amount_val: '', amount_op: 'eq',
      type: false, type_val: 'EXPENSE',
      bank_category: false, bank_category_val: '',
      description: false, description_val: '',
    }
  }
  return {
    account: rule.cond_account_id !== null,
    account_id: rule.cond_account_id ?? '',
    day_month: rule.cond_day_month !== null,
    day_month_val: rule.cond_day_month !== null ? String(rule.cond_day_month) : '',
    day_month_op: rule.cond_day_month_op ?? 'eq',
    day_week: rule.cond_day_week !== null,
    day_week_days: parseWeekDays(rule.cond_day_week),
    amount: rule.cond_amount !== null,
    amount_val: rule.cond_amount ?? '',
    amount_op: rule.cond_amount_op ?? 'eq',
    type: rule.cond_type !== null,
    type_val: rule.cond_type ?? 'EXPENSE',
    bank_category: rule.cond_bank_category !== null,
    bank_category_val: rule.cond_bank_category ?? '',
    description: rule.cond_description !== null,
    description_val: rule.cond_description ?? '',
  }
}

export default function RuleEditModal({ rule, mode, onClose }: Props) {
  const create = useCreateClassifierRule()
  const update = useUpdateClassifierRule()
  const { data: expenseTypes = [] } = useExpenseTypes()
  const { data: accounts = [] } = useAccounts()

  const [name, setName] = useState(rule?.name ?? '')
  const [etId, setEtId] = useState(rule?.expense_type_id ?? '')
  const [priority, setPriority] = useState(String(rule?.priority ?? 1))
  const [isActive, setIsActive] = useState(rule?.is_active ?? true)
  const [cond, setCond] = useState<CondState>(() => initCond(rule))
  const [error, setError] = useState<string | null>(null)

  function setC<K extends keyof CondState>(key: K, val: CondState[K]) {
    setCond((c) => ({ ...c, [key]: val }))
  }

  function toggleWeekDay(idx: number) {
    const next = [...cond.day_week_days]
    next[idx] = !next[idx]
    setC('day_week_days', next)
  }

  function buildPayload() {
    const selectedDays = cond.day_week_days
      .map((v, i) => (v ? i : -1))
      .filter((i) => i >= 0)

    return {
      name,
      expense_type_id: etId,
      priority: Number(priority),
      is_active: isActive,
      cond_account_id: cond.account && cond.account_id ? cond.account_id : null,
      cond_day_month: cond.day_month && cond.day_month_val ? Number(cond.day_month_val) : null,
      cond_day_month_op: cond.day_month ? cond.day_month_op : null,
      cond_day_week: cond.day_week && selectedDays.length > 0 ? JSON.stringify(selectedDays) : null,
      cond_amount: cond.amount && cond.amount_val ? cond.amount_val : null,
      cond_amount_op: cond.amount ? cond.amount_op : null,
      cond_type: cond.type ? cond.type_val : null,
      cond_bank_category: cond.bank_category && cond.bank_category_val ? cond.bank_category_val : null,
      cond_description: cond.description && cond.description_val ? cond.description_val : null,
    }
  }

  async function handleSave() {
    setError(null)
    if (!name.trim()) { setError('Укажите имя правила'); return }
    if (!etId) { setError('Выберите вид расхода'); return }
    if (!priority || isNaN(Number(priority))) { setError('Укажите приоритет'); return }

    const payload = buildPayload()
    const hasCondition = [
      payload.cond_account_id,
      payload.cond_day_month,
      payload.cond_day_week,
      payload.cond_amount,
      payload.cond_type,
      payload.cond_bank_category,
      payload.cond_description,
    ].some((v) => v !== null)
    if (!hasCondition) { setError('Необходимо выбрать хотя бы одно условие'); return }

    try {
      if (mode === 'create') {
        await create.mutateAsync(payload)
      } else if (rule) {
        await update.mutateAsync({ id: rule.id, data: payload })
      }
      onClose()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Ошибка сохранения')
    }
  }

  const isPending = create.isPending || update.isPending

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
          <h2 className="text-lg font-semibold text-gray-900">
            {mode === 'create' ? 'Добавить правило' : 'Изменить правило'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div className="space-y-3">
          <Field label="Имя правила">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
              placeholder="Например: Продукты в будни"
            />
          </Field>
          <Field label="Вид расхода">
            <select value={etId} onChange={(e) => setEtId(e.target.value)} className={inputCls}>
              <option value="">Выберите вид расхода</option>
              {expenseTypes.map((et) => (
                <option key={et.id} value={et.id}>{et.name}</option>
              ))}
            </select>
          </Field>
          <div className="flex gap-3">
            <Field label="Приоритет">
              <input
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className={inputCls + ' w-24'}
                min={1}
              />
            </Field>
            <Field label="Действует">
              <div className="flex items-center h-9">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 accent-indigo-600"
                />
              </div>
            </Field>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Условия</p>
          <div className="space-y-2 border border-gray-200 rounded-lg p-3">
            {/* account_id */}
            <CondRow
              enabled={cond.account}
              onToggle={(v) => setC('account', v)}
              label="Счёт"
            >
              <select
                value={cond.account_id}
                onChange={(e) => setC('account_id', e.target.value)}
                disabled={!cond.account}
                className={inputCls}
              >
                <option value="">Выберите счёт</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.bank} ***{a.account_number.slice(-4)}</option>
                ))}
              </select>
            </CondRow>

            {/* day_month */}
            <CondRow
              enabled={cond.day_month}
              onToggle={(v) => setC('day_month', v)}
              label="День месяца"
            >
              <div className="flex gap-2">
                <select
                  value={cond.day_month_op}
                  onChange={(e) => setC('day_month_op', e.target.value)}
                  disabled={!cond.day_month}
                  className={inputCls + ' w-16'}
                >
                  {OP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <input
                  type="number"
                  value={cond.day_month_val}
                  onChange={(e) => setC('day_month_val', e.target.value)}
                  disabled={!cond.day_month}
                  min={1}
                  max={31}
                  placeholder="1–31"
                  className={inputCls + ' w-20'}
                />
              </div>
            </CondRow>

            {/* day_week */}
            <CondRow
              enabled={cond.day_week}
              onToggle={(v) => setC('day_week', v)}
              label="День недели"
            >
              <div className="flex gap-1 flex-wrap">
                {DAY_LABELS.map((d, i) => (
                  <label key={i} className={`flex items-center gap-0.5 px-2 py-1 rounded border text-xs cursor-pointer ${cond.day_week_days[i] ? 'bg-indigo-50 border-indigo-400 text-indigo-700' : 'border-gray-300 text-gray-600'} ${!cond.day_week ? 'opacity-40 cursor-not-allowed' : ''}`}>
                    <input
                      type="checkbox"
                      checked={cond.day_week_days[i]}
                      onChange={() => toggleWeekDay(i)}
                      disabled={!cond.day_week}
                      className="hidden"
                    />
                    {d}
                  </label>
                ))}
              </div>
            </CondRow>

            {/* amount */}
            <CondRow
              enabled={cond.amount}
              onToggle={(v) => setC('amount', v)}
              label="Сумма"
            >
              <div className="flex gap-2">
                <select
                  value={cond.amount_op}
                  onChange={(e) => setC('amount_op', e.target.value)}
                  disabled={!cond.amount}
                  className={inputCls + ' w-16'}
                >
                  {OP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <input
                  type="number"
                  step="0.01"
                  value={cond.amount_val}
                  onChange={(e) => setC('amount_val', e.target.value)}
                  disabled={!cond.amount}
                  placeholder="Сумма"
                  className={inputCls + ' w-32'}
                />
              </div>
            </CondRow>

            {/* type */}
            <CondRow
              enabled={cond.type}
              onToggle={(v) => setC('type', v)}
              label="Тип"
            >
              <select
                value={cond.type_val}
                onChange={(e) => setC('type_val', e.target.value)}
                disabled={!cond.type}
                className={inputCls}
              >
                {TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </CondRow>

            {/* bank_category */}
            <CondRow
              enabled={cond.bank_category}
              onToggle={(v) => setC('bank_category', v)}
              label="Категория банка содержит"
            >
              <input
                type="text"
                value={cond.bank_category_val}
                onChange={(e) => setC('bank_category_val', e.target.value)}
                disabled={!cond.bank_category}
                placeholder="Например: продукты"
                className={inputCls}
              />
            </CondRow>

            {/* description */}
            <CondRow
              enabled={cond.description}
              onToggle={(v) => setC('description', v)}
              label="Описание содержит"
            >
              <input
                type="text"
                value={cond.description_val}
                onChange={(e) => setC('description_val', e.target.value)}
                disabled={!cond.description}
                placeholder="Например: кофе"
                className={inputCls}
              />
            </CondRow>
          </div>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={isPending}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {isPending ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  )
}

const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
    </div>
  )
}

function CondRow({
  enabled,
  onToggle,
  label,
  children,
}: {
  enabled: boolean
  onToggle: (v: boolean) => void
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start gap-3">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => onToggle(e.target.checked)}
        className="mt-2 w-4 h-4 accent-indigo-600 shrink-0"
      />
      <div className="flex-1 space-y-1">
        <label className="text-xs font-medium text-gray-500">{label}</label>
        <div className={enabled ? '' : 'opacity-40 pointer-events-none'}>{children}</div>
      </div>
    </div>
  )
}

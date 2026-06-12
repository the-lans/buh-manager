import { useState } from 'react'

import { DataTable } from '../components/DataTable'
import RuleEditModal from '../components/RuleEditModal'
import RuleFillModal from '../components/RuleFillModal'
import {
  useClassifierRules,
  useDeleteClassifierRule,
} from '../hooks/useClassifierRules'
import { useExpenseTypes } from '../hooks/useExpenseTypes'
import type { ClassifierRule } from '../types'

export default function Rules() {
  const { data: rules = [], isLoading } = useClassifierRules()
  const { data: expenseTypes = [] } = useExpenseTypes()
  const deleteRule = useDeleteClassifierRule()

  const expenseTypeMap = new Map(expenseTypes.map((et) => [et.id, et.name]))

  const [filterExpenseTypeId, setFilterExpenseTypeId] = useState('')
  const [filterPriority, setFilterPriority] = useState('')

  const priorities = [...new Set(rules.map((r) => r.priority))].sort((a, b) => a - b)

  const filteredRules = rules
    .filter((r) => !filterExpenseTypeId || r.expense_type_id === filterExpenseTypeId)
    .filter((r) => !filterPriority || String(r.priority) === filterPriority)

  const [editModal, setEditModal] = useState<{ mode: 'create' | 'edit'; rule: ClassifierRule | null } | null>(null)
  const [showFill, setShowFill] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Правила</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFill(true)}
            className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50 text-gray-700"
          >
            Заполнить
          </button>
          <button
            onClick={() => setEditModal({ mode: 'create', rule: null })}
            className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
          >
            + Добавить
          </button>
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filterExpenseTypeId}
          onChange={(e) => setFilterExpenseTypeId(e.target.value)}
        >
          <option value="">Все типы затрат</option>
          {expenseTypes.map((et) => (
            <option key={et.id} value={et.id}>{et.name}</option>
          ))}
        </select>
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
        >
          <option value="">Все приоритеты</option>
          {priorities.map((p) => (
            <option key={p} value={String(p)}>{p}</option>
          ))}
        </select>
      </div>

      <DataTable
        columns={[
          { label: 'Имя правила' },
          { label: 'Тип затрат' },
          { label: 'Приоритет', align: 'right' },
          { label: 'Представление' },
          { label: 'Действует', align: 'center' },
          { label: '' },
        ]}
        isEmpty={filteredRules.length === 0}
        emptyMessage="Нет правил. Добавьте первое правило."
        isLoading={isLoading}
      >
        {filteredRules.map((rule) => (
          <tr key={rule.id} className="hover:bg-gray-50">
            <td className="px-4 py-2 text-gray-900 font-medium">{rule.name}</td>
            <td className="px-4 py-2 text-gray-700">
              {expenseTypeMap.get(rule.expense_type_id) ?? rule.expense_type_id}
            </td>
            <td className="px-4 py-2 text-right tabular-nums text-gray-600">{rule.priority}</td>
            <td className="px-4 py-2 text-gray-500 text-sm max-w-[240px] truncate" title={rule.representation}>
              {rule.representation || '—'}
            </td>
            <td className="px-4 py-2 text-center">
              {rule.is_active
                ? <span className="text-green-600 font-medium">✓</span>
                : <span className="text-gray-300">—</span>}
            </td>
            <td className="px-4 py-2">
              {confirmDeleteId === rule.id ? (
                <span className="inline-flex items-center gap-2 text-xs">
                  <span className="text-gray-600">Удалить?</span>
                  <button
                    onClick={() => { deleteRule.mutate(rule.id); setConfirmDeleteId(null) }}
                    disabled={deleteRule.isPending}
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
                    onClick={() => setEditModal({ mode: 'edit', rule })}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Изменить
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(rule.id)}
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

      {editModal && (
        <RuleEditModal
          key={editModal.rule?.id ?? 'new'}
          rule={editModal.rule}
          mode={editModal.mode}
          onClose={() => setEditModal(null)}
        />
      )}

      {showFill && <RuleFillModal onClose={() => setShowFill(false)} />}
    </div>
  )
}

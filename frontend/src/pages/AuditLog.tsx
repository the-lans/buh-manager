import { Fragment, useState } from 'react'

import { DataTable } from '../components/DataTable'
import { useAuditLog } from '../hooks/useAuditLog'
import { formatDateTime } from '../utils/date'

const ENTITY_TYPES = ['', 'receipt', 'transaction', 'match', 'import']

export default function AuditLog() {
  const [entityType, setEntityType] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: entries = [], isLoading } = useAuditLog(
    entityType ? { entity_type: entityType, limit: 100 } : { limit: 100 },
  )

  function toggleExpand(id: string) {
    setExpanded((prev) => (prev === id ? null : id))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-gray-900">Журнал изменений</h1>
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {ENTITY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t === '' ? 'Все типы' : t}
            </option>
          ))}
        </select>
      </div>

      <DataTable
        columns={[
          { label: 'Дата и время' },
          { label: 'Тип' },
          { label: 'Действие' },
          { label: 'Кто изменил' },
          { label: '' },
        ]}
        isEmpty={entries.length === 0}
        emptyMessage="Нет записей"
        isLoading={isLoading}
      >
        {entries.map((entry) => (
          <Fragment key={entry.id}>
            <tr
              className="cursor-pointer hover:bg-gray-50"
              onClick={() => entry.diff && toggleExpand(entry.id)}
            >
              <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                {formatDateTime(entry.changed_at)}
              </td>
              <td className="px-4 py-2">
                <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                  {entry.entity_type}
                </span>
              </td>
              <td className="px-4 py-2">
                <ActionBadge action={entry.action} />
              </td>
              <td className="px-4 py-2 text-gray-600">{entry.changed_by}</td>
              <td className="px-4 py-2 text-gray-400 text-xs">
                {entry.diff ? (expanded === entry.id ? '▲' : '▼') : ''}
              </td>
            </tr>
            {expanded === entry.id && entry.diff && (
              <tr className="bg-gray-50">
                <td colSpan={5} className="px-4 py-3">
                  <DiffViewer diff={entry.diff} />
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </DataTable>
    </div>
  )
}

function ActionBadge({ action }: { action: string }) {
  const colors: Record<string, string> = {
    CREATE: 'bg-green-100 text-green-700',
    UPDATE: 'bg-blue-100 text-blue-700',
    DELETE: 'bg-red-100 text-red-700',
    MATCH: 'bg-indigo-100 text-indigo-700',
    UNMATCH: 'bg-yellow-100 text-yellow-700',
    IMPORT_CONFLICT: 'bg-orange-100 text-orange-700',
  }
  const cls = colors[action] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {action}
    </span>
  )
}

function DiffViewer({ diff }: { diff: string }) {
  let parsed: unknown
  try {
    parsed = JSON.parse(diff)
  } catch {
    return <pre className="text-xs text-gray-700 whitespace-pre-wrap">{diff}</pre>
  }

  const obj = parsed as { before?: Record<string, unknown>; after?: Record<string, unknown> }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
      {obj.before && (
        <div>
          <p className="font-medium text-gray-500 mb-1">До</p>
          <pre className="bg-red-50 border border-red-100 rounded p-2 whitespace-pre-wrap text-red-800 overflow-x-auto">
            {JSON.stringify(obj.before, null, 2)}
          </pre>
        </div>
      )}
      {obj.after && (
        <div>
          <p className="font-medium text-gray-500 mb-1">После</p>
          <pre className="bg-green-50 border border-green-100 rounded p-2 whitespace-pre-wrap text-green-800 overflow-x-auto">
            {JSON.stringify(obj.after, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

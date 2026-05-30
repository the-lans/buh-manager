import type { ReactNode } from 'react'

interface ColumnDef {
  label: string
  align?: 'right'
}

interface DataTableProps {
  columns: ColumnDef[]
  children: ReactNode
  isEmpty?: boolean
  emptyMessage?: string
  isLoading?: boolean
}

export function DataTable({
  columns,
  children,
  isEmpty = false,
  emptyMessage = 'Нет данных',
  isLoading = false,
}: DataTableProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {isLoading ? (
        <div className="p-8 text-center text-gray-400">Загрузка...</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {columns.map((col, i) => (
                <th
                  key={i}
                  className={`px-4 py-2 font-medium text-gray-600${
                    col.align === 'right'
                      ? ' text-right tabular-nums'
                      : col.label
                        ? ' text-left'
                        : ''
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isEmpty ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              children
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

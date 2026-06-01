import { useCallback } from 'react'

import { documentsApi } from '../api/documents'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { useDocuments } from '../hooks/useDocuments'
import { formatDate } from '../utils/date'

const DOC_TYPE_LABELS: Record<string, string> = {
  RECEIPT: 'Чек',
  BANK_STATEMENT: 'Выписка',
}

export default function Documents() {
  const { data: documents = [], isLoading } = useDocuments({ limit: 100 })

  const handleOpen = useCallback(async (id: string) => {
    const url = await documentsApi.getOpenUrl(id)
    window.open(url, '_blank')
  }, [])

  const handleDownload = useCallback(async (id: string, name: string) => {
    const url = await documentsApi.getDownloadUrl(id)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Документы</h1>
      <DataTable
        columns={[
          { label: 'Название' },
          { label: 'Тип' },
          { label: 'Статус' },
          { label: 'Загружен' },
          { label: 'Действия' },
        ]}
        isEmpty={documents.length === 0}
        emptyMessage="Нет документов"
        isLoading={isLoading}
      >
        {documents.map((doc) => (
          <tr key={doc.id} className="hover:bg-gray-50">
            <td className="px-4 py-2 text-gray-800 max-w-xs truncate">{doc.name}</td>
            <td className="px-4 py-2 text-gray-600 text-sm">
              {DOC_TYPE_LABELS[doc.type] ?? doc.type}
            </td>
            <td className="px-4 py-2">
              <StatusBadge status={doc.status} />
            </td>
            <td className="px-4 py-2 text-gray-600 text-sm">{formatDate(doc.uploaded_at)}</td>
            <td className="px-4 py-2">
              <div className="flex gap-2">
                <button
                  onClick={() => handleOpen(doc.id)}
                  className="text-xs text-indigo-600 hover:underline"
                >
                  Открыть
                </button>
                <button
                  onClick={() => handleDownload(doc.id, doc.name)}
                  className="text-xs text-gray-500 hover:underline"
                >
                  Скачать
                </button>
              </div>
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}

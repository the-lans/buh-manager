import { useCallback, useMemo, useState } from 'react'

import { documentsApi } from '../api/documents'
import { useCounterpartyMap } from '../hooks/useCounterparties'
import { useDocument, useDocuments } from '../hooks/useDocuments'
import { useReceipt, useUpdateReceipt } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'

interface Props {
  receiptId: string | null
  onClose: () => void
}

const SIXTY_DAYS_MS = 60 * 24 * 60 * 60 * 1000

export default function ReceiptDetailModal({ receiptId, onClose }: Props) {
  const { data: receipt, isLoading, isError } = useReceipt(receiptId)
  const counterpartyMap = useCounterpartyMap()
  const { data: linkedDocument } = useDocument(receipt?.document_id ?? null)
  const { data: pendingDocs = [] } = useDocuments({ type: 'RECEIPT', status: 'PENDING', limit: 100 })
  const updateReceipt = useUpdateReceipt()

  const [sixtyDaysAgo] = useState(() => new Date(Date.now() - SIXTY_DAYS_MS).toISOString())

  // Recent unlinked docs + always include the currently linked doc
  const docsForSelect = useMemo(() => {
    const recent = pendingDocs.filter((d) => d.uploaded_at >= sixtyDaysAgo)
    if (linkedDocument && !recent.find((d) => d.id === linkedDocument.id)) {
      return [linkedDocument, ...recent]
    }
    return recent
  }, [pendingDocs, sixtyDaysAgo, linkedDocument])

  const handleOpenDocument = useCallback(async (id: string) => {
    const url = await documentsApi.getOpenUrl(id)
    window.open(url, '_blank')
  }, [])

  const handleDownloadDocument = useCallback(async (id: string, name: string) => {
    const url = await documentsApi.getDownloadUrl(id)
    const a = window.document.createElement('a')
    a.href = url
    a.download = name
    a.click()
  }, [])

  const handleDocumentChange = useCallback(
    (selectedId: string) => {
      if (!receiptId) return
      updateReceipt.mutate({
        id: receiptId,
        data: { document_id: selectedId || null },
      })
    },
    [receiptId, updateReceipt],
  )

  if (!receiptId) return null

  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl p-6 w-full max-w-2xl mx-4 overflow-y-auto max-h-[90vh] space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Детали чека</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading && (
          <p className="text-sm text-gray-500">Загрузка...</p>
        )}

        {isError && (
          <p className="text-sm text-red-500">Не удалось загрузить чек.</p>
        )}

        {receipt && (
          <>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-500">Дата</dt>
              <dd className="text-gray-900">{formatDate(receipt.paid_at)}</dd>

              <dt className="text-gray-500">Контрагент</dt>
              <dd className="text-gray-900">
                {receipt.counterparty_id
                  ? (counterpartyMap.get(receipt.counterparty_id) ?? receipt.counterparty_id)
                  : '—'}
              </dd>

              {receipt.fn && (
                <>
                  <dt className="text-gray-500">ФН</dt>
                  <dd className="text-gray-900 font-mono text-xs">{receipt.fn}</dd>
                </>
              )}
              {receipt.fd && (
                <>
                  <dt className="text-gray-500">ФД</dt>
                  <dd className="text-gray-900 font-mono text-xs">{receipt.fd}</dd>
                </>
              )}
              {receipt.fpd && (
                <>
                  <dt className="text-gray-500">ФПД</dt>
                  <dd className="text-gray-900 font-mono text-xs">{receipt.fpd}</dd>
                </>
              )}
            </dl>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                    <th className="pb-2 font-medium">Наименование</th>
                    <th className="pb-2 font-medium text-center px-2">Кол-во</th>
                    <th className="pb-2 font-medium text-center px-2">Ед. изм.</th>
                    <th className="pb-2 font-medium text-right">Цена</th>
                    <th className="pb-2 font-medium text-right">Сумма</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {receipt.items.map((item) => (
                    <tr key={item.id}>
                      <td className="py-2 text-gray-800">{item.name}</td>
                      <td className="py-2 px-2 text-center tabular-nums text-gray-600">
                        {Number(item.quantity).toLocaleString('ru')}
                      </td>
                      <td className="py-2 px-2 text-center text-gray-500 text-xs">{item.unit ?? '—'}</td>
                      <td className="py-2 text-right tabular-nums text-gray-600">
                        {Number(item.price).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                      </td>
                      <td className="py-2 text-right tabular-nums text-gray-900">
                        {Number(item.amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-gray-300">
                    <td colSpan={4} className="pt-2 font-semibold text-gray-900">Итого</td>
                    <td className="pt-2 text-right tabular-nums font-semibold text-gray-900">
                      {Number(receipt.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="space-y-2">
              <label className="block text-sm text-gray-500">Документ</label>
              <select
                value={receipt.document_id ?? ''}
                onChange={(e) => handleDocumentChange(e.target.value)}
                disabled={updateReceipt.isPending}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                <option value="">Не привязан</option>
                {docsForSelect.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.name}
                  </option>
                ))}
              </select>

              {receipt.document_id && (
                <div className="flex gap-3">
                  <button
                    onClick={() => handleOpenDocument(receipt.document_id!)}
                    className="text-sm text-indigo-600 hover:underline"
                  >
                    Открыть
                  </button>
                  <button
                    onClick={() =>
                      handleDownloadDocument(
                        receipt.document_id!,
                        linkedDocument?.name ?? 'document',
                      )
                    }
                    className="text-sm text-gray-500 hover:underline"
                  >
                    Скачать
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

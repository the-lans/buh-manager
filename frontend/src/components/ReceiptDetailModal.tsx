import { documentsApi } from '../api/documents'
import { useCounterpartyMap } from '../hooks/useCounterparties'
import { useDocument } from '../hooks/useDocuments'
import { useReceipt } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'

interface Props {
  receiptId: string | null
  onClose: () => void
}

export default function ReceiptDetailModal({ receiptId, onClose }: Props) {
  const { data: receipt, isLoading, isError } = useReceipt(receiptId)
  const counterpartyMap = useCounterpartyMap()
  const { data: document } = useDocument(receipt?.document_id ?? null)

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
                    <th className="pb-2 font-medium text-right">Кол-во</th>
                    <th className="pb-2 font-medium text-right">Цена</th>
                    <th className="pb-2 font-medium text-right">Сумма</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {receipt.items.map((item) => (
                    <tr key={item.id}>
                      <td className="py-2 text-gray-800">{item.name}</td>
                      <td className="py-2 text-right tabular-nums text-gray-600">
                        {Number(item.quantity).toLocaleString('ru')}
                        {item.unit ? ` ${item.unit}` : ''}
                      </td>
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
                    <td colSpan={3} className="pt-2 font-semibold text-gray-900">Итого</td>
                    <td className="pt-2 text-right tabular-nums font-semibold text-gray-900">
                      {Number(receipt.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
            {receipt.document_id && (
              <div className="border border-gray-200 rounded-lg px-4 py-3 flex items-center justify-between gap-4 text-sm">
                <span className="text-gray-600 truncate">
                  📄 {document?.name ?? 'Документ'}
                </span>
                <div className="flex gap-3 shrink-0">
                  <button
                    onClick={() => window.open(documentsApi.downloadUrl(receipt.document_id!), '_blank')}
                    className="text-indigo-600 hover:underline"
                  >
                    Открыть
                  </button>
                  <a
                    href={documentsApi.downloadUrl(receipt.document_id)}
                    download={document?.name}
                    className="text-gray-500 hover:underline"
                  >
                    Скачать
                  </a>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

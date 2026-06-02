import { useCounterpartyMap } from '../hooks/useCounterparties'
import { useDocument } from '../hooks/useDocuments'
import { useReceipts } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'

interface Props {
  documentId: string | null
  onClose: () => void
}

const DOC_TYPE_LABELS: Record<string, string> = {
  RECEIPT: 'Чек',
  BANK_STATEMENT: 'Выписка',
}

const STATUS_LABELS: Record<string, string> = {
  PENDING: 'Ожидает',
  PROCESSED: 'Обработан',
  ERROR: 'Ошибка',
}

export default function DocumentDetailModal({ documentId, onClose }: Props) {
  const { data: doc, isLoading, isError } = useDocument(documentId)
  const { data: linkedReceipts = [] } = useReceipts({
    document_id: documentId ?? undefined,
    limit: 1,
    enabled: !!documentId && doc?.type === 'RECEIPT',
  })
  const counterpartyMap = useCounterpartyMap()

  const linkedReceipt = linkedReceipts[0] ?? null

  if (!documentId) return null

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
          <h2 className="text-lg font-semibold text-gray-900">Карточка документа</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading && <p className="text-sm text-gray-500">Загрузка...</p>}
        {isError && <p className="text-sm text-red-500">Не удалось загрузить документ.</p>}

        {doc && (
          <>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-500">Название</dt>
              <dd className="text-gray-900 break-all">{doc.name}</dd>

              <dt className="text-gray-500">Тип</dt>
              <dd className="text-gray-900">{DOC_TYPE_LABELS[doc.type] ?? doc.type}</dd>

              <dt className="text-gray-500">Статус</dt>
              <dd className="text-gray-900">{STATUS_LABELS[doc.status] ?? doc.status}</dd>

              <dt className="text-gray-500">Загружен</dt>
              <dd className="text-gray-900">{formatDate(doc.uploaded_at)}</dd>

              {doc.email_source && (
                <>
                  <dt className="text-gray-500">Email-источник</dt>
                  <dd className="text-gray-900">{doc.email_source}</dd>
                </>
              )}
            </dl>

            {linkedReceipt && (
              <div className="border border-gray-200 rounded-lg p-3 space-y-1">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Привязанный чек</p>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <dt className="text-gray-500">Дата</dt>
                  <dd className="text-gray-900">{formatDate(linkedReceipt.paid_at)}</dd>

                  <dt className="text-gray-500">Сумма</dt>
                  <dd className="text-gray-900 tabular-nums">
                    {Number(linkedReceipt.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                  </dd>

                  <dt className="text-gray-500">Контрагент</dt>
                  <dd className="text-gray-900">
                    {linkedReceipt.counterparty_id
                      ? (counterpartyMap.get(linkedReceipt.counterparty_id) ?? linkedReceipt.counterparty_id)
                      : '—'}
                  </dd>
                </dl>
              </div>
            )}

            {doc.payload && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Дополнительные сведения</p>
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto max-h-60 whitespace-pre-wrap break-all">
                  {JSON.stringify(doc.payload, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

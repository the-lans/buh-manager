import { useCallback, useRef, useState } from 'react'

import { documentsApi } from '../api/documents'
import { DataTable } from '../components/DataTable'
import { StatusBadge } from '../components/StatusBadge'
import { useAccounts } from '../hooks/useAccounts'
import {
  useLinkDocumentToReceipt,
  useLinkDocumentToStatement,
  useDocuments,
  useUploadDocument,
} from '../hooks/useDocuments'
import { useReceipts } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'
import type { Document } from '../types'

const PAGE_SIZE = 20

const DOC_TYPE_LABELS: Record<string, string> = {
  RECEIPT: 'Чек',
  BANK_STATEMENT: 'Выписка',
}

function extractErrorMessage(e: unknown): string {
  if (e && typeof e === 'object' && 'response' in e) {
    const resp = (e as { response?: { data?: { detail?: unknown } } }).response
    const detail = resp?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String((detail as { message: string }).message)
    }
    if (typeof detail === 'string') return detail
  }
  return 'Произошла ошибка'
}

export default function Documents() {
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [skip, setSkip] = useState(0)

  const { data: documents = [], isLoading } = useDocuments({
    type: typeFilter || undefined,
    status: statusFilter || undefined,
    skip,
    limit: PAGE_SIZE,
  })

  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadDocType, setUploadDocType] = useState('BANK_STATEMENT')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const upload = useUploadDocument()

  const [processDoc, setProcessDoc] = useState<Document | null>(null)
  const [linkReceiptId, setLinkReceiptId] = useState('')
  const [linkAccountId, setLinkAccountId] = useState('')
  const [linkStart, setLinkStart] = useState('')
  const [linkEnd, setLinkEnd] = useState('')
  const [linkError, setLinkError] = useState<string | null>(null)

  const linkReceipt = useLinkDocumentToReceipt()
  const linkStatement = useLinkDocumentToStatement()
  const { data: receiptList = [] } = useReceipts({ limit: 200 })
  const { data: accounts = [] } = useAccounts()

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

  async function handleUpload() {
    if (!uploadFile) return
    setUploadError(null)
    try {
      await upload.mutateAsync({ file: uploadFile, docType: uploadDocType })
      setUploadOpen(false)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (e: unknown) {
      if (
        e &&
        typeof e === 'object' &&
        'response' in e &&
        (e as { response?: { status?: number } }).response?.status === 409
      ) {
        setUploadError('Такой документ уже существует в системе.')
      } else {
        setUploadError(extractErrorMessage(e))
      }
    }
  }

  function openProcess(doc: Document) {
    setProcessDoc(doc)
    setLinkReceiptId('')
    setLinkAccountId('')
    setLinkStart('')
    setLinkEnd('')
    setLinkError(null)
  }

  async function handleProcess() {
    if (!processDoc) return
    setLinkError(null)
    try {
      if (processDoc.type === 'RECEIPT') {
        const result = await linkReceipt.mutateAsync({
          documentId: processDoc.id,
          receiptId: linkReceiptId,
        })
        if (result.status === 'ERROR') {
          setLinkError(result.message ?? 'Ошибка привязки.')
          return
        }
      } else {
        const result = await linkStatement.mutateAsync({
          documentId: processDoc.id,
          accountId: linkAccountId,
          start: new Date(linkStart).toISOString(),
          end: new Date(linkEnd).toISOString(),
        })
        if (result.status === 'ERROR') {
          setLinkError(result.message ?? 'Ошибка привязки.')
          return
        }
      }
      setProcessDoc(null)
    } catch (e: unknown) {
      setLinkError(extractErrorMessage(e))
    }
  }

  const canProcess =
    processDoc?.type === 'RECEIPT'
      ? !!linkReceiptId
      : !!linkAccountId && !!linkStart && !!linkEnd && linkStart < linkEnd

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Документы</h1>
        <button
          onClick={() => {
            setUploadOpen(true)
            setUploadError(null)
            setUploadFile(null)
          }}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          Загрузить
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setSkip(0) }}
        >
          <option value="">Все типы</option>
          <option value="RECEIPT">Чек</option>
          <option value="BANK_STATEMENT">Выписка</option>
        </select>
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setSkip(0) }}
        >
          <option value="">Все статусы</option>
          <option value="PENDING">Ожидает</option>
          <option value="PROCESSED">Обработан</option>
          <option value="ERROR">Ошибка</option>
        </select>
      </div>

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
              <div className="flex gap-2 flex-wrap">
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
                {doc.status === 'PENDING' && (
                  <button
                    onClick={() => openProcess(doc)}
                    className="text-xs text-emerald-600 hover:underline"
                  >
                    Обработать
                  </button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </DataTable>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
          disabled={skip === 0}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
        >
          ← Назад
        </button>
        <button
          onClick={() => setSkip((s) => s + PAGE_SIZE)}
          disabled={documents.length < PAGE_SIZE}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
        >
          Вперёд →
        </button>
      </div>

      {/* Upload modal */}
      {uploadOpen && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setUploadOpen(false)}
        >
          <div
            className="bg-white rounded-xl p-6 space-y-4 w-full max-w-md mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-semibold text-gray-900">Загрузить документ</h2>
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Тип документа</label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="BANK_STATEMENT">Выписка</option>
                  <option value="RECEIPT">Чек</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Файл</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-gray-600"
                />
              </div>
            </div>
            {uploadError && <p className="text-sm text-red-500">{uploadError}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setUploadOpen(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Отмена
              </button>
              <button
                onClick={handleUpload}
                disabled={!uploadFile || upload.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {upload.isPending ? 'Загрузка...' : 'Загрузить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Process document modal */}
      {processDoc && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setProcessDoc(null)}
        >
          <div
            className="bg-white rounded-xl p-6 space-y-4 w-full max-w-md mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-semibold text-gray-900">
              Обработать документ: {processDoc.name}
            </h2>

            {processDoc.type === 'RECEIPT' ? (
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Выберите чек</label>
                <select
                  value={linkReceiptId}
                  onChange={(e) => setLinkReceiptId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">— выберите чек —</option>
                  {receiptList
                    .filter((r) => r.document_id === null)
                    .map((r) => (
                      <option key={r.id} value={r.id}>
                        {formatDate(r.paid_at)} — {Number(r.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
                      </option>
                    ))}
                </select>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">Счёт</label>
                  <select
                    value={linkAccountId}
                    onChange={(e) => setLinkAccountId(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">— выберите счёт —</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.bank} ···{a.account_number.slice(-4)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">Дата начала</label>
                  <input
                    type="datetime-local"
                    value={linkStart}
                    onChange={(e) => setLinkStart(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">Дата конца</label>
                  <input
                    type="datetime-local"
                    value={linkEnd}
                    onChange={(e) => setLinkEnd(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                {linkStart && linkEnd && linkStart >= linkEnd && (
                  <p className="text-xs text-red-500">Дата начала должна быть раньше даты конца</p>
                )}
              </div>
            )}

            {linkError && <p className="text-sm text-red-500">{linkError}</p>}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setProcessDoc(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Отмена
              </button>
              <button
                onClick={handleProcess}
                disabled={
                  !canProcess ||
                  linkReceipt.isPending ||
                  linkStatement.isPending
                }
                className="px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 disabled:opacity-50"
              >
                {linkReceipt.isPending || linkStatement.isPending ? 'Сохранение...' : 'Привязать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

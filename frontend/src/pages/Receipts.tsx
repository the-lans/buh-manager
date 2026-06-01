import { useState } from 'react'

import { DataTable } from '../components/DataTable'
import ReceiptDetailModal from '../components/ReceiptDetailModal'
import { useCounterpartyMap } from '../hooks/useCounterparties'
import { useDeleteReceipt, useReceipts } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'

const PAGE_SIZE = 20

export default function Receipts() {
  const [skip, setSkip] = useState(0)
  const { data: receipts = [], isLoading } = useReceipts({ skip, limit: PAGE_SIZE })
  const counterpartyMap = useCounterpartyMap()
  const deleteReceipt = useDeleteReceipt()
  const [selectedReceiptId, setSelectedReceiptId] = useState<string | null>(null)

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Чеки</h1>
      <DataTable
        columns={[
          { label: 'Дата' },
          { label: 'Контрагент' },
          { label: 'Сумма', align: 'right' },
          { label: '' },
        ]}
        isEmpty={receipts.length === 0}
        emptyMessage="Нет чеков"
        isLoading={isLoading}
      >
        {receipts.map((r) => (
          <tr
            key={r.id}
            className="cursor-pointer hover:bg-gray-50"
            onClick={() => setSelectedReceiptId(r.id)}
          >
            <td className="px-4 py-2 text-gray-600">{formatDate(r.paid_at)}</td>
            <td className="px-4 py-2 text-gray-800">
              {r.counterparty_id ? (counterpartyMap.get(r.counterparty_id) ?? r.counterparty_id) : '—'}
            </td>
            <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
              {Number(r.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
            </td>
            <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => deleteReceipt.mutate(r.id)}
                className="text-xs text-red-500 hover:underline"
              >
                Удалить
              </button>
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
          disabled={receipts.length < PAGE_SIZE}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
        >
          Вперёд →
        </button>
      </div>

      <ReceiptDetailModal
        receiptId={selectedReceiptId}
        onClose={() => setSelectedReceiptId(null)}
      />
    </div>
  )
}

import { useReceipts, useDeleteReceipt } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'
import { DataTable } from '../components/DataTable'

export default function Receipts() {
  const { data: receipts = [], isLoading } = useReceipts({ limit: 50 })
  const deleteReceipt = useDeleteReceipt()

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
          <tr key={r.id}>
            <td className="px-4 py-2 text-gray-600">{formatDate(r.paid_at)}</td>
            <td className="px-4 py-2 text-gray-800">{r.counterparty_id ?? '—'}</td>
            <td className="px-4 py-2 text-right tabular-nums font-medium text-gray-900">
              {Number(r.total_amount).toLocaleString('ru', { minimumFractionDigits: 2 })} ₽
            </td>
            <td className="px-4 py-2">
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
    </div>
  )
}

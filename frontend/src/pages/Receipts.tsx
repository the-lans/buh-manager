import { useReceipts, useDeleteReceipt } from '../hooks/useReceipts'
import { formatDate } from '../utils/date'

export default function Receipts() {
  const { data: receipts = [], isLoading } = useReceipts({ limit: 50 })
  const deleteReceipt = useDeleteReceipt()

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-gray-900">Чеки</h1>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Загрузка...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Дата</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Контрагент</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600 tabular-nums">Сумма</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
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
              {receipts.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">Нет чеков</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

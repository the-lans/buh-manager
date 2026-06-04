import { useState } from 'react'

import { useApplyClassifierRules } from '../hooks/useClassifierRules'

interface Props {
  onClose: () => void
}

export default function RuleFillModal({ onClose }: Props) {
  const apply = useApplyClassifierRules()
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [result, setResult] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleApply() {
    setError(null)
    if (!startDate || !endDate) { setError('Укажите период'); return }
    if (startDate > endDate) { setError('Дата начала должна быть раньше даты конца'); return }
    try {
      const res = await apply.mutateAsync({
        start_date: `${startDate}T00:00:00`,
        end_date: `${endDate}T23:59:59`,
      })
      setResult(res.updated_count)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Ошибка применения правил')
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl p-6 w-full max-w-sm mx-4 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Заполнить правилами</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        {result === null ? (
          <>
            <p className="text-sm text-gray-500">
              Правила применятся ко всем транзакциям за выбранный период.
            </p>
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Начало периода</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Конец периода</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
                Отмена
              </button>
              <button
                onClick={handleApply}
                disabled={apply.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {apply.isPending ? 'Применяю...' : 'Применить'}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-gray-700">
              Обновлено транзакций: <span className="font-semibold text-indigo-700">{result}</span>
            </p>
            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
              >
                Закрыть
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

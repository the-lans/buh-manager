const STYLES: Record<string, string> = {
  UNMATCHED: 'bg-yellow-100 text-yellow-700',
  MATCHED: 'bg-green-100 text-green-700',
  NOT_REQUIRED: 'bg-gray-100 text-gray-500',
  IGNORED_BY_USER: 'bg-gray-100 text-gray-400',
}

const LABELS: Record<string, string> = {
  UNMATCHED: 'Не сверено',
  MATCHED: 'Сверено',
  NOT_REQUIRED: 'Не требуется',
  IGNORED_BY_USER: 'Игнорируется',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${STYLES[status] ?? ''}`}>
      {LABELS[status] ?? status}
    </span>
  )
}

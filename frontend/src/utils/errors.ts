/**
 * Extract a human-readable error message from an Axios-style error response.
 * Falls back to a generic message when the response shape is unrecognised.
 */
export function extractApiError(e: unknown, fallback = 'Произошла ошибка'): string {
  if (e && typeof e === 'object' && 'response' in e) {
    const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String((detail as { message: string }).message)
    }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
    }
  }
  return fallback
}

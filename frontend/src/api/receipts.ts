import { apiClient } from './client'
import type { Receipt, ReceiptListItem } from '../types'

export const receiptsApi = {
  list: (params?: { skip?: number; limit?: number; document_id?: string; unmatched?: boolean; max_age_days?: number }) =>
    apiClient.get<ReceiptListItem[]>('/receipts', { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Receipt>(`/receipts/${id}`).then((r) => r.data),
  create: (data: object) => apiClient.post<Receipt>('/receipts', data).then((r) => r.data),
  update: (id: string, data: object) =>
    apiClient.put<Receipt>(`/receipts/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/receipts/${id}`),
}

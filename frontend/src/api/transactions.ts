import { apiClient } from './client'
import type { Transaction } from '../types'

export interface TransactionFilters {
  account_id?: string
  type?: string
  reconciled_status?: string
  import_status?: string
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}

export const transactionsApi = {
  list: (filters?: TransactionFilters) =>
    apiClient.get<Transaction[]>('/transactions', { params: filters }).then((r) => r.data),
  create: (data: Partial<Transaction>) =>
    apiClient.post<Transaction>('/transactions', data).then((r) => r.data),
  update: (id: string, data: Partial<Transaction>) =>
    apiClient.put<Transaction>(`/transactions/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/transactions/${id}`),
}

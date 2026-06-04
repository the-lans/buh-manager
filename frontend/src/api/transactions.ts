import { apiClient } from './client'
import type { Transaction } from '../types'

export interface TransactionFilters {
  account_id?: string
  type?: string
  reconciled_status?: string
  import_status?: string
  start_date?: string
  end_date?: string
  skip?: number
  limit?: number
}

export interface TransactionCreatePayload {
  account_id: string
  occurred_at: string
  amount: string
  type: string
  expense_type_id?: string | null
  processed_at?: string | null
  auth_code?: string | null
  bank_category?: string | null
  description?: string | null
  balance_after?: string | null
}

export interface TransactionUpdatePayload {
  occurred_at?: string
  amount?: string
  type?: string
  bank_category?: string | null
  expense_type_id?: string
  description?: string | null
}

export const transactionsApi = {
  list: (filters?: TransactionFilters) =>
    apiClient.get<Transaction[]>('/transactions', { params: filters }).then((r) => r.data),
  create: (data: TransactionCreatePayload) =>
    apiClient.post<Transaction>('/transactions', data).then((r) => r.data),
  update: (id: string, data: TransactionUpdatePayload) =>
    apiClient.put<Transaction>(`/transactions/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/transactions/${id}`),
}

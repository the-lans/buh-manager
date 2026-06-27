import { apiClient } from './client'
import type { Transaction } from '../types'

export interface TransactionFilters {
  account_id?: string
  type?: string
  reconciled_status?: string
  import_status?: string
  expense_type_id?: string
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
  apply_rules?: boolean
}

export interface TransactionUpdatePayload {
  occurred_at?: string
  amount?: string
  type?: string
  bank_category?: string | null
  expense_type_id?: string
  description?: string | null
  apply_rules?: boolean
  receipt_id?: string | null
}

export interface ExpenseTypeSummaryItem {
  expense_type_id: string
  count: number
  total: string
}

export interface ExpenseTypeSummaryResponse {
  unmatched_count: number
  expenses: ExpenseTypeSummaryItem[]
  income: ExpenseTypeSummaryItem[]
  turnover: ExpenseTypeSummaryItem[]
}

export const transactionsApi = {
  list: (filters?: TransactionFilters) =>
    apiClient.get<Transaction[]>('/transactions', { params: filters }).then((r) => r.data),
  expenseTypeSummary: (params: { start_date?: string; end_date?: string }) =>
    apiClient
      .get<ExpenseTypeSummaryResponse>('/transactions/expense-type-summary', { params })
      .then((r) => r.data),
  create: (data: TransactionCreatePayload) =>
    apiClient.post<Transaction>('/transactions', data).then((r) => r.data),
  update: (id: string, data: TransactionUpdatePayload) =>
    apiClient.put<Transaction>(`/transactions/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/transactions/${id}`),
}

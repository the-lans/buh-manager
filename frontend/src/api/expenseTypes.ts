import { apiClient } from './client'
import type { ExpenseType } from '../types'

export const expenseTypesApi = {
  list: () => apiClient.get<ExpenseType[]>('/expense-types').then((r) => r.data),
  create: (data: ExpenseType) => apiClient.post<ExpenseType>('/expense-types', data).then((r) => r.data),
  update: (id: string, data: Partial<ExpenseType>) =>
    apiClient.put<ExpenseType>(`/expense-types/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/expense-types/${id}`),
}

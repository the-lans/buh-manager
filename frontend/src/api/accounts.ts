import { apiClient } from './client'
import type { Account, AccountCreate, AccountUpdate } from '../types'

export const accountsApi = {
  list: () => apiClient.get<Account[]>('/accounts').then((r) => r.data),
  create: (data: AccountCreate) => apiClient.post<Account>('/accounts', data).then((r) => r.data),
  update: (id: string, data: AccountUpdate) =>
    apiClient.put<Account>(`/accounts/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/accounts/${id}`),
  initBalance: (id: string, amount: number, recorded_at: string, source: 'OPENING' | 'CLOSING') =>
    apiClient
      .post(`/accounts/${id}/initialize-balance`, { amount, recorded_at, source })
      .then((r) => r.data),
}

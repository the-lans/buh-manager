import type { Counterparty, CounterpartyCreate, CounterpartyUpdate } from '../types'
import { apiClient } from './client'

export const counterpartiesApi = {
  list: () => apiClient.get<Counterparty[]>('/counterparties').then((r) => r.data),
  create: (data: CounterpartyCreate) =>
    apiClient.post<Counterparty>('/counterparties', data).then((r) => r.data),
  update: (id: string, data: CounterpartyUpdate) =>
    apiClient.put<Counterparty>(`/counterparties/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/counterparties/${id}`),
}

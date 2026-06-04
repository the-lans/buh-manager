import { apiClient } from './client'
import type { Balance } from '../types'

export const balancesApi = {
  list: (params?: { account_id?: string; skip?: number; limit?: number }): Promise<Balance[]> =>
    apiClient.get<Balance[]>('/balances', { params }).then((r) => r.data),
  calculate: (): Promise<Balance[]> =>
    apiClient.post<Balance[]>('/balances/calculate').then((r) => r.data),
}

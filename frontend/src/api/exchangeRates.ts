import { apiClient } from './client'
import type { ExchangeRate } from '../types'

export const exchangeRatesApi = {
  latest: () => apiClient.get<ExchangeRate[]>('/exchange-rates/latest').then((r) => r.data),
  create: (data: Omit<ExchangeRate, 'id'>) =>
    apiClient.post<ExchangeRate>('/exchange-rates', data).then((r) => r.data),
}

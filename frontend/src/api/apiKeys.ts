import { apiClient } from './client'
import type { ApiKey, ApiKeyCreate, ApiKeyCreated, ApiKeyUpdate } from '../types'

export const apiKeysApi = {
  list: () => apiClient.get<ApiKey[]>('/api-keys').then((r) => r.data),
  create: (data: ApiKeyCreate) => apiClient.post<ApiKeyCreated>('/api-keys', data).then((r) => r.data),
  update: (id: string, data: ApiKeyUpdate) =>
    apiClient.patch<ApiKey>(`/api-keys/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/api-keys/${id}`),
}

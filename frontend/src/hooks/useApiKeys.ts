import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi } from '../api/apiKeys'
import type { ApiKeyCreate, ApiKeyUpdate } from '../types'

export function useApiKeys() {
  return useQuery({ queryKey: ['api-keys'], queryFn: apiKeysApi.list })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ApiKeyCreate) => apiKeysApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })
}

export function useUpdateApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ApiKeyUpdate }) => apiKeysApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })
}

export function useDeleteApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiKeysApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
  })
}

import { useQuery } from '@tanstack/react-query'

import { documentsApi } from '../api/documents'

export function useDocuments(params?: { type?: string; status?: string; limit?: number }) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentsApi.list(params),
  })
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: () => documentsApi.get(id!),
    enabled: !!id,
  })
}

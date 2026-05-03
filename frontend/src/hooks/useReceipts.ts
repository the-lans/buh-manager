import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { receiptsApi } from '../api/receipts'

export function useReceipts(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['receipts', params],
    queryFn: () => receiptsApi.list(params),
  })
}

export function useDeleteReceipt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => receiptsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['receipts'] }),
  })
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { receiptsApi } from '../api/receipts'

export function useReceipts(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['receipts', params],
    queryFn: () => receiptsApi.list(params),
  })
}

export function useReceipt(id: string | null) {
  return useQuery({
    queryKey: ['receipts', id],
    queryFn: () => receiptsApi.get(id!),
    enabled: !!id,
  })
}

export function useUpdateReceipt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => receiptsApi.update(id, data),
    onSuccess: (receipt) => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.setQueryData(['receipts', receipt.id], receipt)
    },
  })
}

export function useDeleteReceipt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => receiptsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['receipts'] }),
  })
}

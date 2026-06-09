import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transactionsApi, type TransactionFilters, type TransactionCreatePayload, type TransactionUpdatePayload } from '../api/transactions'

export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
  })
}

export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TransactionCreatePayload) => transactionsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TransactionUpdatePayload }) =>
      transactionsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => transactionsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

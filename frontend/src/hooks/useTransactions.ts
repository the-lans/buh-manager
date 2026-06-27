import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transactionsApi, type TransactionFilters, type TransactionCreatePayload, type TransactionUpdatePayload } from '../api/transactions'

export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionsApi.list(filters),
  })
}

export function useExpenseTypeSummary(params: { start_date?: string; end_date?: string }) {
  return useQuery({
    queryKey: ['expense-type-summary', params],
    queryFn: () => transactionsApi.expenseTypeSummary(params),
  })
}

function invalidateTransactionQueries(qc: ReturnType<typeof useQueryClient>): void {
  qc.invalidateQueries({ queryKey: ['transactions'] })
  qc.invalidateQueries({ queryKey: ['expense-type-summary'] })
}

export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TransactionCreatePayload) => transactionsApi.create(data),
    onSuccess: () => invalidateTransactionQueries(qc),
  })
}

export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TransactionUpdatePayload }) =>
      transactionsApi.update(id, data),
    onSuccess: () => invalidateTransactionQueries(qc),
  })
}

export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => transactionsApi.delete(id),
    onSuccess: () => invalidateTransactionQueries(qc),
  })
}

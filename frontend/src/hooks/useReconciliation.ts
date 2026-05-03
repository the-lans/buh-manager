import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reconciliationApi } from '../api/reconciliation'

export function useReconciliationReport() {
  return useQuery({
    queryKey: ['reconciliationReport'],
    queryFn: reconciliationApi.getReport,
  })
}

export function useRunReconciliation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: reconciliationApi.run,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliationReport'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useManualMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ transactionId, receiptId }: { transactionId: string; receiptId: string }) =>
      reconciliationApi.match(transactionId, receiptId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

export function useIgnoreTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (transactionId: string) => reconciliationApi.ignore(transactionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

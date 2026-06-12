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
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })
}

export function useManualMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ transactionId, receiptId }: { transactionId: string; receiptId: string }) => {
      await reconciliationApi.match(transactionId, receiptId)
      return reconciliationApi.run()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliationReport'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })
}

export function useIgnoreTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (transactionId: string) => {
      await reconciliationApi.ignore(transactionId)
      return reconciliationApi.run()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliationReport'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })
}

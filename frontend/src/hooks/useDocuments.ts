import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { documentsApi } from '../api/documents'

export function useDocuments(params?: {
  type?: string
  status?: string
  skip?: number
  limit?: number
}) {
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

export function useUploadDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, docType }: { file: File; docType: string }) =>
      documentsApi.upload(file, docType),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })
}

export function useLinkDocumentToReceipt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ documentId, receiptId }: { documentId: string; receiptId: string }) =>
      documentsApi.linkToReceipt(documentId, receiptId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['receipts'] })
    },
  })
}

export function useLinkDocumentToStatement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      documentId,
      accountId,
      start,
      end,
    }: {
      documentId: string
      accountId: string
      start: string
      end: string
    }) => documentsApi.linkToStatement(documentId, accountId, start, end),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['balances'] })
    },
  })
}

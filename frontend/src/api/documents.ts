import { apiClient } from './client'
import type { Document, LinkResult } from '../types'

export const documentsApi = {
  upload: (file: File, doc_type = 'BANK_STATEMENT') => {
    const form = new FormData()
    form.append('file', file)
    return apiClient
      .post<Document>(`/documents?doc_type=${doc_type}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  list: (params?: { type?: string; status?: string; skip?: number; limit?: number }) =>
    apiClient.get<Document[]>('/documents', { params }).then((r) => r.data),
  get: (id: string) => apiClient.get<Document>(`/documents/${id}`).then((r) => r.data),
  getOpenUrl: (id: string): Promise<string> =>
    apiClient
      .get<{ url: string }>(`/documents/${id}/download?inline=true`)
      .then((r) => r.data.url),
  getDownloadUrl: (id: string): Promise<string> =>
    apiClient
      .get<{ url: string }>(`/documents/${id}/download`)
      .then((r) => r.data.url),
  linkToReceipt: (documentId: string, receiptId: string): Promise<LinkResult> =>
    apiClient
      .post<LinkResult>(`/documents/${documentId}/link-receipt`, { receipt_id: receiptId })
      .then((r) => r.data),
  linkToStatement: (
    documentId: string,
    accountId: string,
    start: string,
    end: string,
  ): Promise<LinkResult> =>
    apiClient
      .post<LinkResult>(`/documents/${documentId}/link-statement`, {
        account_id: accountId,
        statement_start: start,
        statement_end: end,
      })
      .then((r) => r.data),
}

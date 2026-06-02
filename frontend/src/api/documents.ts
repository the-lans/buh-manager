import { apiClient } from './client'
import type { Document, LinkResult } from '../types'

const JSON_CONTENT_TYPE = 'application/json'
const BANK_STATEMENT_DOC_TYPE = 'BANK_STATEMENT'

async function resolveDownloadResponse(id: string, inline: boolean): Promise<string> {
  const response = await apiClient.get<Blob>(`/documents/${id}/download`, {
    params: { inline },
    responseType: 'blob',
  })
  const contentType = String(response.headers['content-type'] ?? '')
  if (contentType.includes(JSON_CONTENT_TYPE)) {
    const payload = JSON.parse(await response.data.text()) as { url: string }
    return payload.url
  }
  return URL.createObjectURL(response.data)
}

export const documentsApi = {
  upload: (file: File, doc_type = BANK_STATEMENT_DOC_TYPE) => {
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
    resolveDownloadResponse(id, true),
  getDownloadUrl: (id: string): Promise<string> =>
    resolveDownloadResponse(id, false),
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
  reset: (documentId: string): Promise<Document> =>
    apiClient.post<Document>(`/documents/${documentId}/reset`).then((r) => r.data),
  update: (id: string, data: { payload?: Record<string, unknown> | null }): Promise<Document> =>
    apiClient.put<Document>(`/documents/${id}`, data).then((r) => r.data),
}

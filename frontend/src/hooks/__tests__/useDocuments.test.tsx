import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import {
  useDocuments,
  useUploadDocument,
  useLinkDocumentToReceipt,
  useLinkDocumentToStatement,
  useResetDocument,
} from '../useDocuments'
import { makeTestQueryClient } from '../../test/utils'
import { server } from '../../test/server'

function makeWrapper(qc?: QueryClient) {
  const client = qc ?? makeTestQueryClient()
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useDocuments', () => {
  it('fetches and returns documents list', async () => {
    const { result } = renderHook(() => useDocuments(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(2)
    expect(result.current.data![0]).toMatchObject({ id: 'doc-1', status: 'PENDING' })
  })

  it('passes type and status filters as query params', async () => {
    let receivedUrl: string | undefined
    server.use(
      http.get('/api/v1/documents', ({ request }) => {
        receivedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    const { result } = renderHook(
      () => useDocuments({ type: 'RECEIPT', status: 'PENDING' }),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(receivedUrl).toContain('type=RECEIPT')
    expect(receivedUrl).toContain('status=PENDING')
  })

  it('passes skip and limit pagination params', async () => {
    let receivedUrl: string | undefined
    server.use(
      http.get('/api/v1/documents', ({ request }) => {
        receivedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    const { result } = renderHook(
      () => useDocuments({ skip: 20, limit: 20 }),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(receivedUrl).toContain('skip=20')
    expect(receivedUrl).toContain('limit=20')
  })

  it('sets isError on server failure', async () => {
    server.use(http.get('/api/v1/documents', () => HttpResponse.error()))
    const { result } = renderHook(() => useDocuments(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useUploadDocument', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/documents', () =>
        HttpResponse.json(
          { id: 'doc-new', user_id: 'u', type: 'BANK_STATEMENT', url: '/', name: 'f.pdf', status: 'PENDING', uploaded_at: '2026-01-01T00:00:00' },
          { status: 201 },
        ),
      ),
    )
  })

  it('invalidates documents query after successful upload', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useUploadDocument(), { wrapper: makeWrapper(qc) })

    result.current.mutate({ file: new File(['content'], 'test.pdf'), docType: 'BANK_STATEMENT' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] })
  })

  it('transitions to isError on 409 duplicate', async () => {
    server.use(
      http.post('/api/v1/documents', () =>
        HttpResponse.json(
          { message: 'Document already exists.', document_id: 'doc-existing' },
          { status: 409 },
        ),
      ),
    )
    const { result } = renderHook(() => useUploadDocument(), { wrapper: makeWrapper() })
    result.current.mutate({ file: new File(['x'], 'x.pdf'), docType: 'RECEIPT' })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useLinkDocumentToReceipt', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/documents/:id/link-receipt', () =>
        HttpResponse.json({ document_id: 'doc-1', status: 'PROCESSED', updated_count: 1, message: null }),
      ),
    )
  })

  it('invalidates documents and receipts queries on success', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useLinkDocumentToReceipt(), { wrapper: makeWrapper(qc) })

    result.current.mutate({ documentId: 'doc-1', receiptId: 'rec-1' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['receipts'] })
  })

  it('returns ERROR status when document cannot be linked', async () => {
    server.use(
      http.post('/api/v1/documents/:id/link-receipt', () =>
        HttpResponse.json({ document_id: 'doc-1', status: 'ERROR', updated_count: 0, message: 'No match' }),
      ),
    )
    const { result } = renderHook(() => useLinkDocumentToReceipt(), { wrapper: makeWrapper() })
    result.current.mutate({ documentId: 'doc-1', receiptId: 'rec-999' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('ERROR')
  })
})

describe('useResetDocument', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/documents/:id/reset', ({ params }) =>
        HttpResponse.json({
          id: params.id,
          user_id: 'user-1',
          type: 'BANK_STATEMENT',
          url: '/',
          name: 'stmt.pdf',
          status: 'PENDING',
          uploaded_at: '2026-01-01T00:00:00',
          email_source: null,
          file_hash: 'abc',
        }),
      ),
    )
  })

  it('invalidates documents query after reset', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useResetDocument(), { wrapper: makeWrapper(qc) })

    result.current.mutate('doc-error')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] })
    expect(result.current.data?.status).toBe('PENDING')
  })

  it('transitions to isError when server returns 409', async () => {
    server.use(
      http.post('/api/v1/documents/:id/reset', () =>
        HttpResponse.json({ detail: 'Only documents with ERROR status can be reset.' }, { status: 409 }),
      ),
    )
    const { result } = renderHook(() => useResetDocument(), { wrapper: makeWrapper() })
    result.current.mutate('doc-pending')
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useLinkDocumentToStatement', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/documents/:id/link-statement', () =>
        HttpResponse.json({ document_id: 'doc-2', status: 'PROCESSED', updated_count: 5, message: null }),
      ),
    )
  })

  it('invalidates documents, transactions, and balances queries on success', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')
    const { result } = renderHook(() => useLinkDocumentToStatement(), { wrapper: makeWrapper(qc) })

    result.current.mutate({
      documentId: 'doc-2',
      accountId: 'acc-1',
      start: '2024-01-01T00:00:00',
      end: '2024-01-31T23:59:59',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transactions'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['balances'] })
  })
})

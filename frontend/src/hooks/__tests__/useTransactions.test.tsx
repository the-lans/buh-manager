import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import {
  useTransactions,
  useCreateTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
} from '../useTransactions'
import { makeTestQueryClient } from '../../test/utils'
import { server } from '../../test/server'

function makeWrapper(qc?: QueryClient) {
  const client = qc ?? makeTestQueryClient()
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useTransactions', () => {
  it('fetches and returns transactions list', async () => {
    const { result } = renderHook(() => useTransactions(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data![0]).toMatchObject({
      id: 'tx-1',
      amount: '-1500.00',
      type: 'EXPENSE',
    })
  })

  it('passes filters as query params', async () => {
    let receivedUrl: string | undefined
    server.use(
      http.get('/api/v1/transactions', ({ request }) => {
        receivedUrl = request.url
        return HttpResponse.json([])
      }),
    )

    const { result } = renderHook(
      () => useTransactions({ type: 'EXPENSE', reconciled_status: 'UNMATCHED' }),
      { wrapper: makeWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(receivedUrl).toContain('type=EXPENSE')
    expect(receivedUrl).toContain('reconciled_status=UNMATCHED')
  })

  it('returns empty array when no transactions exist', async () => {
    server.use(http.get('/api/v1/transactions', () => HttpResponse.json([])))

    const { result } = renderHook(() => useTransactions(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(0)
  })

  it('sets isError on server failure', async () => {
    server.use(http.get('/api/v1/transactions', () => HttpResponse.error()))

    const { result } = renderHook(() => useTransactions(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useUpdateTransaction', () => {
  beforeEach(() => {
    server.use(
      http.put('/api/v1/transactions/:id', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 'tx-1', ...body })
      }),
    )
  })

  it('invalidates transactions query after successful update', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useUpdateTransaction(), { wrapper: makeWrapper(qc) })

    result.current.mutate({ id: 'tx-1', data: { description: 'Обед' } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transactions'] })
  })
})

describe('useCreateTransaction', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/transactions', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 'tx-new', ...body }, { status: 201 })
      }),
    )
  })

  it('invalidates transactions query after successful creation', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useCreateTransaction(), { wrapper: makeWrapper(qc) })

    result.current.mutate({
      account_id: 'acc-1',
      occurred_at: '2026-04-01T10:00:00',
      amount: '-500.00',
      type: 'EXPENSE',
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transactions'] })
  })
})

describe('useDeleteTransaction', () => {
  beforeEach(() => {
    server.use(
      http.delete('/api/v1/transactions/:id', () => new HttpResponse(null, { status: 204 })),
    )
  })

  it('invalidates transactions query after deletion', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteTransaction(), { wrapper: makeWrapper(qc) })

    result.current.mutate('tx-1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transactions'] })
  })
})

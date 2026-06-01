import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { useBalances } from '../useBalances'
import { makeTestQueryClient } from '../../test/utils'
import { server } from '../../test/server'

function makeWrapper() {
  const client = makeTestQueryClient()
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useBalances', () => {
  it('fetches and returns balances list', async () => {
    const { result } = renderHook(() => useBalances(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(2)
    expect(result.current.data![0]).toMatchObject({ id: 'bal-1', source: 'OPENING' })
  })

  it('passes account_id as query param', async () => {
    let receivedUrl: string | undefined
    server.use(
      http.get('/api/v1/balances', ({ request }) => {
        receivedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    const { result } = renderHook(
      () => useBalances({ account_id: 'acc-1' }),
      { wrapper: makeWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(receivedUrl).toContain('account_id=acc-1')
  })

  it('returns empty array when no balances exist', async () => {
    server.use(http.get('/api/v1/balances', () => HttpResponse.json([])))
    const { result } = renderHook(() => useBalances(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(0)
  })

  it('sets isError on server failure', async () => {
    server.use(http.get('/api/v1/balances', () => HttpResponse.error()))
    const { result } = renderHook(() => useBalances(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

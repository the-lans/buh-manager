import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { useAccounts, useCreateAccount, useUpdateAccount, useDeleteAccount } from '../useAccounts'
import { makeTestQueryClient } from '../../test/utils'
import { server } from '../../test/server'

function makeWrapper(qc?: QueryClient) {
  const client = qc ?? makeTestQueryClient()
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useAccounts', () => {
  it('fetches and returns accounts list', async () => {
    const { result } = renderHook(() => useAccounts(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data![0]).toMatchObject({ bank: 'Сбербанк', currency: 'RUB' })
  })

  it('sets isError when server returns network error', async () => {
    server.use(http.get('/api/v1/accounts', () => HttpResponse.error()))

    const { result } = renderHook(() => useAccounts(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useCreateAccount', () => {
  it('invalidates accounts query after successful creation', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useCreateAccount(), { wrapper: makeWrapper(qc) })

    result.current.mutate({ bank: 'ТБанк', account_number: '40817900', currency: 'RUB' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['accounts'] })
  })
})

describe('useUpdateAccount', () => {
  it('invalidates accounts query after successful update', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useUpdateAccount(), { wrapper: makeWrapper(qc) })

    result.current.mutate({ id: 'acc-1', data: { bank: 'ТБанк' } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['accounts'] })
  })
})

describe('useDeleteAccount', () => {
  it('invalidates accounts query after deletion', async () => {
    const qc = makeTestQueryClient()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteAccount(), { wrapper: makeWrapper(qc) })

    result.current.mutate('acc-1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['accounts'] })
  })
})

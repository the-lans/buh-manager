import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth } from '../useAuth'
import { makeJwt } from '../../test/utils'

const TOKEN_KEY = 'buh_token'

describe('useAuth', () => {
  beforeEach(() => sessionStorage.clear())

  it('returns unauthenticated when no token in sessionStorage', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('returns authenticated user for valid unexpired token', () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    sessionStorage.setItem(TOKEN_KEY, makeJwt({ sub: 'user-1', email: 'a@b.com', exp }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toEqual({ id: 'user-1', email: 'a@b.com' })
  })

  it('returns unauthenticated and clears token when expired', () => {
    const exp = Math.floor(Date.now() / 1000) - 1
    sessionStorage.setItem(TOKEN_KEY, makeJwt({ sub: 'user-1', email: 'a@b.com', exp }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
  })

  it('returns unauthenticated and clears token when JWT is malformed', () => {
    sessionStorage.setItem(TOKEN_KEY, 'not.a.valid.jwt')

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(false)
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
  })

  it('provides logout function that clears token', () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    sessionStorage.setItem(TOKEN_KEY, makeJwt({ sub: 'user-1', email: 'a@b.com', exp }))
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost/' },
      writable: true,
      configurable: true,
    })

    const { result } = renderHook(() => useAuth())
    result.current.logout()

    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(window.location.href).toBe('/login')
  })
})

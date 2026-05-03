import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { apiClient, setToken, clearToken } from '../client'
import { server } from '../../test/server'

const TOKEN_KEY = 'buh_token'

describe('apiClient', () => {
  beforeEach(() => {
    sessionStorage.clear()
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost/' },
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('attaches Bearer token from sessionStorage to requests', async () => {
    let authHeader: string | null = null
    server.use(
      http.get('/api/v1/auth/me', ({ request }) => {
        authHeader = request.headers.get('Authorization')
        return HttpResponse.json({ id: 'user-1' })
      }),
    )

    setToken('test-token-123')
    await apiClient.get('/auth/me')

    expect(authHeader).toBe('Bearer test-token-123')
  })

  it('sends no Authorization header when token is absent', async () => {
    let authHeader: string | null = 'present'
    server.use(
      http.get('/api/v1/auth/me', ({ request }) => {
        authHeader = request.headers.get('Authorization')
        return HttpResponse.json({ id: 'user-1' })
      }),
    )

    clearToken()
    await apiClient.get('/auth/me')

    expect(authHeader).toBeNull()
  })

  it('clears token and redirects to /login on 401 response', async () => {
    server.use(
      http.get('/api/v1/auth/me', () =>
        HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 }),
      ),
    )

    setToken('expired-token')
    try {
      await apiClient.get('/auth/me')
    } catch {
      // axios rejects on 4xx
    }

    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(window.location.href).toBe('/login')
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import AuthCallback from '../AuthCallback'
import { makeJwt } from '../../test/utils'

const TOKEN_KEY = 'buh_token'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const mod = await importOriginal<typeof import('react-router-dom')>()
  return { ...mod, useNavigate: () => mockNavigate }
})

describe('AuthCallback', () => {
  beforeEach(() => {
    sessionStorage.clear()
    mockNavigate.mockReset()
  })

  function renderWithSearch(search: string) {
    vi.stubGlobal('location', { search, hash: '', pathname: '/auth/callback' })
    vi.stubGlobal('history', { replaceState: vi.fn() })
    return render(
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<AuthCallback />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('saves token and navigates to / when token is in URL fragment', async () => {
    const token = makeJwt({ sub: 'user-1', email: 'a@b.com', exp: 9999999999 })
    vi.stubGlobal('location', { search: '', hash: `#token=${token}`, pathname: '/auth/callback' })
    vi.stubGlobal('history', { replaceState: vi.fn() })
    render(
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<AuthCallback />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(sessionStorage.getItem(TOKEN_KEY)).toBe(token)
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })

  it('navigates to /login when token is absent', async () => {
    renderWithSearch('')

    await waitFor(() => {
      expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull()
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })

  it('shows spinner text while processing', () => {
    vi.stubGlobal('location', { search: '', hash: '', pathname: '/auth/callback' })
    vi.stubGlobal('history', { replaceState: vi.fn() })
    const { getByText } = render(
      <MemoryRouter>
        <AuthCallback />
      </MemoryRouter>,
    )
    expect(getByText('Выполняется вход...')).toBeInTheDocument()
  })
})

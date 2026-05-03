import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { makeTestQueryClient, makeJwt } from '../test/utils'

const TOKEN_KEY = 'buh_token'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function renderApp(initialPath: string) {
  const qc = makeTestQueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => sessionStorage.clear())

  it('redirects to /login when user is not authenticated', () => {
    renderApp('/dashboard')
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('renders children when user is authenticated', () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    sessionStorage.setItem(TOKEN_KEY, makeJwt({ sub: 'user-1', email: 'a@b.com', exp }))

    renderApp('/dashboard')
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})

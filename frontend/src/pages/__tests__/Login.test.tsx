import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Login from '../Login'

describe('Login', () => {
  beforeEach(() => {
    vi.stubGlobal('location', { href: '' })
  })

  it('renders the app title and login button', () => {
    render(<Login />)
    expect(screen.getByText('Личный бухгалтер')).toBeInTheDocument()
    expect(screen.getByText('Войти через Google')).toBeInTheDocument()
  })

  it('redirects to Google OAuth endpoint on button click', async () => {
    render(<Login />)
    await userEvent.click(screen.getByText('Войти через Google'))
    expect(window.location.href).toBe('/api/v1/auth/google')
  })
})

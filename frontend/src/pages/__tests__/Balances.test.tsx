import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Balances from '../Balances'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Balance } from '../../types'

describe('Balances page', () => {
  it('renders the Вычислить button', () => {
    renderWithProviders(<Balances />)
    expect(screen.getByRole('button', { name: 'Вычислить' })).toBeInTheDocument()
  })

  it('calls POST /balances/calculate when button is clicked', async () => {
    const spy = vi.fn(() => HttpResponse.json<Balance[]>([
      { id: 'b1', account_id: 'acc-1', amount: '48500.00', recorded_at: '2026-06-04T23:59:59', source: 'MANUAL', document_id: null },
    ]))
    server.use(http.post('/api/v1/balances/calculate', spy))

    renderWithProviders(<Balances />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Вычислить' }))

    await waitFor(() => expect(spy).toHaveBeenCalled())
  })

  it('shows success message after calculation', async () => {
    renderWithProviders(<Balances />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Вычислить' }))

    await waitFor(() => expect(screen.getByText('Обновлено счетов: 1')).toBeInTheDocument())
  })

  it('disables button while pending', async () => {
    let resolve!: (v: unknown) => void
    server.use(
      http.post('/api/v1/balances/calculate', () =>
        new Promise((res) => { resolve = res }).then(() => HttpResponse.json<Balance[]>([])),
      ),
    )

    renderWithProviders(<Balances />)
    const user = userEvent.setup()
    const btn = screen.getByRole('button', { name: 'Вычислить' })
    await user.click(btn)

    expect(screen.getByRole('button', { name: 'Вычисляю...' })).toBeDisabled()
    resolve(undefined)
  })
})

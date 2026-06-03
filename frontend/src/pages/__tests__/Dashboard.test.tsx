import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Dashboard from '../Dashboard'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Transaction } from '../../types'

describe('Dashboard page', () => {
  it('renders month navigation buttons', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Предыдущий месяц' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).toBeInTheDocument()
  })

  it('displays current month and year in the header', () => {
    renderWithProviders(<Dashboard />)
    const now = new Date()
    const year = now.getFullYear()
    expect(screen.getByText(new RegExp(String(year)))).toBeInTheDocument()
  })

  it('disables next-month button when on current month', () => {
    renderWithProviders(<Dashboard />)
    const nextBtn = screen.getByRole('button', { name: 'Следующий месяц' })
    expect(nextBtn).toBeDisabled()
  })

  it('enables next-month button after navigating to a past month', async () => {
    renderWithProviders(<Dashboard />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Предыдущий месяц' }))
    const nextBtn = screen.getByRole('button', { name: 'Следующий месяц' })
    expect(nextBtn).not.toBeDisabled()
  })

  it('changes displayed month when prev button is clicked', async () => {
    renderWithProviders(<Dashboard />)
    const user = userEvent.setup()
    const headerBefore = screen.getByRole('heading', { level: 1 }).textContent
    await user.click(screen.getByRole('button', { name: 'Предыдущий месяц' }))
    const headerAfter = screen.getByRole('heading', { level: 1 }).textContent
    expect(headerBefore).not.toBe(headerAfter)
  })

  it('shows KPI cards: Расходы за месяц, Счета, Несверено, Конфликты', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Расходы за месяц')).toBeInTheDocument()
      expect(screen.getByText('Счета')).toBeInTheDocument()
      expect(screen.getByText('Несверено')).toBeInTheDocument()
      expect(screen.getByText('Конфликты')).toBeInTheDocument()
    })
  })

  it('shows "Остатки на счетах" section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Остатки на счетах')).toBeInTheDocument())
  })

  it('shows "Типы расходов" section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Типы расходов')).toBeInTheDocument())
  })

  it('shows expense type row in "Типы расходов" table', async () => {
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          {
            id: 'tx-food',
            account_id: 'acc-1',
            occurred_at: new Date().toISOString(),
            processed_at: null,
            amount: '-500.00',
            type: 'EXPENSE',
            bank_category: null,
            expense_type_id: 'food',
            description: null,
            balance_after: null,
            calculated_balance_after: null,
            balance_mismatch: false,
            receipt_id: null,
            reconciled_status: 'UNMATCHED',
            import_status: 'IMPORTED',
            document_id: null,
          },
        ]),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
  })

  it('renders expense types section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Типы расходов')).toBeInTheDocument())
    expect(screen.getByText('Типы расходов')).toBeInTheDocument()
  })

  it('shows active accounts count', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('1 активных')).toBeInTheDocument())
  })

  it('aggregates expense amounts by type', async () => {
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          {
            id: 'tx-1',
            account_id: 'acc-1',
            occurred_at: new Date().toISOString(),
            processed_at: null,
            amount: '-300.00',
            type: 'EXPENSE',
            bank_category: null,
            expense_type_id: 'food',
            description: null,
            balance_after: null,
            calculated_balance_after: null,
            balance_mismatch: false,
            receipt_id: null,
            reconciled_status: 'UNMATCHED',
            import_status: 'IMPORTED',
            document_id: null,
          },
          {
            id: 'tx-2',
            account_id: 'acc-1',
            occurred_at: new Date().toISOString(),
            processed_at: null,
            amount: '-200.00',
            type: 'EXPENSE',
            bank_category: null,
            expense_type_id: 'food',
            description: null,
            balance_after: null,
            calculated_balance_after: null,
            balance_mismatch: false,
            receipt_id: null,
            reconciled_status: 'UNMATCHED',
            import_status: 'IMPORTED',
            document_id: null,
          },
        ]),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
    // Total should be 500 ₽ (300 + 200)
    expect(screen.getByText(/500,00\s*₽/)).toBeInTheDocument()
  })
})

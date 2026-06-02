import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Dashboard from '../Dashboard'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Transaction, Balance, ExpenseType } from '../../types'
import { currentYearMonth } from '../../utils/date'

// Helpers to build predictable test data
function txInCurrentMonth(overrides: Partial<Transaction> = {}): Transaction {
  const ym = currentYearMonth()
  return {
    id: 'tx-dash-1',
    account_id: 'acc-1',
    occurred_at: `${ym}-01T10:00:00Z`,
    processed_at: null,
    amount: '-2000.00',
    type: 'EXPENSE',
    bank_category: null,
    counterparty_id: null,
    expense_type_id: 'food',
    description: null,
    balance_after: null,
    calculated_balance_after: null,
    balance_mismatch: false,
    receipt_id: null,
    reconciled_status: 'UNMATCHED',
    import_status: 'IMPORTED',
    ...overrides,
  }
}

describe('Dashboard page', () => {
  it('shows "Дашборд" heading', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Дашборд')).toBeInTheDocument()
  })

  it('shows current month label in header', async () => {
    renderWithProviders(<Dashboard />)
    const ym = currentYearMonth()
    const [year, month] = ym.split('-').map(Number)
    const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
    const label = `${MONTHS[month - 1]} ${year}`
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('shows navigation buttons ← and →', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Предыдущий месяц' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).toBeInTheDocument()
  })

  it('next month button is disabled when on current month', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).toBeDisabled()
  })

  it('prev month button is enabled on current month', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Предыдущий месяц' })).not.toBeDisabled()
  })

  it('navigates to previous month when ← is clicked', async () => {
    renderWithProviders(<Dashboard />)
    const user = userEvent.setup()
    const ym = currentYearMonth()
    const [year, month] = ym.split('-').map(Number)
    const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
    // Compute expected previous month label
    const prevDate = new Date(Date.UTC(year, month - 2, 1))
    const prevLabel = `${MONTHS[prevDate.getUTCMonth()]} ${prevDate.getUTCFullYear()}`

    await user.click(screen.getByRole('button', { name: 'Предыдущий месяц' }))
    expect(screen.getByText(prevLabel)).toBeInTheDocument()
  })

  it('enables next month button after navigating back', async () => {
    renderWithProviders(<Dashboard />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Предыдущий месяц' }))
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).not.toBeDisabled()
  })

  it('shows "Остатки на счетах" section heading', async () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Остатки на счетах')).toBeInTheDocument()
  })

  it('shows "Расходы по типам" section heading', async () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Расходы по типам')).toBeInTheDocument()
  })

  it('shows expense type name in расходы по типам table when transactions have expense_type_id', async () => {
    const ym = currentYearMonth()
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          txInCurrentMonth({ expense_type_id: 'food', amount: '-3000.00' }),
        ]),
      ),
      http.get('/api/v1/expense-types', () =>
        HttpResponse.json<ExpenseType[]>([
          { id: 'food', name: 'Питание', receipt_required: true },
        ]),
      ),
      http.get('/api/v1/balances', () =>
        HttpResponse.json<Balance[]>([
          {
            id: 'bal-curr',
            account_id: 'acc-1',
            amount: '45000.00',
            recorded_at: `${ym}-15T00:00:00Z`,
            source: 'CLOSING',
            document_id: null,
          },
        ]),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
  })

  it('shows "Без категории" for transactions without expense_type_id', async () => {
    const ym = currentYearMonth()
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          txInCurrentMonth({ expense_type_id: null }),
        ]),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Без категории')).toBeInTheDocument())
  })

  it('shows empty message in остатки when no balances in selected month', async () => {
    server.use(
      http.get('/api/v1/balances', () => HttpResponse.json<Balance[]>([])),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() =>
      expect(screen.getByText('Нет данных об остатках за этот месяц')).toBeInTheDocument(),
    )
  })

  it('filters balances to show only those matching selected month', async () => {
    const ym = currentYearMonth()
    server.use(
      http.get('/api/v1/balances', () =>
        HttpResponse.json<Balance[]>([
          {
            id: 'bal-curr',
            account_id: 'acc-1',
            amount: '45000.00',
            recorded_at: `${ym}-01T00:00:00Z`,
            source: 'OPENING',
            document_id: null,
          },
          {
            id: 'bal-old',
            account_id: 'acc-1',
            amount: '10000.00',
            recorded_at: '2024-01-01T00:00:00Z', // different month
            source: 'OPENING',
            document_id: null,
          },
        ]),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText(/45.000,00/)).toBeInTheDocument())
    expect(screen.queryByText(/10.000,00/)).not.toBeInTheDocument()
  })

  it('shows KPI cards', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Расходы за месяц')).toBeInTheDocument()
    expect(screen.getByText('Счета')).toBeInTheDocument()
    expect(screen.getByText('Несверено')).toBeInTheDocument()
    expect(screen.getByText('Конфликты')).toBeInTheDocument()
  })
})

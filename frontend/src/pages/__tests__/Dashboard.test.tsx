import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Dashboard from '../Dashboard'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'

type SummaryResponse = {
  unmatched_count: number
  expenses: { expense_type_id: string; count: number; total: string }[]
  income: { expense_type_id: string; count: number; total: string }[]
  turnover: { expense_type_id: string; count: number; total: string }[]
}

const EMPTY_SUMMARY: SummaryResponse = { unmatched_count: 0, expenses: [], income: [], turnover: [] }

describe('Dashboard page', () => {
  it('renders month navigation buttons', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Предыдущий месяц' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).toBeInTheDocument()
  })

  it('displays current year in the header', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText(new RegExp(String(new Date().getFullYear())))).toBeInTheDocument()
  })

  it('disables next-month button when on current month', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).toBeDisabled()
  })

  it('enables next-month button after navigating to a past month', async () => {
    renderWithProviders(<Dashboard />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Предыдущий месяц' }))
    expect(screen.getByRole('button', { name: 'Следующий месяц' })).not.toBeDisabled()
  })

  it('shows all four KPI cards', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Расходы за месяц')).toBeInTheDocument()
      expect(screen.getByText('Счета')).toBeInTheDocument()
      expect(screen.getByText('Несверено')).toBeInTheDocument()
      expect(screen.getByText('Конфликты')).toBeInTheDocument()
    })
  })

  it('shows active accounts count', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('1 активных')).toBeInTheDocument())
  })

  it('shows "Остатки на счетах" section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Остатки на счетах')).toBeInTheDocument())
  })

  it('shows "Типы расходов" section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Типы расходов')).toBeInTheDocument())
  })

  it('shows "Обороты по типам расходов" section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Обороты по типам расходов')).toBeInTheDocument())
  })
})

describe('Dashboard — "Типы расходов" (EXPENSE only)', () => {
  it('shows expense type rows from summary endpoint', async () => {
    // Default handler returns expenses: [{expense_type_id: 'food'}]; 'food' → 'Питание'
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      // May appear in both "Типы расходов" and "Обороты" tables, so use getAllByText
      expect(screen.getAllByText('Питание').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows expense total with negated sign in KPI (expenses are negative in DB, displayed as positive)', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({
          unmatched_count: 0,
          expenses: [{ expense_type_id: 'food', count: 1, total: '-300.00' }],
          income: [],
          turnover: [],
        }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      // KPI "Расходы за месяц" value is the sibling of the label div
      const kpiValueEl = screen.getByText('Расходы за месяц').nextElementSibling
      // Backend stores expenses as negative; dashboard negates for display → 300, not -300
      expect(kpiValueEl?.textContent).toMatch(/300/)
      expect(kpiValueEl?.textContent).not.toMatch(/-300/)
    })
  })

  it('shows correct total in "Расходы за месяц" KPI', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({
          unmatched_count: 0,
          expenses: [{ expense_type_id: 'food', count: 2, total: '-500.00' }],
          income: [],
          turnover: [{ expense_type_id: 'food', count: 2, total: '-500.00' }],
        }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      const kpiValueEl = screen.getByText('Расходы за месяц').nextElementSibling
      expect(kpiValueEl?.textContent).toMatch(/500/)
    })
  })

  it('shows "Нет расходов за период" when expenses list is empty', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>(EMPTY_SUMMARY),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Нет расходов за период')).toBeInTheDocument())
  })

  it('does not show expense rows when summary returns only income', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({
          unmatched_count: 0,
          expenses: [],
          income: [{ expense_type_id: 'food', count: 1, total: '1000.00' }],
          turnover: [{ expense_type_id: 'food', count: 1, total: '1000.00' }],
        }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Нет расходов за период')).toBeInTheDocument())
  })
})

describe('Dashboard — "Обороты по типам расходов"', () => {
  it('shows turnover rows from summary endpoint', async () => {
    // Default handler returns turnover with 'food' → 'Питание'
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getAllByText('Питание').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows "Нет операций за период" when turnover list is empty', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>(EMPTY_SUMMARY),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('Нет операций за период')).toBeInTheDocument())
  })

  it('shows turnover total aggregating all transaction types', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({
          unmatched_count: 0,
          expenses: [],
          income: [],
          turnover: [{ expense_type_id: 'food', count: 3, total: '700.00' }],
        }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getAllByText(/700,00\s*₽/).length).toBeGreaterThanOrEqual(1)
    })
  })
})

describe('Dashboard — unmatched count KPI', () => {
  it('shows unmatched_count from summary in "Несверено" KPI', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({ ...EMPTY_SUMMARY, unmatched_count: 5 }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      // KpiCard: label text is in a child div; value is in its nextElementSibling
      const valueEl = screen.getByText('Несверено').nextElementSibling
      expect(valueEl?.textContent).toBe('5')
    })
  })

  it('highlights "Несверено" card when count is nonzero', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({ ...EMPTY_SUMMARY, unmatched_count: 3 }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      // KpiCard outer div is the parentElement of the label div
      const card = screen.getByText('Несверено').parentElement
      expect(card?.className).toMatch(/yellow/)
    })
  })

  it('"Несверено" card has no warning class when count is zero', async () => {
    server.use(
      http.get('/api/v1/transactions/expense-type-summary', () =>
        HttpResponse.json<SummaryResponse>({ ...EMPTY_SUMMARY, unmatched_count: 0 }),
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      const valueEl = screen.getByText('Несверено').nextElementSibling
      expect(valueEl?.textContent).toBe('0')
    })
    const card = screen.getByText('Несверено').parentElement
    expect(card?.className).not.toMatch(/yellow/)
  })
})

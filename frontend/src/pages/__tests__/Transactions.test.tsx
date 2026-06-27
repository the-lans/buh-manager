import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Transactions from '../Transactions'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Transaction } from '../../types'

// The ru-locale formats -1500 as "-1 500,00" (non-breaking space, hyphen-minus).
// Use a regex to avoid locale/environment differences.
const TX_AMOUNT = /1\s*500,00\s*₽/

const TX_FIXTURE: Transaction = {
  id: 'tx-with-desc',
  account_id: 'acc-1',
  occurred_at: '2026-04-01T10:00:00',
  processed_at: null,
  amount: '-2750.00',
  type: 'EXPENSE',
  bank_category: 'Супермаркеты',
  expense_type_id: 'food',
  description: 'Покупка продуктов',
  balance_after: null,
  calculated_balance_after: null,
  balance_mismatch: false,
  receipt_id: null,
  reconciled_status: 'UNMATCHED',
  import_status: 'IMPORTED',
  document_id: null,
}

describe('Transactions page', () => {
  it('renders transaction list', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByText(TX_AMOUNT)).toBeInTheDocument())
  })

  it('shows Чек and Документ column headers', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByText(TX_AMOUNT)).toBeInTheDocument())
    const headers = screen.getAllByRole('columnheader')
    const headerTexts = headers.map((h) => h.textContent)
    expect(headerTexts).toContain('Чек')
    expect(headerTexts).toContain('Документ')
  })

  it('shows "—" in Чек column when receipt_id is null', async () => {
    renderWithProviders(<Transactions />)
    // default fixture has receipt_id: null and document_id: null
    await waitFor(() => expect(screen.getByText(TX_AMOUNT)).toBeInTheDocument())
    // Both Чек and Документ columns should show "—"
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })

  it('shows "✓" in Чек column when receipt_id is set', async () => {
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          {
            id: 'tx-with-receipt',
            account_id: 'acc-1',
            occurred_at: '2026-04-01T10:00:00',
            processed_at: null,
            amount: '-500.00',
            type: 'EXPENSE',
            bank_category: null,
            expense_type_id: 'et-1',
            description: null,
            balance_after: null,
            calculated_balance_after: null,
            balance_mismatch: false,
            receipt_id: 'rec-1',
            reconciled_status: 'MATCHED',
            import_status: 'IMPORTED',
            document_id: 'doc-1',
          },
        ]),
      ),
    )
    renderWithProviders(<Transactions />)
    await waitFor(() => {
      const checks = screen.getAllByText('✓')
      expect(checks.length).toBe(2) // both receipt and document have ✓
    })
  })

  it('shows Изменить and Удалить buttons for each transaction', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument()
  })

  it('shows inline confirmation when Удалить is clicked', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Удалить?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Да' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Нет' })).toBeInTheDocument()
  })

  it('cancels deletion when "Нет" is clicked', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Нет' }))
    expect(screen.queryByText('Удалить?')).not.toBeInTheDocument()
  })

  it('calls delete API when "Да" is confirmed', async () => {
    const deleteSpy = vi.fn(() => new HttpResponse(null, { status: 204 }))
    server.use(http.delete('/api/v1/transactions/:id', deleteSpy))

    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))

    await waitFor(() => expect(deleteSpy).toHaveBeenCalled())
  })

  it('opens TransactionEditModal when Изменить is clicked', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить транзакцию')).toBeInTheDocument())
  })

  it('shows "+ Добавить" button', () => {
    renderWithProviders(<Transactions />)
    expect(screen.getByRole('button', { name: '+ Добавить' })).toBeInTheDocument()
  })

  it('shows filter dropdowns', () => {
    renderWithProviders(<Transactions />)
    const selects = screen.getAllByRole('combobox')
    expect(selects.length).toBeGreaterThanOrEqual(4) // type, status, account, expense_type
  })

  it('shows "Все виды расхода" option in expense type filter', () => {
    renderWithProviders(<Transactions />)
    expect(screen.getByRole('option', { name: 'Все виды расхода' })).toBeInTheDocument()
  })

  it('lists expense types in the expense type filter', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => {
      // 'Питание' comes from the mock expense-types handler (id: 'food')
      const options = screen.getAllByRole('option', { name: 'Питание' })
      expect(options.length).toBeGreaterThan(0)
    })
  })

  it('sends expense_type_id param when expense type filter changes', async () => {
    let capturedUrl: string | undefined
    server.use(
      http.get('/api/v1/transactions', ({ request }) => {
        capturedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()

    // Find the expense-type select by its unique "Все виды расхода" option,
    // and wait until the 'food' option from expense-types API has loaded.
    const expenseTypeSelect = await waitFor(() => {
      const found = screen.getAllByRole('combobox').find((s) =>
        Array.from(s.querySelectorAll('option')).some((o) => o.textContent === 'Все виды расхода'),
      ) as HTMLSelectElement | undefined
      if (!found) throw new Error('expense type select not found')
      const hasFood = Array.from(found.querySelectorAll('option')).some(
        (o) => (o as HTMLOptionElement).value === 'food',
      )
      if (!hasFood) throw new Error('food option not yet loaded')
      return found
    })

    await user.selectOptions(expenseTypeSelect, 'food')

    await waitFor(() => expect(capturedUrl).toContain('expense_type_id=food'))
  })

  it('clears expense_type_id param when "Все виды расхода" is selected', async () => {
    let capturedUrl: string | undefined
    server.use(
      http.get('/api/v1/transactions', ({ request }) => {
        capturedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()

    const expenseTypeSelect = await waitFor(() => {
      const found = screen.getAllByRole('combobox').find((s) =>
        Array.from(s.querySelectorAll('option')).some((o) => o.textContent === 'Все виды расхода'),
      ) as HTMLSelectElement | undefined
      if (!found) throw new Error('expense type select not found')
      const hasFood = Array.from(found.querySelectorAll('option')).some(
        (o) => (o as HTMLOptionElement).value === 'food',
      )
      if (!hasFood) throw new Error('food option not yet loaded')
      return found
    })

    await user.selectOptions(expenseTypeSelect, 'food')
    await user.selectOptions(expenseTypeSelect, '')

    await waitFor(() => expect(capturedUrl).not.toContain('expense_type_id'))
  })

  it('shows expense type select in new transaction form', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ Добавить' }))
    await waitFor(() => expect(screen.getByText('Новая транзакция')).toBeInTheDocument())
    expect(screen.getByRole('option', { name: '— Вид расхода —' })).toBeInTheDocument()
  })

  it('lists expense types in new transaction form', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ Добавить' }))
    await waitFor(() => expect(screen.getByText('Новая транзакция')).toBeInTheDocument())
    // "Питание" is the expense type from mock handlers
    await waitFor(() => {
      const options = screen.getAllByRole('option', { name: 'Питание' })
      expect(options.length).toBeGreaterThan(0)
    })
  })

  it('does not show expense type name in table row when expense_type_id is null', async () => {
    server.use(
      http.get('/api/v1/transactions', () =>
        HttpResponse.json<Transaction[]>([
          {
            id: 'tx-null-type',
            account_id: 'acc-1',
            occurred_at: '2026-04-01T10:00:00',
            processed_at: null,
            amount: '-500.00',
            type: 'EXPENSE',
            bank_category: null,
            expense_type_id: null,
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
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByText(/500,00\s*₽/)).toBeInTheDocument())
    // 'Питание' may appear in the filter dropdown options but NOT in transaction table rows
    const dataRows = screen.getAllByRole('row').filter((r) => r.querySelectorAll('td').length > 0)
    expect(dataRows.every((r) => !r.textContent?.includes('Питание'))).toBe(true)
  })

  it('opens edit modal with pre-filled amount when Изменить is clicked', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить транзакцию')).toBeInTheDocument())
    // The transaction has amount -1500.00 — it should be pre-filled
    expect(screen.getByDisplayValue('-1500.00')).toBeInTheDocument()
  })

  it('shows description, bank_category, expense type and type in the list', async () => {
    server.use(
      http.get('/api/v1/transactions', () => HttpResponse.json<Transaction[]>([TX_FIXTURE])),
    )
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByText('Покупка продуктов')).toBeInTheDocument())
    expect(screen.getByText('Супермаркеты')).toBeInTheDocument()
    // 'Питание' appears in both the table row and the expense-type filter dropdown
    await waitFor(() => expect(screen.getAllByText('Питание').length).toBeGreaterThanOrEqual(1))
    expect(screen.getByText(/2\s*750,00\s*₽/)).toBeInTheDocument()
    expect(screen.getByText('EXPENSE')).toBeInTheDocument()
  })

  it('opens edit modal with pre-filled description, amount and bank_category when Изменить is clicked', async () => {
    server.use(
      http.get('/api/v1/transactions', () => HttpResponse.json<Transaction[]>([TX_FIXTURE])),
    )
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить транзакцию')).toBeInTheDocument())
    expect(screen.getByDisplayValue('Покупка продуктов')).toBeInTheDocument()
    expect(screen.getByDisplayValue('-2750.00')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Супермаркеты')).toBeInTheDocument()
  })

  it('shows pagination buttons', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Назад/ })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Вперёд/ })).toBeInTheDocument()
  })

  it('back button is disabled on first page', async () => {
    renderWithProviders(<Transactions />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Назад/ })).toBeDisabled())
  })

  it('forward button is disabled when fewer items than page size', async () => {
    renderWithProviders(<Transactions />)
    // Default fixture has 1 transaction, which is less than PAGE_SIZE=20
    await waitFor(() => expect(screen.getByText(TX_AMOUNT)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Вперёд/ })).toBeDisabled()
  })

  it('shows "Применить правила" checkbox in create form unchecked by default', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ Добавить' }))
    await waitFor(() => expect(screen.getByText('Новая транзакция')).toBeInTheDocument())
    const checkbox = screen.getByRole('checkbox', { name: /Применить правила/ })
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).not.toBeChecked()
  })

  it('"Применить правила" checkbox toggles state correctly in create form', async () => {
    renderWithProviders(<Transactions />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ Добавить' }))
    await waitFor(() => expect(screen.getByText('Новая транзакция')).toBeInTheDocument())

    const checkbox = screen.getByRole('checkbox', { name: /Применить правила/ })
    expect(checkbox).not.toBeChecked()
    await user.click(checkbox)
    expect(checkbox).toBeChecked()
    await user.click(checkbox)
    expect(checkbox).not.toBeChecked()
  })
})

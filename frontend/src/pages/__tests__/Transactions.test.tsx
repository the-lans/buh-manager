import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Transactions from '../Transactions'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Transaction } from '../../types'

// The ru-locale formats -1500 as "-1 500,00" (non-breaking space, hyphen-minus).
// Use a regex to avoid locale/environment differences.
const TX_AMOUNT = /1\s*500,00\s*₽/

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
            counterparty_id: null,
            expense_type_id: null,
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
    expect(selects.length).toBeGreaterThanOrEqual(3) // type, status, account
  })
})

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import TransactionEditModal from '../TransactionEditModal'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Transaction } from '../../types'

const BASE_TX: Transaction = {
  id: 'tx-edit-1',
  account_id: 'acc-1',
  occurred_at: '2026-04-01T10:00:00Z',
  processed_at: null,
  amount: '-1500.00',
  type: 'EXPENSE',
  bank_category: 'Продукты',
  expense_type_id: 'et-1',
  description: 'Покупка продуктов',
  balance_after: '50000.00',
  calculated_balance_after: null,
  balance_mismatch: false,
  receipt_id: null,
  reconciled_status: 'UNMATCHED',
  import_status: 'IMPORTED',
  document_id: null,
}

describe('TransactionEditModal', () => {
  it('renders nothing when transaction is null', () => {
    renderWithProviders(<TransactionEditModal transaction={null} onClose={() => {}} />)
    expect(screen.queryByText('Изменить транзакцию')).not.toBeInTheDocument()
  })

  it('renders modal with transaction data', async () => {
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={() => {}} />)
    expect(screen.getByText('Изменить транзакцию')).toBeInTheDocument()
    expect(screen.getByDisplayValue('-1500.00')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Покупка продуктов')).toBeInTheDocument()
  })

  it('shows account label in readonly section', async () => {
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={() => {}} />)
    await waitFor(() =>
      // Account "Сбербанк ···0810" from mock handler acc-1: bank=Сбербанк, account_number=40817810
      expect(screen.getByText(/Сбербанк/)).toBeInTheDocument(),
    )
  })

  it('calls onClose when cancel is clicked', async () => {
    const onClose = vi.fn()
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={onClose} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Отмена' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when ✕ is clicked', async () => {
    const onClose = vi.fn()
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={onClose} />)
    const user = userEvent.setup()
    await user.click(screen.getByText('✕'))
    expect(onClose).toHaveBeenCalled()
  })

  it('submits updated amount and calls onClose on success', async () => {
    const onClose = vi.fn()
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={onClose} />)
    const user = userEvent.setup()

    const amountInput = screen.getByDisplayValue('-1500.00')
    await user.clear(amountInput)
    await user.type(amountInput, '-2000')

    await user.click(screen.getByRole('button', { name: 'Сохранить' }))

    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('shows error message when save fails', async () => {
    server.use(
      http.put('/api/v1/transactions/:id', () =>
        HttpResponse.json({ detail: 'Transaction not found.' }, { status: 404 }),
      ),
    )
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={() => {}} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Сохранить' }))
    await waitFor(() =>
      expect(screen.getByText('Transaction not found.')).toBeInTheDocument(),
    )
  })

  it('shows all reconciled_status options', async () => {
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={() => {}} />)
    const statusSelect = screen.getByDisplayValue('Не сверено')
    expect(statusSelect).toBeInTheDocument()
    // Check all options exist in the select
    const options = Array.from(statusSelect.querySelectorAll('option')).map((o) => o.textContent)
    expect(options).toContain('Не сверено')
    expect(options).toContain('Сверено')
    expect(options).toContain('Не требуется')
    expect(options).toContain('Игнорируется')
  })

  it('shows expense types in selector', async () => {
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
  })

  it('includes reconciled_status in the save payload', async () => {
    const updateSpy = vi.fn((info) =>
      info.request.json().then((body: Record<string, unknown>) => {
        expect(body.reconciled_status).toBe('IGNORED_BY_USER')
        return HttpResponse.json({
          ...BASE_TX,
          reconciled_status: 'IGNORED_BY_USER',
        })
      }),
    )
    server.use(http.put('/api/v1/transactions/:id', updateSpy))

    const onClose = vi.fn()
    renderWithProviders(<TransactionEditModal transaction={BASE_TX} onClose={onClose} />)
    const user = userEvent.setup()

    // Change reconciled_status to IGNORED_BY_USER
    const statusSelect = screen.getByDisplayValue('Не сверено')
    await user.selectOptions(statusSelect, 'IGNORED_BY_USER')

    await user.click(screen.getByRole('button', { name: 'Сохранить' }))

    await waitFor(() => expect(updateSpy).toHaveBeenCalled())
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Receipts from '../Receipts'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { ReceiptListItem } from '../../types'

describe('Receipts page', () => {
  it('renders receipt list', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByText('500,00 ₽')).toBeInTheDocument())
  })

  it('shows document indicator column header', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByText('Документ')).toBeInTheDocument())
  })

  it('has centered "Документ" column header', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByText('Документ')).toBeInTheDocument())
    const docHeader = screen.getByRole('columnheader', { name: 'Документ' })
    expect(docHeader.className).toContain('text-center')
  })

  it('shows "—" indicator when receipt has no document', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByText('500,00 ₽')).toBeInTheDocument())
    // Default fixture has document_id: null → shows "—"
    const cells = screen.getAllByText('—')
    expect(cells.length).toBeGreaterThan(0)
  })

  it('shows "✓" indicator when receipt has a document', async () => {
    server.use(
      http.get('/api/v1/receipts', () =>
        HttpResponse.json<ReceiptListItem[]>([
          {
            id: 'rec-with-doc',
            paid_at: '2026-04-01T10:00:00',
            total_amount: '250.00',
            counterparty_id: null,
            document_id: 'doc-1',
            transaction_id: null,
          },
        ]),
      ),
    )
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByText('250,00 ₽')).toBeInTheDocument())
    expect(screen.getByText('✓')).toBeInTheDocument()
  })

  it('shows inline confirmation when delete is clicked', async () => {
    renderWithProviders(<Receipts />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Удалить?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Да' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Нет' })).toBeInTheDocument()
  })

  it('cancels deletion when "Нет" is clicked', async () => {
    renderWithProviders(<Receipts />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Удалить?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Нет' }))
    expect(screen.queryByText('Удалить?')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument()
  })

  it('calls delete API when "Да" is confirmed', async () => {
    const deleteSpy = vi.fn(() => new HttpResponse(null, { status: 204 }))
    server.use(http.delete('/api/v1/receipts/:id', deleteSpy))

    renderWithProviders(<Receipts />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))

    await waitFor(() => expect(deleteSpy).toHaveBeenCalled())
  })

  it('opens ReceiptDetailModal on row click', async () => {
    server.use(
      http.get('/api/v1/receipts/:id', () =>
        HttpResponse.json({
          id: 'rec-1',
          document_id: null,
          paid_at: '2026-04-01T10:00:00',
          total_amount: '500.00',
          counterparty_id: null,
          fn: null,
          fd: null,
          fpd: null,
          items: [],
        }),
      ),
    )
    renderWithProviders(<Receipts />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('500,00 ₽')).toBeInTheDocument())
    await user.click(screen.getByText('500,00 ₽'))
    await waitFor(() => expect(screen.getByText('Детали чека')).toBeInTheDocument())
  })

  it('shows pagination buttons', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Назад/ })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Вперёд/ })).toBeInTheDocument()
  })

  it('back button is disabled on first page', async () => {
    renderWithProviders(<Receipts />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Назад/ })).toBeDisabled())
  })
})

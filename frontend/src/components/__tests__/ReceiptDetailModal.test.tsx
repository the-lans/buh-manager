import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import ReceiptDetailModal from '../ReceiptDetailModal'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'

const RECEIPT_WITH_ITEMS = {
  id: 'rec-detail',
  document_id: null,
  paid_at: '2026-04-10T12:00:00',
  total_amount: '750.50',
  counterparty_id: null,
  fn: '1234567890',
  fd: '123456',
  fpd: '987654',
  items: [
    {
      id: 'item-1',
      receipt_id: 'rec-detail',
      code: '001',
      name: 'Молоко',
      unit: 'л',
      quantity: '2.0000',
      price: '75.00',
      amount: '150.00',
      tags: null,
    },
    {
      id: 'item-2',
      receipt_id: 'rec-detail',
      code: null,
      name: 'Хлеб',
      unit: null,
      quantity: '1.0000',
      price: '45.50',
      amount: '45.50',
      tags: null,
    },
  ],
}

function setupReceiptHandler() {
  server.use(
    http.get('/api/v1/receipts/:id', () => HttpResponse.json(RECEIPT_WITH_ITEMS)),
  )
}

describe('ReceiptDetailModal', () => {
  it('renders nothing when receiptId is null', () => {
    renderWithProviders(<ReceiptDetailModal receiptId={null} onClose={() => {}} />)
    expect(screen.queryByText('Детали чека')).not.toBeInTheDocument()
  })

  it('shows receipt details modal title', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Детали чека')).toBeInTheDocument())
  })

  it('shows item names in the table', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Молоко')).toBeInTheDocument())
    expect(screen.getByText('Хлеб')).toBeInTheDocument()
  })

  it('shows total amount', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText(/750/)).toBeInTheDocument())
  })

  it('shows "—" for unit when unit is null', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Хлеб')).toBeInTheDocument())
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThan(0)
  })

  it('has centered "Кол-во" column header', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Молоко')).toBeInTheDocument())
    const qtyHeader = screen.getByRole('columnheader', { name: 'Кол-во' })
    expect(qtyHeader.className).toContain('text-center')
  })

  it('has centered "Ед. изм." column header', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Молоко')).toBeInTheDocument())
    const unitHeader = screen.getByRole('columnheader', { name: 'Ед. изм.' })
    expect(unitHeader.className).toContain('text-center')
  })

  it('quantity cells have centered alignment', async () => {
    setupReceiptHandler()
    renderWithProviders(<ReceiptDetailModal receiptId="rec-detail" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('Молоко')).toBeInTheDocument())
    // Find quantity cells by their content pattern (numeric)
    const rows = screen.getAllByRole('row')
    // Find data rows (skip header row)
    const firstDataRow = rows[1]
    const cells = firstDataRow.querySelectorAll('td')
    const qtyCell = cells[1] // Кол-во is second column
    expect(qtyCell.className).toContain('text-center')
  })
})

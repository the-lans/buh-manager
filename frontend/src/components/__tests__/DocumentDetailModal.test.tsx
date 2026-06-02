import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import DocumentDetailModal from '../DocumentDetailModal'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Document, ReceiptListItem } from '../../types'

describe('DocumentDetailModal', () => {
  it('renders nothing when documentId is null', () => {
    renderWithProviders(<DocumentDetailModal documentId={null} onClose={() => {}} />)
    expect(screen.queryByText('Карточка документа')).not.toBeInTheDocument()
  })

  it('shows document fields after loading', async () => {
    renderWithProviders(<DocumentDetailModal documentId="doc-1" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    expect(screen.getByText('Чек')).toBeInTheDocument()
    expect(screen.getByText('Обработан')).toBeInTheDocument()
  })

  it('shows URL field in document card', async () => {
    renderWithProviders(<DocumentDetailModal documentId="doc-1" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    expect(screen.getByText('URL')).toBeInTheDocument()
    expect(screen.getByText('/media/fake/doc-1')).toBeInTheDocument()
  })

  it('shows email_source when present', async () => {
    server.use(
      http.get('/api/v1/documents/:id', () =>
        HttpResponse.json<Document>({
          id: 'doc-email',
          user_id: 'user-1',
          type: 'RECEIPT',
          url: '/media/doc-email',
          name: 'email-doc.pdf',
          status: 'PENDING',
          email_source: 'noreply@shop.ru',
          file_hash: 'hashemail',
          uploaded_at: '2026-04-01T10:00:00',
          payload: null,
        }),
      ),
    )
    renderWithProviders(<DocumentDetailModal documentId="doc-email" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('email-doc.pdf')).toBeInTheDocument())
    expect(screen.getByText('noreply@shop.ru')).toBeInTheDocument()
  })

  it('shows payload when document has payload data', async () => {
    const payload = { магазин: 'Пятёрочка', адрес: 'ул. Ленина 1' }
    server.use(
      http.get('/api/v1/documents/:id', () =>
        HttpResponse.json<Document>({
          id: 'doc-payload',
          user_id: 'user-1',
          type: 'RECEIPT',
          url: '/media/doc-payload',
          name: 'payload-doc.pdf',
          status: 'PROCESSED',
          email_source: null,
          file_hash: 'hashpayload',
          uploaded_at: '2026-04-01T10:00:00',
          payload,
        }),
      ),
    )
    renderWithProviders(<DocumentDetailModal documentId="doc-payload" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('payload-doc.pdf')).toBeInTheDocument())
    expect(screen.getByText('Дополнительные сведения')).toBeInTheDocument()
    expect(screen.getByText(/Пятёрочка/)).toBeInTheDocument()
  })

  it('does not show payload section when payload is null', async () => {
    renderWithProviders(<DocumentDetailModal documentId="doc-1" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    expect(screen.queryByText('Дополнительные сведения')).not.toBeInTheDocument()
  })

  it('shows linked receipt for RECEIPT type document', async () => {
    server.use(
      http.get('/api/v1/receipts', () =>
        HttpResponse.json<ReceiptListItem[]>([
          {
            id: 'rec-linked',
            paid_at: '2026-04-10T12:00:00',
            total_amount: '750.00',
            counterparty_id: 'cp-1',
            document_id: 'doc-1',
          },
        ]),
      ),
    )
    renderWithProviders(<DocumentDetailModal documentId="doc-1" onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByText('Привязанный чек')).toBeInTheDocument())
    expect(screen.getByText(/750/)).toBeInTheDocument()
  })

  it('calls onClose when backdrop clicked', async () => {
    const onClose = vi.fn()
    renderWithProviders(<DocumentDetailModal documentId="doc-1" onClose={onClose} />)
    await waitFor(() => expect(screen.getByText('Карточка документа')).toBeInTheDocument())
    const user = userEvent.setup()
    // Click backdrop (the fixed overlay behind the modal)
    await user.click(screen.getByText('✕'))
    expect(onClose).toHaveBeenCalled()
  })

  it('shows loading state initially', () => {
    server.use(http.get('/api/v1/documents/:id', () => new Promise(() => {})))
    renderWithProviders(<DocumentDetailModal documentId="doc-slow" onClose={() => {}} />)
    expect(screen.getByText('Загрузка...')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    server.use(http.get('/api/v1/documents/:id', () => HttpResponse.error()))
    renderWithProviders(<DocumentDetailModal documentId="doc-fail" onClose={() => {}} />)
    await waitFor(() =>
      expect(screen.getByText('Не удалось загрузить документ.')).toBeInTheDocument(),
    )
  })
})

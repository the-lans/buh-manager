import { describe, it, expect, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Documents from '../Documents'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Document } from '../../types'

describe('Documents page', () => {
  it('renders filter dropdowns and upload button', async () => {
    renderWithProviders(<Documents />)
    expect(screen.getByText('Загрузить')).toBeInTheDocument()
    expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(2) // type + status selects
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
  })

  it('shows documents from API', async () => {
    renderWithProviders(<Documents />)
    await waitFor(() => {
      expect(screen.getByText('receipt.pdf')).toBeInTheDocument()
      expect(screen.getByText('statement.pdf')).toBeInTheDocument()
    })
  })

  it('shows "Обработать" button only for PENDING documents', async () => {
    renderWithProviders(<Documents />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    // receipt.pdf is PENDING → should have "Обработать"
    // statement.pdf is PROCESSED → should NOT have "Обработать"
    const processButtons = screen.getAllByText('Обработать')
    expect(processButtons).toHaveLength(1)
  })

  it('opens upload modal on "Загрузить" button click', async () => {
    renderWithProviders(<Documents />)
    const user = userEvent.setup()
    await user.click(screen.getByText('Загрузить'))
    expect(screen.getByText('Загрузить документ')).toBeInTheDocument()
  })

  it('shows duplicate error message on 409 upload response', async () => {
    server.use(
      http.post('/api/v1/documents', () =>
        HttpResponse.json(
          { message: 'Document already exists.', document_id: 'doc-existing' },
          { status: 409 },
        ),
      ),
    )
    renderWithProviders(<Documents />)
    const user = userEvent.setup()
    await user.click(screen.getByText('Загрузить'))

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    await user.upload(fileInput, file)

    // Find the submit button inside the modal (the one with text "Загрузить" that is not disabled)
    const allButtons = screen.getAllByRole('button', { name: /^Загрузить/ })
    const submitButton = allButtons[allButtons.length - 1]
    await user.click(submitButton)

    await waitFor(() =>
      expect(screen.getByText('Такой документ уже существует в системе.')).toBeInTheDocument(),
    )
  })

  it('opens RECEIPT process modal with receipt selector', async () => {
    renderWithProviders(<Documents />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    const user = userEvent.setup()
    await user.click(screen.getByText('Обработать'))
    await waitFor(() =>
      expect(screen.getByText('Обработать документ: receipt.pdf')).toBeInTheDocument(),
    )
    expect(screen.getByText('Выберите чек')).toBeInTheDocument()
  })

  it('shows "Сбросить" button only for ERROR documents', async () => {
    server.use(
      http.get('/api/v1/documents', () =>
        HttpResponse.json<Document[]>([
          {
            id: 'doc-err',
            user_id: 'user-1',
            type: 'BANK_STATEMENT',
            url: '/',
            name: 'err.pdf',
            status: 'ERROR',
            uploaded_at: '2026-04-01T10:00:00',
          },
          {
            id: 'doc-ok',
            user_id: 'user-1',
            type: 'BANK_STATEMENT',
            url: '/',
            name: 'ok.pdf',
            status: 'PROCESSED',
            uploaded_at: '2026-03-01T10:00:00',
          },
        ]),
      ),
    )
    renderWithProviders(<Documents />)
    await waitFor(() => expect(screen.getByText('err.pdf')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Сбросить' })).toBeInTheDocument()
    expect(screen.queryByText('Обработать')).not.toBeInTheDocument()
  })

  it('backward pagination button is disabled on first page', async () => {
    renderWithProviders(<Documents />)
    await waitFor(() => expect(screen.getByText('receipt.pdf')).toBeInTheDocument())
    const backBtn = screen.getByRole('button', { name: /Назад/ })
    expect(backBtn).toBeDisabled()
  })

  it('forward pagination button is disabled when fewer items than page size returned', async () => {
    server.use(
      http.get('/api/v1/documents', () =>
        HttpResponse.json<Document[]>([
          {
            id: 'doc-only',
            user_id: 'user-1',
            type: 'RECEIPT',
            url: '/media/fake/doc-only',
            name: 'only.pdf',
            status: 'PENDING',
            uploaded_at: '2026-04-01T10:00:00',
          },
        ]),
      ),
    )
    renderWithProviders(<Documents />)
    await waitFor(() => expect(screen.getByText('only.pdf')).toBeInTheDocument())
    const nextBtn = screen.getByRole('button', { name: /Вперёд/ })
    expect(nextBtn).toBeDisabled()
  })

  it('applies type filter when dropdown changes', async () => {
    let receivedUrl: string | undefined
    server.use(
      http.get('/api/v1/documents', ({ request }) => {
        receivedUrl = request.url
        return HttpResponse.json([])
      }),
    )
    renderWithProviders(<Documents />)
    await waitFor(() => expect(receivedUrl).toBeDefined())

    const user = userEvent.setup()
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'RECEIPT')

    await waitFor(() => expect(receivedUrl).toContain('type=RECEIPT'))
  })
})

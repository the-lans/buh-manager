import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Counterparties from '../Counterparties'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'

describe('Counterparties page', () => {
  it('renders counterparty list', async () => {
    renderWithProviders(<Counterparties />)
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
  })

  it('shows no error message initially', async () => {
    renderWithProviders(<Counterparties />)
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    expect(screen.queryByText(/не может быть удалён/)).not.toBeInTheDocument()
  })

  // ── Confirmation dialog ──────────────────────────────────────────────────────

  it('shows confirmation dialog when delete button is clicked', async () => {
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Удалить?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Да' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Нет' })).toBeInTheDocument()
  })

  it('hides confirmation dialog when "Нет" is clicked', async () => {
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Нет' }))
    expect(screen.queryByText('Удалить?')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument()
  })

  it('calls delete API when "Да" is confirmed', async () => {
    const deleteSpy = vi.fn(() => new HttpResponse(null, { status: 204 }))
    server.use(http.delete('/api/v1/counterparties/:id', deleteSpy))
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))
    await waitFor(() => expect(deleteSpy).toHaveBeenCalled())
  })

  it('does NOT call delete API when only "Удалить" is clicked (before confirmation)', async () => {
    const deleteSpy = vi.fn(() => new HttpResponse(null, { status: 204 }))
    server.use(http.delete('/api/v1/counterparties/:id', deleteSpy))
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(deleteSpy).not.toHaveBeenCalled()
  })

  // ── Error handling after confirmation ────────────────────────────────────────

  it('shows error message when delete returns 409 (used in receipts)', async () => {
    server.use(
      http.delete('/api/v1/counterparties/:id', () =>
        HttpResponse.json(
          { detail: 'Контрагент используется в чеках и не может быть удалён.' },
          { status: 409 },
        ),
      ),
    )
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))
    await waitFor(() =>
      expect(screen.getByText('Контрагент используется в чеках и не может быть удалён.')).toBeInTheDocument(),
    )
  })

  it('shows error message when delete returns 409 (used in transactions)', async () => {
    server.use(
      http.delete('/api/v1/counterparties/:id', () =>
        HttpResponse.json(
          { detail: 'Контрагент используется в транзакциях и не может быть удалён.' },
          { status: 409 },
        ),
      ),
    )
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))
    await waitFor(() =>
      expect(
        screen.getByText('Контрагент используется в транзакциях и не может быть удалён.'),
      ).toBeInTheDocument(),
    )
  })

  it('shows generic error message on network failure', async () => {
    server.use(http.delete('/api/v1/counterparties/:id', () => HttpResponse.error()))
    renderWithProviders(<Counterparties />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByText('Магазин Тест')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))
    await waitFor(() =>
      expect(screen.getByText('Произошла ошибка')).toBeInTheDocument(),
    )
  })
})

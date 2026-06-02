import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Settings from '../Settings'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { ExpenseType } from '../../types'

describe('Settings — ExpenseTypesTab', () => {
  it('renders existing expense types with name and id', async () => {
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
    expect(screen.getByText('food')).toBeInTheDocument()
  })

  it('shows description when expense type has one', async () => {
    server.use(
      http.get('/api/v1/expense-types', () =>
        HttpResponse.json<ExpenseType[]>([
          { id: 'food', name: 'Питание', description: 'Продукты и еда', receipt_required: true },
        ]),
      ),
    )
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByText('Продукты и еда')).toBeInTheDocument())
  })

  it('does not show description row when description is null', async () => {
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
    // No description in fixture → no description text besides the name
    expect(screen.queryByText('Продукты и еда')).not.toBeInTheDocument()
  })

  it('has a description textarea in the create form', async () => {
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByPlaceholderText('Описание (необязательно)')).toBeInTheDocument())
  })

  it('submits description when creating expense type', async () => {
    let capturedBody: Record<string, unknown> | null = null
    server.use(
      http.post('/api/v1/expense-types', async (info) => {
        capturedBody = (await info.request.json()) as Record<string, unknown>
        return HttpResponse.json(
          { id: 'transport', name: 'Транспорт', description: 'Поездки и такси', receipt_required: true },
          { status: 201 },
        )
      }),
    )
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByPlaceholderText('ID (slug, напр. groceries)')).toBeInTheDocument())

    await user.type(screen.getByPlaceholderText('ID (slug, напр. groceries)'), 'transport')
    await user.type(screen.getByPlaceholderText('Название'), 'Транспорт')
    await user.type(screen.getByPlaceholderText('Описание (необязательно)'), 'Поездки и такси')
    await user.click(screen.getByRole('button', { name: 'Создать' }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    expect(capturedBody!.description).toBe('Поездки и такси')
    expect(capturedBody!.name).toBe('Транспорт')
  })

  it('submits null description when description field is empty', async () => {
    let capturedBody: Record<string, unknown> | null = null
    server.use(
      http.post('/api/v1/expense-types', async (info) => {
        capturedBody = (await info.request.json()) as Record<string, unknown>
        return HttpResponse.json(
          { id: 'other', name: 'Прочее', description: null, receipt_required: true },
          { status: 201 },
        )
      }),
    )
    renderWithProviders(<Settings />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByPlaceholderText('ID (slug, напр. groceries)')).toBeInTheDocument())

    await user.type(screen.getByPlaceholderText('ID (slug, напр. groceries)'), 'other')
    await user.type(screen.getByPlaceholderText('Название'), 'Прочее')
    await user.click(screen.getByRole('button', { name: 'Создать' }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    expect(capturedBody!.description).toBeNull()
  })
})

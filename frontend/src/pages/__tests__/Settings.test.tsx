import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Settings from '../Settings'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { Account, ExpenseType } from '../../types'

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

describe('Settings — ExpenseTypesTab edit modal', () => {
  const goToExpenseTypes = async (user: ReturnType<typeof userEvent.setup>) => {
    renderWithProviders(<Settings />)
    await user.click(screen.getByRole('button', { name: 'Типы расходов' }))
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
  }

  it('opens edit modal when Изменить is clicked', async () => {
    const user = userEvent.setup()
    await goToExpenseTypes(user)
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить тип расходов')).toBeInTheDocument())
    expect(screen.getByDisplayValue('Питание')).toBeInTheDocument()
  })

  it('closes modal when Отмена is clicked', async () => {
    const user = userEvent.setup()
    await goToExpenseTypes(user)
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить тип расходов')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Отмена' }))
    expect(screen.queryByText('Изменить тип расходов')).not.toBeInTheDocument()
  })

  it('calls PUT /expense-types/:id with updated data on save', async () => {
    let captured: Record<string, unknown> | null = null
    server.use(
      http.put('/api/v1/expense-types/:id', async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>
        return HttpResponse.json<ExpenseType>({ id: 'food', name: 'Новое название', description: null, receipt_required: true })
      }),
    )

    const user = userEvent.setup()
    await goToExpenseTypes(user)
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить тип расходов')).toBeInTheDocument())

    const nameInput = screen.getByDisplayValue('Питание')
    await user.clear(nameInput)
    await user.type(nameInput, 'Новое название')
    await user.click(screen.getByRole('button', { name: 'Сохранить' }))

    await waitFor(() => expect(captured).not.toBeNull())
    expect(captured!.name).toBe('Новое название')
  })
})

describe('Settings — AccountsTab edit modal', () => {
  const goToAccounts = async () => {
    renderWithProviders(<Settings />)
    // Accounts tab is default — just wait for content
    await waitFor(() => expect(screen.getByText('Сбербанк')).toBeInTheDocument())
  }

  it('opens edit modal when Изменить is clicked for an account', async () => {
    const user = userEvent.setup()
    await goToAccounts()
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить счёт')).toBeInTheDocument())
    expect(screen.getByDisplayValue('Сбербанк')).toBeInTheDocument()
  })

  it('closes modal when Отмена is clicked', async () => {
    const user = userEvent.setup()
    await goToAccounts()
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить счёт')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Отмена' }))
    expect(screen.queryByText('Изменить счёт')).not.toBeInTheDocument()
  })

  it('calls PUT /accounts/:id with updated data on save', async () => {
    let captured: Record<string, unknown> | null = null
    server.use(
      http.put('/api/v1/accounts/:id', async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>
        return HttpResponse.json<Account>({
          id: 'acc-1', user_id: 'user-1', bank: 'Тинькофф', account_number: '40817810',
          currency: 'RUB', is_active: true, has_balances: true,
        })
      }),
    )

    const user = userEvent.setup()
    await goToAccounts()
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByDisplayValue('Сбербанк')).toBeInTheDocument())

    const bankInput = screen.getByDisplayValue('Сбербанк')
    await user.clear(bankInput)
    await user.type(bankInput, 'Тинькофф')
    await user.click(screen.getByRole('button', { name: 'Сохранить' }))

    await waitFor(() => expect(captured).not.toBeNull())
    expect(captured!.bank).toBe('Тинькофф')
  })
})

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import Rules from '../Rules'
import { renderWithProviders } from '../../test/utils'
import { server } from '../../test/server'
import type { ClassifierRule } from '../../types'

const RULE_FIXTURE: ClassifierRule = {
  id: 'rule-1',
  name: 'Продукты',
  expense_type_id: 'food',
  priority: 1,
  is_active: true,
  representation: "Тип: Расход; Категория содержит 'продукты'",
  cond_account_id: null,
  cond_day_month: null,
  cond_day_month_op: null,
  cond_day_week: null,
  cond_amount: null,
  cond_amount_op: null,
  cond_type: 'EXPENSE',
  cond_bank_category: 'продукты',
  cond_description: null,
}

describe('Rules page', () => {
  it('renders rules list with all columns', async () => {
    renderWithProviders(<Rules />)
    await waitFor(() => expect(screen.getByText('Продукты')).toBeInTheDocument())
    // name
    expect(screen.getByText('Продукты')).toBeInTheDocument()
    // expense type (from mock: id='food' → name='Питание')
    await waitFor(() => expect(screen.getByText('Питание')).toBeInTheDocument())
    // priority
    expect(screen.getByText('1')).toBeInTheDocument()
    // representation
    expect(screen.getByText(/Тип: Расход/)).toBeInTheDocument()
    // is_active → ✓
    expect(screen.getByText('✓')).toBeInTheDocument()
  })

  it('shows column headers', async () => {
    renderWithProviders(<Rules />)
    await waitFor(() => expect(screen.getByText('Продукты')).toBeInTheDocument())
    const headers = screen.getAllByRole('columnheader').map((h) => h.textContent)
    expect(headers).toContain('Имя правила')
    expect(headers).toContain('Тип затрат')
    expect(headers).toContain('Приоритет')
    expect(headers).toContain('Представление')
    expect(headers).toContain('Действует')
  })

  it('shows "—" when rule is inactive', async () => {
    server.use(
      http.get('/api/v1/classifier-rules', () =>
        HttpResponse.json<ClassifierRule[]>([{ ...RULE_FIXTURE, is_active: false }]),
      ),
    )
    renderWithProviders(<Rules />)
    await waitFor(() => expect(screen.getByText('Продукты')).toBeInTheDocument())
    expect(screen.queryByText('✓')).not.toBeInTheDocument()
  })

  it('shows "+ Добавить" and "Заполнить" buttons', () => {
    renderWithProviders(<Rules />)
    expect(screen.getByRole('button', { name: '+ Добавить' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Заполнить' })).toBeInTheDocument()
  })

  it('opens RuleEditModal in create mode when "+ Добавить" is clicked', async () => {
    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '+ Добавить' }))
    await waitFor(() => expect(screen.getByText('Добавить правило')).toBeInTheDocument())
  })

  it('opens RuleEditModal in edit mode with pre-filled data when Изменить is clicked', async () => {
    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Изменить' }))
    await waitFor(() => expect(screen.getByText('Изменить правило')).toBeInTheDocument())
    // name pre-filled
    expect(screen.getByDisplayValue('Продукты')).toBeInTheDocument()
    // priority pre-filled
    expect(screen.getByDisplayValue('1')).toBeInTheDocument()
  })

  it('opens RuleFillModal when "Заполнить" is clicked', async () => {
    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Заполнить' }))
    await waitFor(() => expect(screen.getByText('Заполнить правилами')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Применить/ })).toBeInTheDocument()
  })

  it('shows inline delete confirmation when Удалить is clicked', async () => {
    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    expect(screen.getByText('Удалить?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Да' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Нет' })).toBeInTheDocument()
  })

  it('cancels delete when "Нет" is clicked', async () => {
    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Нет' }))
    expect(screen.queryByText('Удалить?')).not.toBeInTheDocument()
  })

  it('calls delete API when "Да" is confirmed', async () => {
    const deleteSpy = vi.fn(() => new HttpResponse(null, { status: 204 }))
    server.use(http.delete('/api/v1/classifier-rules/:id', deleteSpy))

    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Удалить' }))
    await user.click(screen.getByRole('button', { name: 'Да' }))
    await waitFor(() => expect(deleteSpy).toHaveBeenCalled())
  })

  it('calls apply API from RuleFillModal', async () => {
    const applySpy = vi.fn(() => HttpResponse.json({ updated_count: 5 }))
    server.use(http.post('/api/v1/classifier-rules/apply', applySpy))

    renderWithProviders(<Rules />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Заполнить' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /Применить/ })).toBeInTheDocument())

    // Fill in dates
    const dateInputs = screen.getAllByDisplayValue('')
    await user.type(dateInputs[0], '2026-01-01')
    await user.type(dateInputs[1], '2026-01-31')

    await user.click(screen.getByRole('button', { name: /Применить/ }))
    await waitFor(() => expect(applySpy).toHaveBeenCalled())
  })

  it('shows Изменить and Удалить for each rule', async () => {
    renderWithProviders(<Rules />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Изменить' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument()
  })

  it('shows empty state when no rules', async () => {
    server.use(
      http.get('/api/v1/classifier-rules', () => HttpResponse.json<ClassifierRule[]>([])),
    )
    renderWithProviders(<Rules />)
    await waitFor(() => expect(screen.getByText(/Нет правил/)).toBeInTheDocument())
  })
})

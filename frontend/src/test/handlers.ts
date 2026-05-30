import { http, HttpResponse } from 'msw'
import type { Account, Transaction, ExpenseType } from '../types'
import type { AccountCreate } from '../types'

export const handlers = [
  http.get('/api/v1/accounts', () =>
    HttpResponse.json<Account[]>([
      {
        id: 'acc-1',
        user_id: 'user-1',
        bank: 'Сбербанк',
        account_number: '40817810',
        currency: 'RUB',
        is_active: true,
        has_balances: true,
      },
    ]),
  ),

  http.post('/api/v1/accounts', async ({ request }) => {
    const body = (await request.json()) as AccountCreate
    return HttpResponse.json<Account>(
      {
        id: 'acc-new',
        user_id: 'user-1',
        bank: body.bank,
        account_number: body.account_number,
        currency: body.currency ?? 'RUB',
        is_active: true,
        has_balances: false,
      },
      { status: 201 },
    )
  }),

  http.put('/api/v1/accounts/:id', async ({ request }) => {
    const body = (await request.json()) as Partial<Account>
    return HttpResponse.json<Account>({
      id: 'acc-1',
      user_id: 'user-1',
      bank: body.bank ?? 'Сбербанк',
      account_number: body.account_number ?? '40817810',
      currency: body.currency ?? 'RUB',
      is_active: body.is_active ?? true,
      has_balances: true,
    })
  }),

  http.delete('/api/v1/accounts/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/v1/transactions', () =>
    HttpResponse.json<Transaction[]>([
      {
        id: 'tx-1',
        account_id: 'acc-1',
        occurred_at: '2026-04-01T10:00:00',
        processed_at: null,
        amount: '-1500.00',
        type: 'EXPENSE',
        bank_category: null,
        counterparty_id: 'cp-1',
        expense_type_id: null,
        description: null,
        balance_after: '50000.00',
        calculated_balance_after: null,
        balance_mismatch: false,
        receipt_id: null,
        reconciled_status: 'UNMATCHED',
        import_status: 'IMPORTED',
      },
    ]),
  ),

  http.post('/api/v1/transactions', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ id: 'tx-new', ...body }, { status: 201 })
  }),

  http.delete('/api/v1/transactions/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/v1/expense-types', () =>
    HttpResponse.json<ExpenseType[]>([{ id: 'food', name: 'Питание', receipt_required: true }]),
  ),

  http.post('/api/v1/reconciliation/run', () =>
    HttpResponse.json({
      report_generated_at: '2026-04-01T12:00:00',
      summary: {
        auto_matched_count: 0,
        missing_receipts_count: 0,
        unmatched_receipts_count: 0,
        collisions_count: 0,
      },
      collisions: [],
      missing_receipts: [],
      unmatched_receipts: [],
    }),
  ),

  http.get('/api/v1/auth/me', () =>
    HttpResponse.json({
      id: 'user-1',
      email: 'test@example.com',
      full_name: 'Test User',
      avatar_url: null,
      is_active: true,
    }),
  ),
]

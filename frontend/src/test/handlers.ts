import { http, HttpResponse } from 'msw'
import type { Account, Balance, Counterparty, Document, ReceiptListItem, Transaction, ExpenseType } from '../types'
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
        expense_type_id: 'et-1',
        description: null,
        balance_after: '50000.00',
        calculated_balance_after: null,
        balance_mismatch: false,
        receipt_id: null,
        reconciled_status: 'UNMATCHED',
        import_status: 'IMPORTED',
        document_id: null,
      },
    ]),
  ),

  http.post('/api/v1/transactions', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ id: 'tx-new', ...body }, { status: 201 })
  }),

  http.delete('/api/v1/transactions/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/v1/expense-types', () =>
    HttpResponse.json<ExpenseType[]>([{ id: 'food', name: 'Питание', description: null, receipt_required: true }]),
  ),

  http.get('/api/v1/reconciliation/report', () =>
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

  http.get('/api/v1/documents/:id', ({ params }) =>
    HttpResponse.json<Document>({
      id: String(params.id),
      user_id: 'user-1',
      type: 'RECEIPT',
      url: '/media/fake/doc-1',
      name: 'receipt.pdf',
      status: 'PROCESSED',
      email_source: null,
      file_hash: 'hash1',
      uploaded_at: '2026-04-01T10:00:00',
      payload: null,
    }),
  ),

  http.put('/api/v1/documents/:id', async ({ request }) => {
    const body = (await request.json()) as Partial<Document>
    return HttpResponse.json<Document>({
      id: 'doc-1',
      user_id: 'user-1',
      type: 'RECEIPT',
      url: '/media/fake/doc-1',
      name: 'receipt.pdf',
      status: 'PROCESSED',
      email_source: null,
      file_hash: 'hash1',
      uploaded_at: '2026-04-01T10:00:00',
      payload: body.payload ?? null,
    })
  }),

  http.put('/api/v1/transactions/:id', async ({ request }) => {
    const body = (await request.json()) as Partial<Transaction>
    return HttpResponse.json<Transaction>({
      id: 'tx-1',
      account_id: 'acc-1',
      occurred_at: body.occurred_at ?? '2026-04-01T10:00:00',
      processed_at: null,
      amount: body.amount ?? '-1500.00',
      type: (body.type as Transaction['type']) ?? 'EXPENSE',
      bank_category: body.bank_category ?? null,
      expense_type_id: body.expense_type_id ?? 'et-1',
      description: body.description ?? null,
      balance_after: '50000.00',
      calculated_balance_after: null,
      balance_mismatch: false,
      receipt_id: null,
      reconciled_status: (body.reconciled_status as Transaction['reconciled_status']) ?? 'UNMATCHED',
      import_status: 'IMPORTED',
      document_id: null,
    })
  }),

  http.get('/api/v1/documents', () =>
    HttpResponse.json<Document[]>([
      {
        id: 'doc-1',
        user_id: 'user-1',
        type: 'RECEIPT',
        url: '/media/fake/doc-1',
        name: 'receipt.pdf',
        status: 'PENDING',
        email_source: null,
        file_hash: 'hash1',
        uploaded_at: '2026-04-01T10:00:00',
      },
      {
        id: 'doc-2',
        user_id: 'user-1',
        type: 'BANK_STATEMENT',
        url: '/media/fake/doc-2',
        name: 'statement.pdf',
        status: 'PROCESSED',
        email_source: null,
        file_hash: 'hash2',
        uploaded_at: '2026-03-01T10:00:00',
      },
    ]),
  ),

  http.post('/api/v1/documents', () =>
    HttpResponse.json<Document>(
      {
        id: 'doc-new',
        user_id: 'user-1',
        type: 'BANK_STATEMENT',
        url: '/media/fake/doc-new',
        name: 'upload.pdf',
        status: 'PENDING',
        email_source: null,
        file_hash: 'hashnew',
        uploaded_at: '2026-04-10T10:00:00',
      },
      { status: 201 },
    ),
  ),

  http.post('/api/v1/documents/:id/link-receipt', () =>
    HttpResponse.json({ document_id: 'doc-1', status: 'PROCESSED', updated_count: 1, message: null }),
  ),

  http.post('/api/v1/documents/:id/link-statement', () =>
    HttpResponse.json({ document_id: 'doc-2', status: 'PROCESSED', updated_count: 3, message: null }),
  ),

  http.post('/api/v1/documents/:id/reset', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      user_id: 'user-1',
      type: 'BANK_STATEMENT',
      url: '/media/fake/doc-2',
      name: 'statement.pdf',
      status: 'PENDING',
      uploaded_at: '2026-03-01T10:00:00',
      email_source: null,
      file_hash: 'abc123',
    }),
  ),

  http.get('/api/v1/receipts', () =>
    HttpResponse.json<ReceiptListItem[]>([
      {
        id: 'rec-1',
        paid_at: '2026-04-01T10:00:00',
        total_amount: '500.00',
        counterparty_id: 'cp-1',
        document_id: null,
      },
    ]),
  ),

  http.get('/api/v1/balances', () =>
    HttpResponse.json<Balance[]>([
      {
        id: 'bal-1',
        account_id: 'acc-1',
        amount: '50000.00',
        recorded_at: '2026-04-01T00:00:00',
        source: 'OPENING',
        document_id: null,
      },
      {
        id: 'bal-2',
        account_id: 'acc-1',
        amount: '48000.00',
        recorded_at: '2026-04-30T23:59:59',
        source: 'CLOSING',
        document_id: 'doc-2',
      },
    ]),
  ),

  http.get('/api/v1/counterparties', () =>
    HttpResponse.json<Counterparty[]>([
      { id: 'cp-1', name: 'Магазин Тест', type: 'STORE', inn: null, kpp: null },
    ]),
  ),

  http.post('/api/v1/counterparties', async ({ request }) => {
    const body = (await request.json()) as { name: string; type?: string }
    return HttpResponse.json<Counterparty>(
      { id: body.name.toLowerCase(), name: body.name, type: body.type ?? 'STORE', inn: null, kpp: null },
      { status: 201 },
    )
  }),

  http.put('/api/v1/counterparties/:id', async ({ request }) => {
    const body = (await request.json()) as Partial<Counterparty>
    return HttpResponse.json<Counterparty>({
      id: 'cp-1',
      name: body.name ?? 'Магазин Тест',
      type: body.type ?? 'STORE',
      inn: body.inn ?? null,
      kpp: body.kpp ?? null,
    })
  }),

  http.delete('/api/v1/counterparties/:id', () => new HttpResponse(null, { status: 204 })),
]
